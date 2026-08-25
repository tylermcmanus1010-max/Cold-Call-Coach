// Fetches a business website and scores it against the 12 checks automatically.
// This is the part that used to take you ten minutes per lead.

const CHECKS = require('./checks');
const UA = 'Mozilla/5.0 (compatible; site-audit/1.0)';

const BUILDERS = [
  [/wix\.com|_wixCssImports|X-Wix-/i, 'Wix'],
  [/squarespace|static1\.squarespace/i, 'Squarespace'],
  [/godaddy|starfieldtech|websitebuilder/i, 'GoDaddy builder'],
  [/weebly|editmysite/i, 'Weebly'],
  [/wp-content|wp-includes/i, 'WordPress'],
  [/shopify|cdn\.shopify/i, 'Shopify'],
  [/webs\.com|homestead|networksolutions|yellowpages\.com\/website/i, 'legacy builder'],
];

const PARKED = /this domain (is|may be) for sale|parked (free )?courtesy|godaddy\.com\/domainsearch|domain( name)? expired|coming soon|under construction|site temporarily unavailable/i;

async function grab(url, timeoutMs) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  const started = Date.now();
  try {
    const res = await fetch(url, {
      redirect: 'follow', signal: ctl.signal,
      headers: { 'user-agent': UA, accept: 'text/html,*/*' },
    });
    const html = await res.text();
    return { ok: true, status: res.status, finalUrl: res.url, html, ms: Date.now() - started, bytes: html.length };
  } catch (e) {
    return { ok: false, error: e.name === 'AbortError' ? `timeout after ${timeoutMs}ms` : e.message, ms: Date.now() - started };
  } finally { clearTimeout(t); }
}

