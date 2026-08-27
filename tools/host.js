// Turns a built client into a folder a host can serve, and refuses to do it
// while anything on the page is still ours rather than theirs.
//
// The gate matters more than the folder. Everything on a spec page starts as a
// placeholder — a phone number in the reserved fiction range, prices we picked
// so the menu would work, an email at a domain nobody owns yet. All of that is
// fine in an attachment and none of it is fine on a live site, where a wrong
// email silently swallows enquiries and a price we invented is one the owner
// has to honour.

const fs = require('fs');
const path = require('path');
const render = require('./render');

const ROOT = path.join(__dirname, '..');

// 555-0100 to 555-0199 is the range reserved for fiction. Anything else in it
// is a real number belonging to a real stranger.
const FAKE_PHONE = /\b555[-.\s]?01\d\d\b/;

// What the owner has to have signed off before their name goes on it.
const SIGNOFF = {
  prices: 'every price on the page',
  email: 'the email address enquiries go to',
  hours: 'the opening hours',
  area: 'the towns in the service area',
};

function preflight(slug, b) {
  const stop = [];
  const warn = [];

  if (FAKE_PHONE.test(b.phone || '')) {
    stop.push(`phone is still the placeholder (${b.phone}) — put their real number in`);
  }
  if (!b.phone) stop.push('no phone number, which is the only thing the page is really for');

  const signed = b.confirmed || {};
  for (const [key, what] of Object.entries(SIGNOFF)) {
    if (signed[key] !== true) stop.push(`${what} — not confirmed by the owner yet ("confirmed": { "${key}": true })`);
  }

  // An email on a domain that is not live yet bounces, and nobody finds out
  // until the enquiries have already been lost.
  const mail = String(b.email || '');
  if (mail && b.liveUrl) {
    const at = mail.split('@')[1] || '';
    let host = '';
    try { host = new URL(b.liveUrl).hostname.replace(/^www\./, ''); } catch { /* checked below */ }
    if (at && host && at.toLowerCase() === host.toLowerCase() && signed.email !== true) {
      stop.push(`${mail} is on the site's own domain — check that mailbox actually exists before it goes live`);
    }
  }

  if (!b.liveUrl) {
    stop.push('no liveUrl — set it to the address this will be served from, so the page can name itself');
  } else {
    try {
      const u = new URL(b.liveUrl);
      if (u.protocol !== 'https:') stop.push(`liveUrl is ${u.protocol}// — it has to be https`);
    } catch { stop.push(`liveUrl is not a valid URL: ${b.liveUrl}`); }
  }

  if ((b.status || '') === 'spec') {
    stop.push('status is still "spec" — set it to "won" when they have actually said yes');
  }

  if (!(b.reviews || []).length) warn.push('no reviews on the page — the one gap our own checks flag');
  if (!(b.address || {}).street) warn.push('no street address — fine for a mobile service, worth knowing');
  if (!(b.photos || []).length) warn.push('no photos of their work');

  return { stop, warn };
}

// Cloudflare Pages and Netlify both read _headers. The page pulls in nothing
// from anywhere, so the policy can be as tight as it goes.
const HEADERS = `/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'
`;

function build(slug, { force = false } = {}) {
  const dir = path.join(ROOT, 'clients', slug);
  const f = path.join(dir, 'business.json');
  if (!fs.existsSync(f)) throw new Error(`no such client: ${slug}`);
  const b = JSON.parse(fs.readFileSync(f, 'utf8'));

  const { stop, warn } = preflight(slug, b);
  if (stop.length && !force) return { blocked: true, stop, warn, b };

  const out = path.join(ROOT, 'sites', slug);
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, 'index.html'), render(b));
  fs.writeFileSync(path.join(out, '_headers'), HEADERS);

  const url = (b.liveUrl || '').replace(/\/$/, '');
  fs.writeFileSync(path.join(out, 'robots.txt'),
    `User-agent: *\nAllow: /\n${url ? `\nSitemap: ${url}/sitemap.xml\n` : ''}`);
  if (url) {
    fs.writeFileSync(path.join(out, 'sitemap.xml'),
      `<?xml version="1.0" encoding="UTF-8"?>\n` +
      `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
      `  <url>\n    <loc>${url}/</loc>\n` +
      `    <lastmod>${new Date().toISOString().slice(0, 10)}</lastmod>\n` +
      `  </url>\n</urlset>\n`);
  }

  return { blocked: false, stop, warn, b, out, files: fs.readdirSync(out).sort() };
}

module.exports = build;
module.exports.preflight = preflight;
