// Everything we can learn about a business before we build its page, from
// every source we can reach, into one harvest.json — and only the parts
// that are structured and attributed into business.json.
//
//   node tools/research.js <slug> [--apply] [--fresh]
//   node tools/research.js --all  [--apply] [--fresh]      every open client
//   --no-crawl   siteKind + JSON-LD + Google only; skip the nine-page read
//
// Why this exists: the old harvest read one site, one slug per button
// press, and had been run on 1 client in 90. Across the 35 open leads, 3 had
// real reviews, 1 had a price, 1 had a domain-parking blurb as its headline.
// The three gaps every pitch flags — hours, services, reviews — are the three
// things most small-business sites never put in scrapeable text. You can
// crawl their site perfectly and come up empty. So this asks four sources,
// in order, and each one is allowed to fail without taking the others down:
//
//   1. siteKind  what is actually at their URL, decided BEFORE anything is
//                scraped: own | parked | dead | challenge | platform |
//                notTheirs | none. A parked page's description is the
//                parking company's; a challenge page's shortcomings are the
//                CAPTCHA's. Nothing downstream reads a page this says not to.
//   2. JSON-LD   the site's own schema.org block. Hours, price range and
//                socials, structured, for free — the crawl's regexes ignore it.
//   3. Google    Place Details. Real hours, up to five reviews with names,
//                owner-uploaded photos, the business's own description.
//                Needs GOOGLE_MAPS_API_KEY; skipped, loudly, without it.
//   4. crawl     tools/harvest.js — the nine-page read, unchanged.
//
// What --apply writes, and only when the field is empty or a placeholder:
// siteKind, the Google place (id, rating, count, maps link), hours, up to
// three four-or-five-star reviews with names attributed to Google, and
// photos through the same dedup/embed as ./cc photo, untagged. Never
// services, never a headline — those need someone to read the harvest.
// The rule is the designer's rule: invent nothing that is a fact.

const fs = require('fs');
const path = require('path');
const { looksParked, BUILDERS } = require('./audit');
const { guessKind } = require('./photo-kind');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
const TIMEOUT = 20000;
const GOOGLE = 'https://places.googleapis.com/v1';
const GOOGLE_CACHE_DAYS = 30;   // Google's own limit on holding Places content
const MAX_PHOTOS = 6;

const load = (slug) => JSON.parse(fs.readFileSync(path.join(CLIENTS, slug, 'business.json'), 'utf8'));
const save = (slug, b) => fs.writeFileSync(path.join(CLIENTS, slug, 'business.json'), JSON.stringify(b, null, 2) + '\n');

function openSlugs() {
  return fs.readdirSync(CLIENTS).filter((d) => {
    if (d.startsWith('example-')) return false;
    const f = path.join(CLIENTS, d, 'business.json');
    if (!fs.existsSync(f)) return false;
    const s = JSON.parse(fs.readFileSync(f, 'utf8')).status;
    return s !== 'dead' && s !== 'spec';
  });
}

// ---------------------------------------------------------------- 1. siteKind

async function fetchPage(url) {
  try {
    const res = await fetch(url, { redirect: 'follow', headers: { 'user-agent': UA, accept: 'text/html,*/*' },
      signal: AbortSignal.timeout(TIMEOUT) });
    const html = await res.text();
    return { status: res.status, finalUrl: res.url, html, bytes: Buffer.byteLength(html) };
  } catch (e) {
    return { error: e.message.split('\n')[0] };
  }
}

// The prospector's list, not the audit's: a site on one of these has someone
// already paid to look after it. WordPress and GoDaddy's builder are not on it
// — those are exactly the neglected sites we rebuild.
const PLATFORMS = [
  [/vagaro\.com/i, 'Vagaro'], [/booksy\.com/i, 'Booksy'], [/bukkii/i, 'Bukkii'],
  [/squarespace|static1\.squarespace/i, 'Squarespace'], [/wix\.com|_wixCssImports|X-Wix-/i, 'Wix'],
  [/cdn\.shopify|shopify/i, 'Shopify'],
];
// A challenge page announces itself in its URL or its title. The word
// "captcha" in a body is usually a contact form — LashBar and Eichman were
// both called challenges for having one.
const CHALLENGE_URL = /cdn-cgi\/challenge|\/\.well-known\/sgcaptcha|\/_Incapsula_Resource|distil_r_captcha/i;
const CHALLENGE_TITLE = /just a moment|attention required|robot challenge|checking your browser|verify you are human|access denied|security check|are you a robot/i;
const STOP = new Set(['the', 'and', 'inc', 'llc', 'co', 'of', 'a', 'an', 'at', 'in', 'for', 'dba', 'company', 'group', 'services', 'service']);

const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
const strip = (html) => html.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/gi, ' ').replace(/<[^>]+>/g, ' ');
const norm = (s) => String(s || '').toLowerCase().replace(/&amp;/g, '&').replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();