// Pull whatever the site already publishes about itself, so business.json
// arrives half-filled instead of empty.
function extract(html) {
  const out = {};
  const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (title) out.title = title[1].replace(/\s+/g, ' ').trim();
  const desc = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)/i);
  if (desc) out.description = desc[1].trim();

  const tel = html.match(/href=["']tel:([^"']+)/i);
  const loose = html.match(/\(?\b([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b/);
  if (tel) out.phone = tel[1].trim();
  else if (loose) out.phone = `(${loose[1]}) ${loose[2]}-${loose[3]}`;

  const zip = html.match(/\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),?\s+(CA|California)\s+(9\d{4})\b/);
  if (zip) out.cityState = { city: zip[1], state: 'CA', zip: zip[3] };

  const street = html.match(/\b(\d{1,6}\s+(?:[NSEW]\.?\s+)?[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,2}\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Way|Ln|Lane|Ct|Court|Pl|Place|Pkwy|Parkway|Hwy|Highway))\.?\b/);
  if (street) out.street = street[1].replace(/\s+/g, ' ').trim();

  const years = [...html.matchAll(/(?:©|&copy;|copyright)[^0-9]{0,20}((?:19|20)\d{2})/gi)].map((m) => +m[1]);
  if (years.length) out.copyrightYear = Math.max(...years);

  for (const [re, name] of BUILDERS) if (re.test(html)) { out.builder = name; break; }

  // If they already ship LocalBusiness JSON-LD, take the good data straight out.
  for (const m of html.matchAll(/<script[^>]+application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)) {
    try {
      const nodes = [].concat(JSON.parse(m[1].trim()));
      for (const n of nodes.flatMap((x) => x['@graph'] || [x])) {
        if (!/business|store|restaurant|service|organization|shop/i.test(n['@type'] || '')) continue;
        out.ldName = out.ldName || n.name;
        out.ldPhone = out.ldPhone || n.telephone;
        if (n.address?.streetAddress) out.ldAddress = {
          street: n.address.streetAddress, city: n.address.addressLocality,
          state: n.address.addressRegion, zip: n.address.postalCode,
        };
        if (n.aggregateRating) out.ldRating = { value: n.aggregateRating.ratingValue, count: n.aggregateRating.reviewCount };
      }
    } catch { /* malformed JSON-LD is itself a finding, not a crash */ }
  }
  return out;
}

function score(html, page, httpsWorked) {
  const h = html;
  const has = (re) => re.test(h);
  return {
    https:    httpsWorked,
    mobile:   has(/<meta[^>]+name=["']viewport["'][^>]+width\s*=\s*device-width/i),
    speed:    page.ms < 2500 && page.bytes < 1_500_000,
    phoneTap: has(/href=["']tel:/i),
    hours:    has(/\b(mon|tues?|wed|thur?s?|fri|sat|sun)[a-z]*\.?\s*[-–—:]/i) || has(/\bhours\b[\s\S]{0,120}\d{1,2}\s*(:\d{2})?\s*(am|pm)/i),
    address:  has(/\b\d{1,6}\s+[A-Z][A-Za-z.]*\s+(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|way|ln|lane|ct|pl|pkwy|hwy)\b/i) && has(/\b9\d{4}\b/),
    services: has(/\$\s?\d/) ,
    reviews:  has(/testimonial|review/i) && has(/★|⭐|stars?\b|yelp|google review/i),
    cta:      has(/href=["']tel:/i) || has(/\b(call (us )?now|book (online|now|an? appointment)|schedule (a |your )?(service|appointment)|free (estimate|quote|consultation)|request a quote)\b/i),
    seo:      has(/application\/ld\+json/i),
    meta:     has(/<title[^>]*>\s*\S[\s\S]{4,}?<\/title>/i)
              && !has(/<title[^>]*>\s*(untitled document|home|welcome|index|new page \d*|my site|website)\s*<\/title>/i)
              && has(/<meta[^>]+name=["']description["'][^>]+content=["']\s*\S/i),
    social:   has(/property=["']og:(title|image|description)["']/i),
  };
}

// A dead or missing site is the strongest lead there is, so it scores as a
// full miss on everything rather than being dropped from the list.
const allFalse = () => Object.fromEntries(CHECKS.map((c) => [c.key, false]));

async function audit(rawUrl, { timeout = 12000 } = {}) {
  if (!rawUrl) return { url: null, reachable: false, reason: 'no website', checks: allFalse(), gaps: CHECKS.length, info: {} };

  const bare = String(rawUrl).replace(/^https?:\/\//i, '').replace(/\/+$/, '');
  const https = await grab('https://' + bare, timeout);
  let page = https, httpsWorked = https.ok && https.status < 400;

  if (!httpsWorked) {
    const http = await grab('http://' + bare, timeout);
    if (http.ok && http.status < 400) { page = http; httpsWorked = false; }
  }

  if (!page.ok || page.status >= 400) {
    return {
      url: bare, reachable: false,
      reason: page.ok ? `HTTP ${page.status}` : page.error,
      checks: allFalse(), gaps: CHECKS.length, info: {},
    };
  }

  const info = extract(page.html);
  const stats = { ms: page.ms, kb: Math.round(page.bytes / 1024) };
  if (PARKED.test(page.html) || (page.bytes < 600 && !info.phone)) {
    return { url: bare, finalUrl: page.finalUrl, reachable: true, reason: 'parked or placeholder page',
             ...stats, checks: allFalse(), gaps: CHECKS.length, info };
  }

  const checks = score(page.html, page, httpsWorked);
  const gaps = CHECKS.filter((c) => !checks[c.key]).length;
  const stale = info.copyrightYear && info.copyrightYear < new Date().getFullYear() - 2;

  return {
    url: bare, finalUrl: page.finalUrl, reachable: true,
    ms: page.ms, kb: Math.round(page.bytes / 1024),
    checks, gaps, info, stale,
    reason: [stale && `© ${info.copyrightYear}`, info.builder].filter(Boolean).join(', ') || null,
  };
}

module.exports = { audit, CHECKS };
