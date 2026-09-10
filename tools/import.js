// Brings in leads found by hand — or by Polar — as scaffolded clients.
//
// Polar can go where no API reaches: Yelp results, Thumbtack and Angi
// contractor lists, Nextdoor, Facebook pages. What it produces is a list:
// name, phone, city, website. This turns that list into
// clients/<slug>/business.json the way ./cc scout would — except nothing
// here has been measured yet, so nothing is claimed: audit is empty, the
// scout block says unverified, no page is built. reaudit.yml measures it in
// a real browser and research.yml decides what the URL actually is; only
// then does it earn a page. Audit first, build second.
//
// Accepts CSV (a header row; name / phone / website / city / state /
// category, column names matched loosely) or a JSON array of the same.
// Never writes an email: one Polar read off a contact page is kept under
// _import for a person to judge — the same rule campaign.js applies to a
// crawl, because an address nobody checked is how the bounces happened.

const fs = require('fs');
const path = require('path');
const suppress = require('./suppress');
const { slugify } = require('./scout');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');
const TPL = path.join(ROOT, 'tools/business.template.json');

const digits = (s) => String(s || '').replace(/[^0-9]/g, '');
const ten = (s) => digits(s).replace(/^1(?=\d{10}$)/, '');
const TOLL_FREE = /^8(00|33|44|55|66|77|88)/;

const ALIASES = {
  name: ['name', 'business', 'businessname', 'company'],
  phone: ['phone', 'tel', 'telephone', 'number', 'phonenumber'],
  website: ['website', 'site', 'url', 'web', 'domain', 'homepage'],
  city: ['city', 'town'],
  state: ['state', 'st', 'province'],
  zip: ['zip', 'zipcode', 'postcode', 'postal'],
  street: ['street', 'address', 'address1'],
  category: ['category', 'type', 'trade', 'kind', 'industry'],
  email: ['email', 'emailaddress'],
  notes: ['notes', 'note', 'source', 'foundon', 'why'],
};
const canon = (h) => String(h || '').toLowerCase().replace(/[^a-z0-9]/g, '');
function fieldFor(header) {
  const c = canon(header);
  for (const [field, names] of Object.entries(ALIASES)) if (names.includes(c)) return field;
  return null;
}

// A small CSV reader: quoted fields, doubled quotes, CRLF, blank lines.
function parseCsv(text) {
  const rows = [];
  let row = [], cell = '', quoted = false;
  const s = String(text).replace(/^﻿/, '');
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (quoted) {
      if (ch === '"') { if (s[i + 1] === '"') { cell += '"'; i++; } else quoted = false; }
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && s[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim() !== ''));
}

function parse(text) {
  const t = String(text || '').trim();
  if (!t) return [];
  if (t[0] === '[' || t[0] === '{') {
    const j = JSON.parse(t);
    const arr = Array.isArray(j) ? j : (j.rows || j.leads || j.results || j.businesses || []);
    return arr.map((o) => {
      const out = {};
      for (const [k, v] of Object.entries(o || {})) { const f = fieldFor(k); if (f && v != null && String(v).trim() !== '') out[f] = String(v).trim(); }
      return out;
    });
  }
  const rows = parseCsv(t);
  if (rows.length < 2) return [];
  const fields = rows[0].map(fieldFor);
  if (!fields.includes('name')) throw new Error(`the header row needs a "name" column (got: ${rows[0].join(', ')})`);
  return rows.slice(1).map((r) => {
    const out = {};
    fields.forEach((f, i) => { if (f && r[i] != null && r[i].trim() !== '') out[f] = r[i].trim(); });
    return out;
  });
}

// The shape business.json already uses ("+1-619-477-8588"), so dedupe
// against the pipeline matches on digits either way.
function normalizePhone(s) {
  const d = ten(s);
  return d.length === 10 ? `+1-${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}` : '';
}

function normalizeSite(s) {
  let u = String(s || '').trim();
  if (!u || /^(none|n\/?a|no website|no site|-|—)$/i.test(u)) return '';
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  try {
    const x = new URL(u);
    x.hash = '';
    for (const k of [...x.searchParams.keys()]) if (/^(utm_|fbclid|gclid)/.test(k)) x.searchParams.delete(k);
    return x.toString();
  } catch { return ''; }
}

const hostOf = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
const nameKey = (name, city) => String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '') + '@' + String(city || '').toLowerCase().trim();

