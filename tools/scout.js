// Builds the lead list: pull local businesses from a source, audit every
// website automatically, rank by how much money the bad site is costing them.
//
//   osm     OpenStreetMap via Overpass — free, no key, no rate limit worth caring about
//   places  Google Places — costs a little, but adds star rating and review count
//   file    a text file of URLs or "name,url" lines you gathered yourself

const fs = require('fs');
const path = require('path');
const { audit, CHECKS } = require('./audit');

// Overpass instances go down and rate-limit independently; try them in turn.
const OVERPASS_MIRRORS = (process.env.OVERPASS_MIRRORS || '').split(',').map((x) => x.trim()).filter(Boolean);
if (!OVERPASS_MIRRORS.length) OVERPASS_MIRRORS.push(
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass.osm.ch/api/interpreter',
);

// OSM's usage policy requires a descriptive User-Agent. Without one,
// overpass-api.de answers 406 and refuses to look at the query at all.
const OSM_UA = 'cold-call-coach/1.0 (local business lead scout; https://github.com/tylermcmanus1010-max/Cold-Call-Coach)';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Overpass explains itself in the response body — a "remark" naming the real
// problem. Surface it instead of leaving you with a bare status code.
function explain(status, body) {
  const remark = (body.match(/<remark>([\s\S]*?)<\/remark>/i) || body.match(/(Error: [^<\n]{0,200})/i) || [])[1];
  const cleaned = (remark || body).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 180);
  const hint =
    status === 406 ? 'refused the request outright — usually a User-Agent it does not accept' :
    status === 429 ? 'rate limited — this mirror wants you to wait' :
    status === 504 ? 'query timed out on their side — the area or trade list is too big' :
    status === 500 ? 'server error, often a query too heavy for this mirror' :
    status === 403 ? 'refused — usually a proxy or firewall between you and it' : '';
  return [hint, cleaned && `said: "${cleaned}"`].filter(Boolean).join('; ');
}

async function overpassQuery(query, label) {
  const failures = [];

  for (const mirror of OVERPASS_MIRRORS) {
    const host = new URL(mirror).host;

    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const res = await fetch(mirror, {
          method: 'POST',
          headers: { 'content-type': 'application/x-www-form-urlencoded', 'user-agent': OSM_UA, accept: 'application/json' },
          body: new URLSearchParams({ data: query }),
        });
        if (res.ok) return (await res.json()).elements || [];

        const body = await res.text().catch(() => '');
        failures.push(`${host}: HTTP ${res.status} ${explain(res.status, body)}`);
        // A heavy query or a busy mirror can come good on a second try; a refusal will not.
        if (![429, 500, 502, 503, 504].includes(res.status) || attempt === 2) break;
        await sleep(3000);
      } catch (e) {
        const code = e.cause?.code || e.message;
        failures.push(`${host}: ${code}` + (String(code).includes('CERT') ? ' (their TLS certificate is expired — nothing you can do)' : ''));
        break;
      }
    }
    process.stderr.write(`  [${label}] ${failures[failures.length - 1]}\n`);
  }

  const err = new Error(`every mirror failed for ${label}`);
  err.failures = failures;
  throw err;
}
const PLACES = 'https://places.googleapis.com/v1/places:searchNearby';

// "Great Clips #1234" is a chain; "Chase's Barber Shop" is not. Normalising
// strips punctuation, so a possessive never collides with a bank.
// Drop apostrophes before anything else so a possessive collapses into one
// word: "Chase's" becomes "chases", which can never match the bank "chase".
const normName = (s) => String(s || '').toLowerCase()
  .replace(/['’]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

function isChain(name, list) {
  const n = normName(name);
  return list.some((raw) => {
    const c = normName(raw);
    return n === c || n.startsWith(c + ' ');
  });
}

const slugify = (s) => String(s).toLowerCase().replace(/&/g, ' and ')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);

// Run the audits a few at a time: fast, but not so fast it looks like an attack.
async function pool(items, limit, fn, onTick) {
  const out = new Array(items.length);
  let next = 0, done = 0;
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      try { out[i] = await fn(items[i], i); } catch (e) { out[i] = { error: e.message }; }
      if (onTick) onTick(++done, items.length);
    }
  }));
  return out;
}

