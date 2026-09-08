// Pulls real photos off a business's own site — plain HTTP, same technique
// quicklook.js already uses reliably for email. Works well for server-
// rendered sites (WordPress, mostly); finds nothing on JS-rendered ones
// (GoDaddy Website Builder, some React/Vue sites) where the real markup only
// exists after client-side hydration — same limitation quicklook already
// has for email, handled the same way: find what's really there, invent
// nothing, and leave the gallery off the page when nothing real turns up.

const path = require('path');
const { embed } = require('./embed-photo');

const TIMEOUT = 10000;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

// Not a photo of the business: logos, icons, tracking pixels, stock
// placeholder assets, WordPress/theme furniture.
const SKIP = /logo|icon|favicon|sprite|pixel|spacer|placeholder|avatar|badge|banner-ad|wp-includes|gravatar|elementor-placeholder/i;

function imageUrlsIn(html, baseUrl) {
  const raw = [...html.matchAll(/<img[^>]+(?:src|data-src)=["']([^"']+)["']/gi)].map((m) => m[1]);
  const out = [];
  for (const u of raw) {
    if (!u || u.startsWith('data:')) continue;
    let abs;
    try { abs = new URL(u, baseUrl).href; } catch { continue; }
    if (SKIP.test(abs)) continue;
    if (!/\.(jpe?g|png|webp)(\?|$)/i.test(abs)) continue;
    out.push(abs);
  }
  return [...new Set(out)];
}

async function fetchBuffer(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT), headers: { 'user-agent': UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('content-type') || '';
  if (!/^image\//i.test(ct)) throw new Error(`not an image (${ct})`);
  return Buffer.from(await res.arrayBuffer());
}

// Finds up to `max` real photo URLs on a site. Returns [] rather than
// guessing when the page is JS-rendered and nothing is really there.
async function findPhotoUrls(siteUrl, max = 4) {
  const start = /^https?:\/\//i.test(siteUrl) ? siteUrl : 'https://' + siteUrl;
  const res = await fetch(start, { signal: AbortSignal.timeout(TIMEOUT), headers: { 'user-agent': UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const html = await res.text();
  return imageUrlsIn(html, start).slice(0, max);
}

// Downloads and embeds (resized data URIs, via the same tool ./cc photo
// uses for hand-picked local files) up to `max` real photos from the site.
// Skips any single image that fails to fetch or decode rather than aborting
// the whole batch — one broken URL on their page shouldn't cost the rest.
async function embedFromSite(siteUrl, max = 4) {
  const urls = await findPhotoUrls(siteUrl, max);
  if (!urls.length) return [];

  const tmp = require('os').tmpdir();
  const fs = require('fs');
  const files = [];
  for (const [i, url] of urls.entries()) {
    try {
      const buf = await fetchBuffer(url);
      if (buf.length < 4000) continue;   // smaller than any real photo — a 1x1 tracker or a broken placeholder
      const ext = (url.match(/\.(jpe?g|png|webp)(\?|$)/i) || [, 'jpg'])[1].toLowerCase();
      const f = path.join(tmp, `photo-${Date.now()}-${i}.${ext}`);
      fs.writeFileSync(f, buf);
      files.push(f);
    } catch { /* skip this one, keep going */ }
  }
  if (!files.length) return [];

  const embedded = await embed(files);
  files.forEach((f) => { try { fs.unlinkSync(f); } catch {} });
  return embedded.map((e) => ({ src: e.src }));
}

module.exports = { findPhotoUrls, embedFromSite };
