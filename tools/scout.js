// Builds the lead list: pull local businesses from a source, audit every
// website automatically, rank by how much money the bad site is costing them.
//
//   osm     OpenStreetMap via Overpass — free, no key, no rate limit worth caring about
//   places  Google Places — costs a little, but adds star rating and review count
//   file    a text file of URLs or "name,url" lines you gathered yourself

const fs = require('fs');
const path = require('path');
const { audit, CHECKS } = require('./audit');

const OVERPASS = 'https://overpass-api.de/api/interpreter';
const PLACES = 'https://places.googleapis.com/v1/places:searchNearby';

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
  const clauses = Object.entries(cfg.osmTags)
    .map(([k, vals]) => `  nwr["${k}"~"^(${vals.join('|')})$"]${bbox};`).join('\n');
  const q = `[out:json][timeout:120];\n(\n${clauses}\n);\nout tags center;`;

  const res = await fetch(OVERPASS, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ data: q }),
  });
  if (!res.ok) throw new Error(`Overpass returned ${res.status}. It rate-limits; wait a minute and retry.`);
  const { elements = [] } = await res.json();

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
  }).filter((b) => b.name);
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
        throw new Error(`Places returned ${res.status} after ${calls} calls: ${body.slice(0, 300)}`);
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
  if (!lead.website) s += 30;                       // no site at all
  if (!a.reachable) s += 25;                        // site is down or parked
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

  if (opts.limit) leads = leads.slice(0, opts.limit);

  process.stderr.write(`Auditing ${leads.length} websites, ${cfg.concurrency} at a time…\n`);
  const audits = await pool(leads, cfg.concurrency, (b) => audit(b.website, { timeout: cfg.timeoutMs }),
    (done, total) => { if (done % 25 === 0 || done === total) process.stderr.write(`  ${done}/${total}\n`); });

  leads.forEach((b, i) => { b.auditResult = audits[i]; b.slug = slugify(b.name); });
  const qualified = leads.filter((b) => b.auditResult.gaps >= f.minGaps);
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

module.exports = { scout, toCsv, toBusinessJson, rank, slugify };