async function fromOsm(cfg) {
  const [s, w, n, e] = cfg.area.bbox;
  const bbox = `(${s},${w},${n},${e})`;
  const clause = (k, vals) => `  nwr["${k}"~"^(${vals.join('|')})$"]${bbox};`;
  const wrap = (body, secs) => `[out:json][timeout:${secs}];\n(\n${body}\n);\nout tags center;`;

  const categories = Object.entries(cfg.osmTags);
  const combined = wrap(categories.map(([k, v]) => clause(k, v)).join('\n'), 90);

  // One request for everything is fastest when it works.
  try {
    return toLeads(await overpassQuery(combined, 'all trades'));
  } catch (bigErr) {
    process.stderr.write('  combined query failed — retrying one trade group at a time…\n');

    // Smaller queries are far likelier to survive a busy mirror, and a group
    // that fails only costs us that group instead of the whole run.
    const collected = [];
    const failed = [];
    for (const [k, vals] of categories) {
      try {
        const els = await overpassQuery(wrap(clause(k, vals), 60), k);
        collected.push(...els);
        process.stderr.write(`  ${k}: ${els.length}\n`);
      } catch (e) {
        failed.push(`${k} (${(e.failures || []).join(' | ')})`);
      }
    }

    if (collected.length) {
      if (failed.length) process.stderr.write(`  note: no results for ${failed.length} of ${categories.length} trade groups\n`);
      return toLeads(collected);
    }

    throw new Error(
      'Could not reach any Overpass mirror.\n  ' + (bigErr.failures || []).join('\n  ') +
      (failed.length ? '\n\n  Per-trade retries also failed:\n  ' + failed.join('\n  ') : '') +
      '\n\n  Overpass is a free volunteer service and does go down. Options:\n' +
      '    - wait 10 minutes and run it again\n' +
      '    - ./cc scout --source places      (needs GOOGLE_MAPS_API_KEY, and gives review counts)\n' +
      '    - ./cc scout --source file --file leads/urls.txt');
  }
}

function toLeads(elements) {
  const seen = new Set();
  return elements.map((el) => {
    const t = el.tags || {};
    const category = t.craft || t.shop || t.amenity || t.office || t.leisure || '';
    return {
      source: 'osm',
      id: `osm-${el.type}-${el.id}`,
      name: t.name,
      category: category.replace(/_/g, ' '),
      phone: t.phone || t['contact:phone'] || '',
      website: (t.website || t['contact:website'] || t.url || '').trim(),
      facebook: t['contact:facebook'] || '',
      address: {
        street: [t['addr:housenumber'], t['addr:street']].filter(Boolean).join(' '),
        city: t['addr:city'] || '', state: t['addr:state'] || 'CA', zip: t['addr:postcode'] || '',
      },
      rating: null, reviewCount: null,
    };
  }).filter((b) => {
    // The per-trade fallback can return the same place under two tags.
    if (!b.name || seen.has(b.id)) return false;
    seen.add(b.id);
    return true;
  });
}

async function fromPlaces(cfg, key) {
  const seen = new Map();
  const fields = ['places.id', 'places.displayName', 'places.primaryTypeDisplayName', 'places.websiteUri',
    'places.nationalPhoneNumber', 'places.formattedAddress', 'places.rating',
    'places.userRatingCount', 'places.businessStatus'].join(',');

  let calls = 0;
  for (const c of cfg.area.centers) {
    for (const type of cfg.placesTypes) {
      const res = await fetch(PLACES, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Goog-Api-Key': key, 'X-Goog-FieldMask': fields },
        body: JSON.stringify({
          includedTypes: [type], maxResultCount: 20,
          locationRestriction: { circle: { center: { latitude: c.lat, longitude: c.lng }, radius: cfg.area.radiusMeters } },
        }),
      });
      calls++;
      if (!res.ok) {
        const body = await res.text();
        const hint =
          res.status === 403 ? '\n  The key is valid but not authorized. Enable "Places API (New)" in your Google Cloud project.' :
          res.status === 400 ? '\n  Check placesTypes in config/scout.json — one of them is not a valid Places type.' :
          res.status === 429 ? '\n  Quota exceeded. Trim config/scout.json → area.centers or placesTypes and rerun.' : '';
        throw new Error(`Places returned ${res.status} after ${calls} calls: ${body.slice(0, 300)}${hint}`);
      }
      for (const p of (await res.json()).places || []) {
        if (p.businessStatus && p.businessStatus !== 'OPERATIONAL') continue;
        if (seen.has(p.id)) continue;
        const m = (p.formattedAddress || '').match(/^(.*?),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5})/);
        seen.set(p.id, {
          source: 'places', id: p.id,
          name: p.displayName?.text,
          category: p.primaryTypeDisplayName?.text || type.replace(/_/g, ' '),
          phone: p.nationalPhoneNumber || '',
          website: (p.websiteUri || '').trim(),
          address: m ? { street: m[1], city: m[2], state: m[3], zip: m[4] } : { street: p.formattedAddress || '', city: '', state: 'CA', zip: '' },
          rating: p.rating ?? null, reviewCount: p.userRatingCount ?? null,
        });
      }
    }
    process.stderr.write(`  ${c.name}: ${seen.size} businesses so far\n`);
  }
  return [...seen.values()];
}