// Does the page ever say their name? Directory data is wrong constantly — an
// expired domain resold, a page on a competitor's site. Half the significant
// words of the name, or the domain's own stem, has to appear.
function namesBusiness(html, name, url) {
  const text = norm(strip(html)).slice(0, 200000);
  const words = norm(name).split(' ').filter((w) => w.length >= 3 && !STOP.has(w));
  if (!words.length) return true;   // nothing to test against; don't condemn on no evidence
  const hits = words.filter((w) => text.includes(w)).length;
  if (hits * 2 >= words.length) return true;
  try {
    const stem = new URL(url).hostname.replace(/^www\./, '').split('.')[0].replace(/[^a-z0-9]/g, '');
    if (stem.length >= 5 && norm(name).replace(/ /g, '').includes(stem)) return true;
  } catch { /* no url */ }
  return false;
}

// Domain marketplaces. A URL on one of these is proof of parking before a
// byte is fetched — Estrella's "site" was a HugeDomains sale page that
// Cloudflare 403'd to us, which read as a challenge until the URL was checked.
const PARKED_HOSTS = /(^|\.)(hugedomains|sedo|sedoparking|afternic|dan|undeveloped|domainmarket|buydomains|godaddy|namecheap|squadhelp|brandbucket)\.com$/i;

// The scout stores the URL a site redirected to. When that redirect was a
// bot challenge, the stored "site" is the challenge — seven of 34 open leads
// carried /.well-known/sgcaptcha/ as their currentSite. Fetch the origin
// instead, so the site gets a fair second look.
function startUrl(url) {
  if (!url) return url;
  try { return CHALLENGE_URL.test(url) ? new URL(url).origin + '/' : url; } catch { return url; }
}

function decideSiteKind(b, page) {
  if (!b.currentSite) return { siteKind: 'none' };
  // What the URL alone says, before trusting anything the server sent back.
  const startHost = host(b.currentSite), endHost = host(page.finalUrl || b.currentSite);
  if (PARKED_HOSTS.test(startHost) || PARKED_HOSTS.test(endHost)) return { siteKind: 'parked', reason: 'domain marketplace URL' };
  for (const [re, name] of PLATFORMS) if (re.test(b.currentSite) || (page.finalUrl && re.test(page.finalUrl))) return { siteKind: 'platform', platform: name };
  // Dead means the domain is gone or the page is, on the server's word. A
  // failed connection is OUR network as often as theirs — two live sites
  // were called dead from the sandbox — so that is 'unreachable', retried
  // next run, and never something the campaign acts on.
  if (page.error) {
    return /ENOTFOUND|EAI_AGAIN|getaddrinfo/i.test(page.error) ? { siteKind: 'dead', reason: 'domain does not resolve' }
                                                               : { siteKind: 'unreachable', reason: page.error };
  }
  const { status, html, bytes, finalUrl } = page;
  const title = (html.match(/<title[^>]*>([^<]*)<\/title>/i) || [])[1] || '';
  if (status === 404 || status === 410) return { siteKind: 'dead', reason: `HTTP ${status}` };
  // The challenge may be in the URL we landed on, the title, or — for a WAF
  // that hands back a stub which scripts its own redirect — in the body of
  // an otherwise empty 200. Those stubs read as "empty shell" until this
  // ran first; five SiteGround sites were called parked that way.
  if (CHALLENGE_URL.test(finalUrl || '') || CHALLENGE_TITLE.test(title) || CHALLENGE_URL.test(html.slice(0, 20000)) ||
      ((status === 403 || status === 503 || status === 429) && bytes < 20000)) {
    return { siteKind: 'challenge', reason: `HTTP ${status}` };
  }
  if (status >= 500) return { siteKind: 'unreachable', reason: `HTTP ${status}` };
  if (looksParked(html, bytes, !!b.phone)) return { siteKind: 'parked' };
  // GoDaddy's "/lander" is a 700-byte shell that scripts in "Website Coming
  // Soon". No text, no links, at that path, is a placeholder — three open
  // leads had one and read as 'own'. Same for any sub-2KB page with nothing
  // in it: whatever that is, it is not a website.
  const links = (html.match(/<a\s/gi) || []).length;
  const visible = norm(strip(html));
  if (/\/lander\/?$/i.test(finalUrl || '') && links < 3) return { siteKind: 'parked', reason: 'GoDaddy lander' };
  if (bytes < 2000 && !visible && links === 0) return { siteKind: 'parked', reason: 'empty shell' };
  for (const [re, name] of PLATFORMS) if (re.test(html.slice(0, 60000))) return { siteKind: 'platform', platform: name };
  // A script-rendered page has no text to judge by. That is not evidence the
  // site is somebody else's; the crawl's rendered DOM settles it (below).
  if (visible.length >= 300 && !namesBusiness(html, b.name, finalUrl)) return { siteKind: 'notTheirs' };
  const builder = (BUILDERS.find(([re]) => re.test(html)) || [])[1] || null;
  return { siteKind: 'own', builder, ...(visible.length < 300 ? { thin: true } : {}) };
}