function existingIndex() {
  const idx = { tel: new Set(), host: new Set(), name: new Set(), slug: new Set() };
  if (!fs.existsSync(CLIENTS)) return idx;
  for (const slug of fs.readdirSync(CLIENTS)) {
    const f = path.join(CLIENTS, slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    idx.slug.add(slug);
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }
    const d = ten(b.phone); if (d) idx.tel.add(d);
    const h = hostOf(b.currentSite); if (h) idx.host.add(h);
    idx.name.add(nameKey(b.name, b.address && b.address.city));
  }
  return idx;
}

function scaffold(row, { source, file }) {
  const tpl = JSON.parse(fs.readFileSync(TPL, 'utf8'));
  const b = {
    ...tpl,
    _howto: `Imported from ${source}${file ? ` (${path.basename(file)})` : ''} — NOT measured yet. Nothing in audit is claimed until reaudit.yml has looked in a real browser and research.yml has decided what is at the URL. Do not build or pitch before then.`,
    slug: row.slug,
    name: row.name,
    category: row.category || '',
    currentSite: row.website || '',
    phone: row.phone || '',
    address: { street: row.street || '', city: row.city || '', state: String(row.state || '').toUpperCase().slice(0, 2), zip: row.zip || '' },
    audit: {},
    _scout: {
      source,
      rendered: false,
      currentSiteStatus: row.website ? 'unverified — imported, not yet opened' : 'no website',
      importedAt: new Date().toISOString().slice(0, 10),
    },
  };
  if (!row.website) b.siteKind = 'none';
  const imp = {};
  if (row.email) {
    imp.email = row.email;
    imp._email = 'Read off a page by whoever imported it, not verified. Set "email" yourself if you trust it — nothing sends to it until you do.';
  }
  if (row.notes) imp.notes = row.notes;
  if (Object.keys(imp).length) b._import = imp;
  return b;
}

function importLeads(text, { source = 'polar', file = '', dryRun = false } = {}) {
  const rows = parse(text);
  const idx = existingIndex();
  const created = [], skipped = [];
  const seen = new Set();

  rows.forEach((raw, i) => {
    const r = { ...raw };
    r.name = String(r.name || '').trim().replace(/\s+/g, ' ');
    r.phone = normalizePhone(r.phone);
    r.website = normalizeSite(r.website);
    r.city = String(r.city || '').trim();
    r.state = String(r.state || '').trim();
    r.category = String(r.category || '').trim().toLowerCase();
    const label = r.name || `row ${i + 2}`;

    if (!r.name) return skipped.push({ name: label, why: 'no name' });
    if (!r.phone && !r.website) return skipped.push({ name: label, why: 'no phone and no website — nothing to reach them by' });
    const d = ten(r.phone);
    if (d && TOLL_FREE.test(d)) return skipped.push({ name: label, why: 'toll-free number — a call centre, not an owner' });

    const host = hostOf(r.website);
    const key = nameKey(r.name, r.city);
    const fileKey = d || host || key;
    if (seen.has(fileKey)) return skipped.push({ name: label, why: 'listed twice in this file' });
    // Do-not-contact outranks every other reason: someone who asked us to
    // stop must be told so, not filed as a duplicate.
    if (suppress.isSuppressed({ email: r.email, domain: host, phone: r.phone })) {
      return skipped.push({ name: label, why: 'on the do-not-contact list' });
    }
    if ((d && idx.tel.has(d)) || (host && idx.host.has(host)) || idx.name.has(key)) {
      return skipped.push({ name: label, why: 'already in the pipeline' });
    }

    let slug = slugify(r.name) || (d ? `lead-${d.slice(-4)}` : '');
    if (!slug) return skipped.push({ name: label, why: 'could not make a slug from the name' });
    if (idx.slug.has(slug)) slug += '-' + (r.city ? slugify(r.city) : d.slice(-4) || 'b');
    if (idx.slug.has(slug)) return skipped.push({ name: label, why: `clients/${slug} already exists` });
    r.slug = slug;

    const b = scaffold(r, { source, file });
    if (!dryRun) {
      fs.mkdirSync(path.join(CLIENTS, slug), { recursive: true });
      fs.writeFileSync(path.join(CLIENTS, slug, 'business.json'), JSON.stringify(b, null, 2) + '\n');
    }
    seen.add(fileKey);
    if (d) idx.tel.add(d);
    if (host) idx.host.add(host);
    idx.name.add(key);
    idx.slug.add(slug);
    created.push({ slug, name: r.name, phone: r.phone, website: r.website, city: r.city, state: b.address.state, category: r.category, email: r.email || '' });
  });

  return { total: rows.length, created, skipped };
}

module.exports = { importLeads, parse, parseCsv, normalizePhone, normalizeSite, fieldFor, scaffold };