function fromFile(file) {
  return fs.readFileSync(file, 'utf8').split('\n').map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'))
    .map((line, i) => {
      const [a, b] = line.split(',').map((x) => (x || '').trim());
      const url = /^https?:|\./.test(b || '') ? b : (/^https?:|\./.test(a) ? a : '');
      const name = url === a ? '' : a;
      return { source: 'file', id: `file-${i}`, name: name || url, category: '', phone: '', website: url,
               address: { city: '', state: 'CA', zip: '' }, rating: null, reviewCount: null };
    });
}

// Rank by opportunity, not just by how broken the site is: a shop with 400
// reviews and no mobile site is worth ten with 20 reviews.
function rank(lead) {
  const a = lead.auditResult;
  let s = a.gaps * 6;
  if (!lead.website) {
    // Google knows whether a business has a website; OpenStreetMap only knows
    // whether a volunteer typed one in. Only trust the former.
    s += lead.source === 'places' ? 30 : 2;
  }
  if (lead.website && !a.reachable) s += 25;        // we fetched it and it is dead
  if (a.stale) s += 10;                             // visibly abandoned
  if (!a.checks.mobile) s += 12;                    // the one that actually costs them calls
  if (!a.checks.https) s += 8;
  if (lead.reviewCount) s += Math.min(30, Math.log10(lead.reviewCount) * 14);
  if (lead.rating) s += (lead.rating - 3.5) * 6;
  if (lead.phone) s += 5;                           // you can actually call them
  return Math.round(s);
}

async function scout(cfg, opts) {
  const src = opts.source || 'osm';
  process.stderr.write(`Pulling businesses from ${src}${src === 'osm' ? ' (OpenStreetMap)' : ''}…\n`);

  let leads =
    src === 'osm' ? await fromOsm(cfg) :
    src === 'places' ? await fromPlaces(cfg, opts.key) :
    fromFile(opts.file);

  process.stderr.write(`Found ${leads.length} businesses.\n`);

  const f = cfg.filters;
  if (src === 'places') {
    const before = leads.length;
    leads = leads.filter((b) => (b.reviewCount ?? 0) >= f.minReviews && (b.rating ?? 0) >= f.minRating);
    process.stderr.write(`${leads.length} pass the ${f.minReviews}+ reviews / ${f.minRating}+ stars filter (dropped ${before - leads.length}).\n`);
  }

  const chains = cfg.excludeNames?.names || [];
  if (chains.length) {
    const before = leads.length;
    leads = leads.filter((b) => !isChain(b.name, chains));
    if (before - leads.length) process.stderr.write(`Dropped ${before - leads.length} chain locations.\n`);
  }

  const withSite = leads.filter((b) => b.website);
  const withoutSite = leads.filter((b) => !b.website);
  process.stderr.write(`${withSite.length} have a website listed, ${withoutSite.length} do not.\n`);

  // Auditable businesses first: a site we can fetch and prove broken is a real
  // lead, where a missing OSM website tag is only a maybe.
  leads = [...withSite, ...withoutSite];
  if (opts.limit) leads = leads.slice(0, opts.limit);

  process.stderr.write(`Auditing ${leads.length} websites, ${cfg.concurrency} at a time…\n`);
  const audits = await pool(leads, cfg.concurrency, (b) => audit(b.website, { timeout: cfg.timeoutMs }),
    (done, total) => { if (done % 25 === 0 || done === total) process.stderr.write(`  ${done}/${total}\n`); });

  leads.forEach((b, i) => { b.auditResult = audits[i]; b.slug = slugify(b.name); });
  const blocked = leads.filter((b) => b.auditResult.blocked);
  if (blocked.length) process.stderr.write(
    `${blocked.length} sites blocked our check (Cloudflare and similar) — skipped, since we cannot prove anything is wrong with them.\n`);

  const qualified = leads.filter((b) => !b.auditResult.blocked && b.auditResult.gaps >= f.minGaps);
  qualified.sort((a, b) => rank(b) - rank(a));
  qualified.forEach((b) => { b.score = rank(b); });

  process.stderr.write(`${qualified.length} leads have ${f.minGaps}+ gaps and are worth calling.\n`);
  return qualified;
}