function pageMeta(html) {
  const title = (html.match(/<title[^>]*>([^<]*)<\/title>/i) || [])[1] || '';
  const desc = (html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i) ||
                html.match(/<meta[^>]+content=["']([^"']*)["'][^>]+name=["']description["']/i) || [])[1] || '';
  return { title: title.trim().slice(0, 200), description: desc.trim().slice(0, 500) };
}

// ----------------------------------------------------------------- 2. JSON-LD

// The site's own structured data. Whoever built the site wrote this for
// Google; it is the closest thing to the owner filling in a form.
function jsonLd(html) {
  const blocks = [...html.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
  const nodes = [];
  for (const raw of blocks) {
    let v; try { v = JSON.parse(raw.trim()); } catch { continue; }
    const walk = (n) => { if (Array.isArray(n)) n.forEach(walk); else if (n && typeof n === 'object') { nodes.push(n); if (n['@graph']) walk(n['@graph']); } };
    walk(v);
  }
  const biz = nodes.filter((n) => n.openingHoursSpecification || n.openingHours || n.priceRange || n.aggregateRating ||
    (n.telephone && n.address) || /LocalBusiness|Store|Salon|Dentist|Plumber|Roofing|HVAC|Bakery|Restaurant|Cafe|Medical|Clinic|Insurance|Attorney|Florist|Gym|AutoRepair|Electrician|Contractor/i.test(String(n['@type'])));
  if (!biz.length) return null;
  const out = { types: [...new Set(biz.map((n) => n['@type']).flat().filter(Boolean))] };
  for (const n of biz) {
    for (const k of ['openingHours', 'openingHoursSpecification', 'priceRange', 'sameAs', 'telephone', 'email', 'description', 'aggregateRating', 'image', 'address', 'geo']) {
      if (n[k] !== undefined && out[k] === undefined) out[k] = n[k];
    }
  }
  return out;
}

// schema.org openingHoursSpecification → our {days, time, schema} rows.
const DAY = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY3 = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DAY2 = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const hhmm = (h, m) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
const ampm = (h, m) => `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`;

// Given per-day [{open:'09:00', close:'17:00'}] (index 0 = Sunday), group
// consecutive days Mon→Sun with identical hours into the rows the page shows.
function rowsFromDays(days) {
  const order = [1, 2, 3, 4, 5, 6, 0];
  const key = (d) => (days[d] || []).map((r) => `${r.open}-${r.close}`).join(',') || 'closed';
  const rows = [];
  let i = 0;
  while (i < order.length) {
    let j = i;
    while (j + 1 < order.length && key(order[j + 1]) === key(order[i])) j++;
    const a = order[i], z = order[j];
    const ranges = days[a] || [];
    const label = a === z ? DAY[a] : `${DAY3[a]}–${DAY3[z]}`;
    const code = a === z ? DAY2[a] : `${DAY2[a]}-${DAY2[z]}`;
    if (!ranges.length) rows.push({ days: label, time: 'Closed' });
    else {
      const time = ranges.map((r) => r.allDay ? 'Open 24 hours' : `${ampm(...r.open.split(':').map(Number))} – ${ampm(...r.close.split(':').map(Number))}`).join(', ');
      const schema = ranges.map((r) => `${code} ${r.allDay ? '00:00-23:59' : r.open + '-' + r.close}`).join(', ');
      rows.push({ days: label, time, schema });
    }
    i = j + 1;
  }
  // Trailing "Closed" rows past the last open day are noise ("Sunday: Closed" is not).
  return rows;
}

function hoursFromGoogle(reg) {
  if (!reg) return null;
  const days = Array.from({ length: 7 }, () => []);
  if (Array.isArray(reg.periods) && reg.periods.length) {
    for (const p of reg.periods) {
      const o = p.open; if (!o) continue;
      if (!p.close) { days[o.day].push({ allDay: true, open: '00:00', close: '23:59' }); continue; }
      days[o.day].push({ open: hhmm(o.hour || 0, o.minute || 0), close: hhmm(p.close.hour || 0, p.close.minute || 0) });
    }
    return rowsFromDays(days);
  }
  if (Array.isArray(reg.weekdayDescriptions)) {   // no periods (rare): keep Google's own wording
    return reg.weekdayDescriptions.map((line) => {
      const [d, ...rest] = line.split(':'); return { days: d.trim(), time: rest.join(':').trim() };
    });
  }
  return null;
}

function hoursFromJsonLd(ld) {
  const spec = ld && ld.openingHoursSpecification;
  if (!Array.isArray(spec) || !spec.length) return null;
  const days = Array.from({ length: 7 }, () => []);
  for (const s of spec) {
    const ds = [].concat(s.dayOfWeek || []).map((d) => DAY.findIndex((n) => String(d).toLowerCase().includes(n.toLowerCase()))).filter((i) => i >= 0);
    if (!ds.length || !s.opens || !s.closes) continue;
    for (const d of ds) days[d].push({ open: String(s.opens).slice(0, 5), close: String(s.closes).slice(0, 5) });
  }
  return days.some((d) => d.length) ? rowsFromDays(days) : null;
}

// ------------------------------------------------------------------ 3. Google

async function gFetch(url, key, { method = 'GET', mask, body } = {}) {
  const res = await fetch(url, {
    method, signal: AbortSignal.timeout(TIMEOUT),
    headers: { 'X-Goog-Api-Key': key, ...(mask ? { 'X-Goog-FieldMask': mask } : {}), 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Google ${res.status}: ${j.error?.message || res.statusText}`);
  return j;
}

const digits = (s) => String(s || '').replace(/\D/g, '').slice(-10);
// Dice coefficient on character bigrams — good enough to tell "Portal Salon"
// from "Portal Nails" and forgiving of "Salon" vs "Hair Salon".
function similar(a, b) {
  const grams = (s) => { const n = norm(s).replace(/ /g, ''); const g = new Map(); for (let i = 0; i < n.length - 1; i++) g.set(n.slice(i, i + 2), (g.get(n.slice(i, i + 2)) || 0) + 1); return g; };
  const A = grams(a), B = grams(b); let hit = 0;
  for (const [k, v] of A) hit += Math.min(v, B.get(k) || 0);
  const tot = [...A.values()].reduce((s, v) => s + v, 0) + [...B.values()].reduce((s, v) => s + v, 0);
  return tot ? (2 * hit) / tot : 0;
}

// Which of Google's candidates is this business? Phone and website are
// near-proof; the name alone is not (every city has three "Palm Dental").
function scoreCandidate(b, p) {
  let s = 0; const why = [];
  if (b.phone && digits(p.nationalPhoneNumber) && digits(p.nationalPhoneNumber) === digits(b.phone)) { s += 3; why.push('phone'); }
  if (b.currentSite && host(p.websiteUri) && host(p.websiteUri) === host(b.currentSite)) { s += 3; why.push('website'); }
  const sim = similar(b.name, p.displayName?.text || '');
  if (sim >= 0.8) { s += 3; why.push('name'); } else if (sim >= 0.55) { s += 2; why.push('name≈'); }
  const city = norm(b.address?.city || '');
  if (city && norm(p.formattedAddress || '').includes(city)) { s += 1; why.push('city'); }
  return { score: s, why, sim };
}

async function resolvePlace(b, key) {
  const a = b.address || {};
  const textQuery = [b.name, a.street, a.city, a.state].filter(Boolean).join(', ');
  const j = await gFetch(`${GOOGLE}/places:searchText`, key, {
    method: 'POST', body: { textQuery, maxResultCount: 5 },
    mask: 'places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri',
  });
  const scored = (j.places || []).map((p) => ({ p, ...scoreCandidate(b, p) })).sort((x, y) => y.score - x.score);
  const best = scored[0];
  if (best && best.score >= 3) return { resolved: true, placeId: best.p.id, matchedOn: best.why, name: best.p.displayName?.text };
  return { resolved: false, query: textQuery, candidates: scored.slice(0, 3).map((c) => ({ name: c.p.displayName?.text, address: c.p.formattedAddress, score: c.score })) };
}

const DETAIL_MASK = ['id', 'displayName', 'rating', 'userRatingCount', 'reviews', 'regularOpeningHours', 'photos',
  'editorialSummary', 'priceRange', 'priceLevel', 'websiteUri', 'nationalPhoneNumber', 'googleMapsUri',
  'primaryTypeDisplayName', 'businessStatus'].join(',');

async function placeDetails(placeId, key) {
  return gFetch(`${GOOGLE}/places/${placeId}`, key, { mask: DETAIL_MASK });
}

// Four-or-five-star, with something to say, newest first, at most three.
// Trimmed at a sentence so a cut never reads as a misquote.
function pickReviews(reviews, n = 3) {
  return (reviews || [])
    .map((r) => ({ author: r.authorAttribution?.displayName || '', stars: r.rating || 0,
                   text: (r.text?.text || r.originalText?.text || '').replace(/\s+/g, ' ').trim(), when: (r.publishTime || '').slice(0, 10) }))
    .filter((r) => r.author && r.stars >= 4 && r.text.length >= 40)
    .sort((x, y) => (y.when > x.when ? 1 : -1))
    .slice(0, n)
    .map((r) => {
      let t = r.text;
      if (t.length > 500) { const cut = t.slice(0, 500); const end = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('! '), cut.lastIndexOf('? ')); t = end > 200 ? cut.slice(0, end + 1) : cut.trim() + '…'; }
      return { author: r.author, stars: r.stars, text: t, source: 'Google', when: r.when };
    });
}

async function placePhotos(details, key, max, log) {
  const out = [];
  for (const ph of (details.photos || []).slice(0, max * 2)) {
    try {
      const meta = await gFetch(`${GOOGLE}/${ph.name}/media?maxWidthPx=1400&skipHttpRedirect=true`, key);
      if (!meta.photoUri) continue;
      const res = await fetch(meta.photoUri, { signal: AbortSignal.timeout(TIMEOUT) });
      if (!res.ok) continue;
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length < 4000) continue;
      const author = ph.authorAttributions?.[0]?.displayName || '';
      out.push({ buf, mime: res.headers.get('content-type') || 'image/jpeg', author,
                 owner: !!author && similar(author, details.displayName?.text || '') >= 0.8 });
      if (out.length >= max) break;
    } catch (e) { log(`    photo skipped — ${e.message.split('\n')[0]}`); }
  }
  // Owner uploads first: they are the ones most likely to be the place itself.
  return out.sort((x, y) => Number(y.owner) - Number(x.owner));
}

async function google(b, prior, { key, fresh, log }) {
  if (!key) return { skipped: 'no GOOGLE_MAPS_API_KEY' };
  const age = prior?.fetchedAt ? (Date.now() - Date.parse(prior.fetchedAt)) / 86400000 : Infinity;
  if (prior?.resolved && age < GOOGLE_CACHE_DAYS && !fresh) { log(`  google: cached ${Math.round(age)}d ago (--fresh to refetch)`); return { ...prior, cached: true }; }
  const r = prior?.resolved && prior.placeId && !fresh ? { resolved: true, placeId: prior.placeId, matchedOn: prior.matchedOn } : await resolvePlace(b, key);
  if (!r.resolved) { log(`  google: no confident match for "${r.query}"` + (r.candidates?.length ? ` — nearest: ${r.candidates.map((c) => c.name).join(' / ')}` : '')); return { resolved: false, ...r, fetchedAt: new Date().toISOString() }; }
  const d = await placeDetails(r.placeId, key);
  const out = {
    resolved: true, placeId: r.placeId, matchedOn: r.matchedOn, fetchedAt: new Date().toISOString(),
    name: d.displayName?.text, mapsUrl: d.googleMapsUri, websiteUri: d.websiteUri, phone: d.nationalPhoneNumber,
    rating: d.rating ?? null, reviewCount: d.userRatingCount ?? null, businessStatus: d.businessStatus,
    type: d.primaryTypeDisplayName?.text, priceRange: d.priceRange ? `${d.priceRange.startPrice?.units || ''}–${d.priceRange.endPrice?.units || ''}` : null,
    editorialSummary: d.editorialSummary?.text || null,
    hours: hoursFromGoogle(d.regularOpeningHours),
    reviews: pickReviews(d.reviews, 5),
    allReviews: (d.reviews || []).map((x) => ({ author: x.authorAttribution?.displayName, stars: x.rating, when: (x.publishTime || '').slice(0, 10), text: (x.text?.text || '').slice(0, 800) })),
    photoCount: (d.photos || []).length,
    _details: d,   // kept on the object for --apply's photo fetch; not written
  };
  log(`  google: ${out.name} · ${out.rating ?? '–'}★ (${out.reviewCount ?? 0}) · ${out.reviews.length} usable reviews · ${out.hours ? 'hours' : 'no hours'} · ${out.photoCount} photos · matched on ${r.matchedOn.join('+')}`);
  return out;
}

// ------------------------------------------------------------------- 4. crawl

async function crawl(slug, log) {
  try {
    const harvest = require('./harvest');
    const out = await harvest(slug, { write: false, log: (l) => log('  ' + l) });
    log(`  crawl: ${out.pagesRead.length} pages · ${out.quotes.length} quotes · ${out.hours.length} hours lines · ${out.prices.length} prices`);
    return out;
  } catch (e) {
    const msg = e.message.split('\n')[0];
    log(`  crawl: skipped — ${msg}`);
    return { error: msg };
  }
}

// ------------------------------------------------------------- 5. CSLB
//
// Not automated. CSLB's public lookup has no API — classic ASP.NET
// WebForms, a viewstate postback to a detail page. In testing that flow
// worked cleanly once, against a real license (Helix Mechanical, #834736,
// confirmed active). Ten-odd requests later, spread over several minutes
// with a courtesy delay between them, the same endpoint answered "Request
// Rejected... consult with your administrator" — a WAF declining automated
// traffic. That is the site's own bot-defense saying no, the same category
// of signal as DCA's Cloudflare Turnstile and the CA Secretary of State's
// Akamai block on its search API — both of those are skipped entirely for
// the same reason. This one is not built around either.
//
// What's left is harmless and costs no request: recognizing a CSLB-shaped
// number already sitting in business.json, so research can point a human
// at cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx to check
// it by hand — one person, one click-through, which is what that form is
// actually for.
function extractCslbNumber(license) {
  const m = String(license || '').match(/\b(\d{6,7})\b/);
  return m ? m[1] : null;
}

// ------------------------------------------------------------- 6. RDAP
//
// Domain age, from the standard RDAP protocol — no key, no bot-protection,
// well-behaved. Kept for internal use only: a `_` field, never rendered.
// "This domain has been registered since 2003" is not "in business since
// 2003" — they could have moved onto a new domain last year and this would
// say nothing true about them. It is a weak signal, worth having, never a
// claim.
async function domainAge(hostname, log) {
  if (!hostname) return null;
  try {
    const res = await fetch(`https://rdap.org/domain/${hostname}`, { redirect: 'follow', headers: { 'user-agent': UA, accept: 'application/rdap+json' }, signal: AbortSignal.timeout(TIMEOUT) });
    if (!res.ok) return null;
    const d = await res.json();
    const reg = (d.events || []).find((e) => e.eventAction === 'registration');
    if (!reg) return null;
    const years = (Date.now() - Date.parse(reg.eventDate)) / (365.25 * 86400000);
    return { registered: reg.eventDate.slice(0, 10), years: Math.round(years * 10) / 10 };
  } catch (e) {
    log(`  domain age: skipped — ${e.message.split('\n')[0]}`);
    return null;
  }
}

// ------------------------------------------------------------- 7. wider OSM tags
//
// scout.js's Overpass query already asks for every tag on the node
// ("out tags center") — toLeads() just throws all but five of them away.
// So this costs nothing new: whatever survived into `_scout.osmTags` at
// scout time (only present on leads scouted after this shipped) is read
// here. opening_hours is OSM's own mini-language, not schema.org's — this
// parses the common shapes (day ranges, one time range per group, "off",
// "24/7") and returns null on anything it cannot read with confidence,
// same rule as everywhere else: an unparsed spec is not a guessed one.
function hoursFromOsm(spec) {
  if (!spec || typeof spec !== 'string') return null;
  const s = spec.trim();
  if (/^24\/7$/i.test(s)) return [{ days: 'Every day', time: 'Open 24 hours', schema: 'Mo-Su 00:00-23:59' }];
  // Reject anything with syntax this parser does not model, rather than
  // guess at it: fallback groups ("||"), comments, holiday rules, week
  // numbers, or a comma inside a single time spec (multiple ranges in one
  // day — real, just not handled here). A run of ";"-joined day groups,
  // the shape almost every real listing uses, is exactly what this parses.
  if (/\|\||\(|PH|SH|week|easter|\d{2}:\d{2}\s*,/i.test(s) || (s.match(/;/g) || []).length > 8) return null;
  const DAY_RE = /^(Mo|Tu|We|Th|Fr|Sa|Su)(-(Mo|Tu|We|Th|Fr|Sa|Su))?((,(Mo|Tu|We|Th|Fr|Sa|Su)(-(Mo|Tu|We|Th|Fr|Sa|Su))?)*)$/;
  const order = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  const rows = [];
  for (const clause of s.split(';').map((c) => c.trim()).filter(Boolean)) {
    const m = clause.match(/^([A-Za-z,\-]+)\s+(off|closed|(\d{2}:\d{2})-(\d{2}:\d{2}))$/i);
    if (!m || !DAY_RE.test(m[1])) return null;
    const days = [];
    for (const part of m[1].split(',')) {
      const [a, z] = part.split('-');
      const ai = order.indexOf(a), zi = order.indexOf(z || a);
      if (ai < 0 || zi < 0) return null;
      if (zi >= ai) for (let i = ai; i <= zi; i++) days.push(order[i]);
      else { for (let i = ai; i < 7; i++) days.push(order[i]); for (let i = 0; i <= zi; i++) days.push(order[i]); }
    }
    const closed = /^(off|closed)$/i.test(m[2]);
    const label = closed ? 'Closed' : `${ampm(...m[3].split(':').map(Number))} – ${ampm(...m[4].split(':').map(Number))}`;
    const schemaFrag = closed ? null : `${m[3]}-${m[4]}`;
    for (const d of days) rows.push({ day: d, label, schemaFrag });
  }
  if (!rows.length) return null;
  // Group consecutive Mon→Sun days with identical hours, same shape as
  // rowsFromDays elsewhere in this file.
  const byDay = Object.fromEntries(rows.map((r) => [r.day, r]));
  const seq = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
  const full = { Sunday: 'Su', Monday: 'Mo', Tuesday: 'Tu', Wednesday: 'We', Thursday: 'Th', Friday: 'Fr', Saturday: 'Sa' };
  const nameOf = Object.fromEntries(Object.entries(full).map(([k, v]) => [v, k]));
  const out = [];
  let i = 0;
  while (i < seq.length) {
    const d = seq[i];
    if (!byDay[d]) { i++; continue; }
    let j = i;
    while (j + 1 < seq.length && byDay[seq[j + 1]] && byDay[seq[j + 1]].label === byDay[d].label) j++;
    const label = i === j ? nameOf[seq[i]] : `${DAY3[order.indexOf(seq[i]) === 0 ? 0 : ['Su','Mo','Tu','We','Th','Fr','Sa'].indexOf(seq[i])]}`;
    const a = seq[i], z = seq[j];
    const days = a === z ? nameOf[a] : `${nameOf[a].slice(0, 3)}–${nameOf[z].slice(0, 3)}`;
    const code = a === z ? a : `${a}-${z}`;
    out.push({ days, time: byDay[d].label, ...(byDay[d].schemaFrag ? { schema: `${code} ${byDay[d].schemaFrag}` } : {}) });
    i = j + 1;
  }
  return out;
}

function fromOsmTags(tags) {
  if (!tags || typeof tags !== 'object') return {};
  const out = {};
  const hours = hoursFromOsm(tags.opening_hours);
  if (hours) out.hours = hours;
  const insta = tags['contact:instagram'] || tags.instagram;
  const fb = tags['contact:facebook'] || tags.facebook;
  if (insta || fb) out.social = [insta, fb].filter(Boolean);
  if (tags.wheelchair) out.wheelchair = tags.wheelchair;   // 'yes' | 'limited' | 'no'
  const payment = Object.entries(tags).filter(([k, v]) => k.startsWith('payment:') && v === 'yes').map(([k]) => k.slice('payment:'.length));
  if (payment.length) out.payment = payment;
  if (tags.cuisine) out.cuisine = tags.cuisine.split(';');
  if (tags.outdoor_seating) out.outdoorSeating = tags.outdoor_seating === 'yes';
  return out;
}

// ------------------------------------------------------------------- --apply

const PLACEHOLDER_HOURS_SIG = require('./render').PLACEHOLDER_HOURS_SIG;
const hasRealHours = (b) => (b.hours || []).some((h) => h.time) &&
  (b.hours || []).map((h) => h.schema || '').filter(Boolean).join('|') !== PLACEHOLDER_HOURS_SIG;
const hasReviews = (b) => (b.reviews || []).some((r) => r && r.text);

async function applyPhotos(b, photos, log) {
  if (!photos.length) return 0;
  const { keepDistinct } = require('./dedupe-images');
  const { embed } = require('./embed-photo');
  const existing = (b.photos || []).map((p) => {
    const m = /^data:(image\/[a-z+]+);base64,(.+)$/s.exec(typeof p === 'string' ? p : p.src || '');
    return m ? { buf: Buffer.from(m[2], 'base64'), mime: m[1] } : null;
  }).filter(Boolean);
  const room = MAX_PHOTOS - (b.photos || []).length;
  if (room <= 0) return 0;
  const pool = [...existing, ...photos];
  const keep = await keepDistinct(pool.map((p) => ({ buf: p.buf, mime: p.mime })));
  const fresh = keep.filter((i) => i >= existing.length).slice(0, room).map((i) => pool[i]);
  if (!fresh.length) return 0;
  const tmp = require('os').tmpdir();
  const files = fresh.map((p, i) => { const f = path.join(tmp, `research-${Date.now()}-${i}.${p.mime.includes('png') ? 'png' : 'jpg'}`); fs.writeFileSync(f, p.buf); return f; });
  const embedded = await embed(files);
  files.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  b.photos = [...(b.photos || []), ...embedded.map((e, i) => ({
    src: e.src, alt: `${b.name} — photo ${(b.photos || []).length + i + 1}`,
    from: { source: 'google', author: fresh[i].author, owner: fresh[i].owner, url: b.google?.mapsUrl || '' },
  }))];
  return embedded.length;
}

async function apply(slug, b, h, { key, log }) {
  const applied = {};
  b.siteKind = h.siteKind;
  if (h.site?.platform) b.sitePlatform = h.site.platform;
  const g = h.google;
  if (g?.resolved) {
    b.google = { placeId: g.placeId, mapsUrl: g.mapsUrl, rating: g.rating, reviewCount: g.reviewCount, fetchedAt: g.fetchedAt };
    if (!b.rating && g.rating && g.reviewCount) b.rating = { value: g.rating, count: g.reviewCount, source: 'Google' };
  }
  // OSM's own opening_hours, when Google and JSON-LD both came up empty —
  // it costs nothing new (the tags were already fetched at scout time) and
  // it is the site owner's or a mapper's own word, structured, for free.
  const osm = fromOsmTags(h.osmTags);
  if (!hasRealHours(b)) {
    const hours = (g?.resolved && g.hours) || hoursFromJsonLd(h.jsonld) || osm.hours;
    if (hours && hours.some((r) => r.schema)) {
      b.hours = hours; applied.hours = g?.hours ? 'google' : h.jsonld?.openingHoursSpecification ? 'jsonld' : 'osm';
    }
  }
  if (!hasReviews(b) && g?.resolved && g.reviews?.length) { b.reviews = g.reviews.slice(0, 3); applied.reviews = 'google'; }
  if (g?.resolved && g._details && key) {
    try {
      const photos = await placePhotos(g._details, key, MAX_PHOTOS, log);
      const n = await applyPhotos(b, photos, log);
      if (n) applied.photos = n;
    } catch (e) { log(`  photos: skipped — ${e.message.split('\n')[0]}`); }
  }
  if (!b.social && osm.social?.length) { b.social = osm.social; applied.social = 'osm'; }

  // CSLB is not queried automatically (see the comment above extractCslbNumber).
  // A number that looks like one is just pointed out for a human to check.
  const licNo = extractCslbNumber(b.license);
  if (licNo && b.address?.state === 'CA' && !b.licenseCheck) {
    log(`  cslb: #${licNo} on file, not verified — check by hand at cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx`);
  }

  // Domain age: internal only, `_`-prefixed, never a page claim.
  const host = (() => { try { return new URL(b.currentSite).hostname.replace(/^www\./, ''); } catch { return null; } })();
  if (host) {
    const age = await domainAge(host, log);
    if (age) { b._domainAge = age; log(`  domain age: registered ${age.registered} (${age.years}y) — internal only, never a page claim`); }
  }

  b._research = { at: new Date().toISOString().slice(0, 10), applied: Object.keys(applied) };
  save(slug, b);
  const what = Object.entries(applied).map(([k, v]) => `${k}${typeof v === 'number' ? ' ×' + v : ' from ' + v}`).join(', ');
  log(`  applied: siteKind=${b.siteKind}${what ? ', ' + what : ''}`);
  return applied;
}

// -------------------------------------------------------------------- main

async function research(slug, { apply: doApply = false, fresh = false, noCrawl = false, log = console.log } = {}) {
  const b = load(slug);
  const hFile = path.join(CLIENTS, slug, 'harvest.json');
  const prior = fs.existsSync(hFile) ? JSON.parse(fs.readFileSync(hFile, 'utf8')) : {};
  log(`\n${slug}${b.currentSite ? ' — ' + b.currentSite : ' — no site listed'}`);

  const page = b.currentSite ? await fetchPage(startUrl(b.currentSite)) : {};
  const kind = decideSiteKind(b, page);
  const meta = page.html ? pageMeta(page.html) : {};
  log(`  site: ${kind.siteKind}${kind.platform ? ' (' + kind.platform + ')' : ''}${kind.builder ? ' · ' + kind.builder : ''}${kind.reason ? ' · ' + kind.reason : ''}${meta.title ? ' · "' + meta.title.slice(0, 60) + '"' : ''}`);

  const ld = kind.siteKind === 'own' && page.html ? jsonLd(page.html) : null;
  if (ld) log(`  json-ld: ${ld.types.join('/')}${ld.openingHoursSpecification || ld.openingHours ? ' · hours' : ''}${ld.priceRange ? ' · ' + ld.priceRange : ''}${ld.sameAs ? ' · ' + [].concat(ld.sameAs).length + ' socials' : ''}`);

  const g = await google(b, prior.google, { key: process.env.GOOGLE_MAPS_API_KEY, fresh, log });
  if (g.skipped) log(`  google: skipped — ${g.skipped}`);

  const c = noCrawl ? { skipped: '--no-crawl' } : kind.siteKind === 'own' ? await crawl(slug, log) : { skipped: `site is ${kind.siteKind}` };
  if (c.skipped) log(`  crawl: skipped — ${c.skipped}`);
  // The rendered DOM is the authority on whether the page names them.
  if (c.namesBusiness === false) { kind.siteKind = 'notTheirs'; kind.reason = 'rendered page never names them'; log('  site: notTheirs — the rendered page never names them'); }
  // A crawl that could not run here must not erase one that ran in Actions.
  const crawlOut = c.error || c.skipped ? (prior.pagesRead ? { ...pickCrawl(prior), crawlNote: c.error || c.skipped } : { crawlNote: c.error || c.skipped }) : c;

  const osmTags = b._scout?.osmTags || null;
  if (osmTags) log(`  osm: ${Object.keys(fromOsmTags(osmTags)).join(', ') || 'no usable tags'}`);

  const { _details, ...gStored } = g;
  const out = {
    _readMe: 'Everything research.js could find, from every source, raw. NOTHING here is verified. ' +
             '--apply wrote only the structured, attributed parts (siteKind, Google hours/reviews/photos, ' +
             'OSM hours/social) into business.json; services and headline still need a person to read ' +
             'this. A CSLB-shaped license number is pointed out, never fetched — see extractCslbNumber. ' +
             '_domainAge, when present, is internal only — never a page claim.',
    researchedAt: new Date().toISOString().slice(0, 10),
    siteKind: kind.siteKind,
    site: { url: b.currentSite || null, finalUrl: page.finalUrl || null, status: page.status ?? null,
            platform: kind.platform || null, builder: kind.builder || null, ...meta, reason: kind.reason || null },
    jsonld: ld,
    google: gStored,
    osmTags,
    ...crawlOut,
  };
  fs.writeFileSync(hFile, JSON.stringify(out, null, 2));

  let applied = null;
  if (doApply) applied = await apply(slug, b, { ...out, google: g, osmTags }, { key: process.env.GOOGLE_MAPS_API_KEY, log });
  return { slug, siteKind: kind.siteKind, google: { resolved: !!g.resolved }, applied };
}

const CRAWL_KEYS = ['harvestedAt', 'from', 'namesBusiness', 'pagesRead', 'emails', 'phones', 'hours', 'people', 'prices', 'social', 'headings', 'quotes', 'pageText'];
const pickCrawl = (h) => Object.fromEntries(CRAWL_KEYS.filter((k) => h[k] !== undefined).map((k) => [k, h[k]]));

module.exports = { research, openSlugs, decideSiteKind, namesBusiness, jsonLd, hoursFromGoogle, hoursFromJsonLd, pickReviews, scoreCandidate, similar, hoursFromOsm, fromOsmTags, extractCslbNumber, domainAge };

if (require.main === module) {
  const argv = process.argv.slice(2);
  const all = argv.includes('--all');
  const slugs = all ? openSlugs() : argv.filter((a) => !a.startsWith('--'));
  if (!slugs.length) { console.error('Usage: node tools/research.js <slug> [--apply] [--fresh]   |   --all [--apply]'); process.exit(2); }
  (async () => {
    const tally = {};
    for (const s of slugs) {
      try { const r = await research(s, { apply: argv.includes('--apply'), fresh: argv.includes('--fresh'), noCrawl: argv.includes('--no-crawl') }); tally[r.siteKind] = (tally[r.siteKind] || 0) + 1; }
      catch (e) { console.log(`  ✗ ${s}: ${e.message.split('\n')[0]}`); tally.failed = (tally.failed || 0) + 1; }
    }
    console.log('\n' + Object.entries(tally).map(([k, v]) => `${v} ${k}`).join(' · '));
  })();
}
