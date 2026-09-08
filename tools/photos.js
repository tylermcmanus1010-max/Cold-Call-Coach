// Pulls real photos off a business's own site — plain HTTP, same technique
// quicklook.js already uses reliably for email. Works well for server-
// rendered sites (WordPress, mostly); finds nothing on JS-rendered ones
// (GoDaddy Website Builder, some React/Vue sites) where the real markup only
// exists after client-side hydration — same limitation quicklook already
// has for email, handled the same way: find what's really there, invent
// nothing, and leave the gallery off the page when nothing real turns up.

const path = require('path');
const { embed } = require('./embed-photo');
const { keepDistinct } = require('./dedupe-images');
const { guessKind } = require('./photo-kind');

const TIMEOUT = 10000;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

// Not a photo of the business: logos, icons, tracking pixels, stock
// placeholder assets, WordPress/theme furniture.
const SKIP = /logo|icon|favicon|sprite|pixel|spacer|placeholder|avatar|badge|banner-ad|wp-includes|gravatar|elementor-placeholder/i;

// Returns { url, alt } per image. The alt is kept because it is the site's
// own word for what the photo shows — the only evidence a plain fetch has
// (no rendered DOM, so no heading above it) for whether this is their work
// or their wall. See photo-kind.js.
function imagesIn(html, baseUrl) {
  const out = [];
  const seen = new Set();
  for (const m of html.matchAll(/<img\b[^>]*>/gi)) {
    const tag = m[0];
    const u = (tag.match(/\b(?:src|data-src)=["']([^"']+)["']/i) || [])[1];
    if (!u || u.startsWith('data:')) continue;
    let abs;
    try { abs = new URL(u, baseUrl).href; } catch { continue; }
    if (seen.has(abs) || SKIP.test(abs)) continue;
    if (!/\.(jpe?g|png|webp)(\?|$)/i.test(abs)) continue;
    seen.add(abs);
    const alt = ((tag.match(/\balt=["']([^"']*)["']/i) || tag.match(/\btitle=["']([^"']*)["']/i) || [])[1] || '').trim().slice(0, 120);
    out.push({ url: abs, alt });
  }
  return out;
}
const imageUrlsIn = (html, baseUrl) => imagesIn(html, baseUrl).map((i) => i.url);

async function fetchBuffer(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT), headers: { 'user-agent': UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('content-type') || '';
  if (!/^image\//i.test(ct)) throw new Error(`not an image (${ct})`);
  return Buffer.from(await res.arrayBuffer());
}

// Finds up to `max` real photo URLs on a site. Returns [] rather than
// guessing when the page is JS-rendered and nothing is really there.
async function findPhotos(siteUrl, max = 4) {
  const start = /^https?:\/\//i.test(siteUrl) ? siteUrl : 'https://' + siteUrl;
  const res = await fetch(start, { signal: AbortSignal.timeout(TIMEOUT), headers: { 'user-agent': UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const html = await res.text();
  return imagesIn(html, start).slice(0, max);
}
const findPhotoUrls = async (siteUrl, max = 4) => (await findPhotos(siteUrl, max)).map((i) => i.url);

// Downloads and embeds (resized data URIs, via the same tool ./cc photo
// uses for hand-picked local files) up to `max` real photos from the site.
// Skips any single image that fails to fetch or decode rather than aborting
// the whole batch — one broken URL on their page shouldn't cost the rest.
async function embedFromSite(siteUrl, max = 4) {
  // A wider pool than needed — dedup below picks the max distinct ones
  // rather than trusting whichever `max` happened to appear first.
  const found = await findPhotos(siteUrl, max * 3);
  if (!found.length) return [];

  const tmp = require('os').tmpdir();
  const fs = require('fs');
  const downloaded = [];   // { file, buf, mime, meta: { url, alt } }
  for (const [i, meta] of found.entries()) {
    const url = meta.url;
    try {
      const buf = await fetchBuffer(url);
      if (buf.length < 4000) continue;   // smaller than any real photo — a 1x1 tracker or a broken placeholder
      const ext = (url.match(/\.(jpe?g|png|webp)(\?|$)/i) || [, 'jpg'])[1].toLowerCase();
      const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
      const f = path.join(tmp, `photo-${Date.now()}-${i}.${ext}`);
      fs.writeFileSync(f, buf);
      downloaded.push({ file: f, buf, mime, meta });
    } catch { /* skip this one, keep going */ }
  }
  if (!downloaded.length) return [];

  const distinctIdx = await keepDistinct(downloaded.map((d) => ({ buf: d.buf, mime: d.mime })));
  const kept = distinctIdx.slice(0, max).map((i) => downloaded[i]);

  const embedded = await embed(kept.map((d) => d.file));
  downloaded.forEach((d) => { try { fs.unlinkSync(d.file); } catch {} });
  // A guessed kind is a hint, not a verdict. Untagged photos never sit under
  // "Recent work" until someone looks (./cc shot writes them out to look at).
  return embedded.map((e, i) => {
    const m = kept[i]?.meta || {};
    const kind = guessKind(m);
    return { src: e.src, ...(m.alt ? { alt: m.alt } : {}), ...(kind ? { kind } : {}), from: { url: m.url, alt: m.alt || '', under: '' } };
  });
}

module.exports = { findPhotoUrls, findPhotos, embedFromSite };