const csvCell = (v) => {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};

function toCsv(leads) {
  const head = ['score', 'name', 'category', 'phone', 'website', 'status', 'gaps', 'rating', 'reviews', 'city', 'slug', 'failing'];
  const rows = leads.map((b) => {
    const a = b.auditResult;
    return [
      b.score, b.name, b.category, b.phone, b.website || '(none)',
      !b.website ? (b.source === 'osm' ? 'no website listed - verify' : 'no website')
        : !a.reachable ? (a.reason || 'unreachable') : (a.reason || 'live'),
      a.gaps, b.rating ?? '', b.reviewCount ?? '', b.address?.city || '', b.slug,
      CHECKS.filter((c) => !a.checks[c.key]).map((c) => c.key).join(' '),
    ].map(csvCell).join(',');
  });
  return [head.join(','), ...rows].join('\n') + '\n';
}

// Turn a lead straight into a client folder, pre-filled with everything we
// already know, so the only work left is the sales copy.
function toBusinessJson(lead, tplPath) {
  const tpl = JSON.parse(fs.readFileSync(tplPath, 'utf8'));
  const a = lead.auditResult, info = a.info || {};
  // Prefer structured data, then the address scraped off the page, then the directory listing.
  const addr = info.ldAddress?.street ? info.ldAddress
    : (lead.address?.street ? lead.address
    : { street: info.street || '', ...(info.cityState || {}) });

  return {
    ...tpl,
    _howto: `Auto-filled by ./cc scout from ${lead.source}. Verify everything, then write headline, services and reviews by hand — that is the part that sells.`,
    slug: lead.slug,
    name: lead.name || info.ldName || info.title || '',
    category: lead.category,
    currentSite: lead.website ? (a.finalUrl || 'https://' + a.url) : '',
    phone: lead.phone || info.ldPhone || info.phone || '',
    address: { street: addr?.street || '', city: addr?.city || 'San Diego', state: addr?.state || 'CA', zip: addr?.zip || '' },
    tagline: info.description || '',
    rating: lead.rating
      ? { value: String(lead.rating), count: String(lead.reviewCount ?? ''), source: 'Google' }
      : (info.ldRating ? { value: String(info.ldRating.value), count: String(info.ldRating.count), source: 'Google' } : tpl.rating),
    audit: a.checks,
    _scout: {
      score: lead.score, gaps: a.gaps,
      currentSiteStatus: !lead.website ? 'no website' : a.reachable ? (a.reason || 'live') : `unreachable: ${a.reason}`,
      loadMs: a.ms ?? null, pageKb: a.kb ?? null, builder: info.builder || null, copyrightYear: info.copyrightYear || null,
    },
  };
}

// A business name containing "|" would otherwise break the table row and
// shift every cell after it into the wrong column.
const mdCell = (v) => String(v == null ? '' : v).replace(/\|/g, '\\|').replace(/\n/g, ' ');

// Markdown so the list is readable straight off a phone screen.
function toMarkdown(leads, area) {
  const rows = leads.slice(0, 40).map((b, i) => {
    const a = b.auditResult;
    const site = !b.website ? (b.source === 'osm' ? '**no site listed** _(verify)_' : '**no website**')
      : !a.reachable ? `**${a.reason || 'unreachable'}**`
      : (a.reason ? `${mdCell(a.reason)}` : `[live](${a.finalUrl || 'https://' + a.url})`);
    const rev = b.reviewCount != null ? `${b.rating ?? '–'}★ / ${b.reviewCount}` : '–';
    return `| ${i + 1} | **${mdCell(b.name)}** | ${mdCell(b.category) || '–'} | ${mdCell(b.phone) || '–'} | ${a.gaps}/12 | ${rev} | ${mdCell(site)} |`;
  });
  return [
    `## ${leads.length} leads worth calling — ${area}`, '',
    '| # | Business | Type | Phone | Gaps | Rating | Current site |',
    '|---|---|---|---|---|---|---|',
    ...rows, '',
    leads.length > 40 ? `_Showing the top 40 of ${leads.length}. Full list in the leads.csv artifact._` : '',
    '', 'Pick one and reply with its number.',
  ].join('\n');
}

module.exports = { scout, toCsv, toMarkdown, toBusinessJson, rank, slugify };
