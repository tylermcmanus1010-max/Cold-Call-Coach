// Reads a business's site the way a person would — in a real Chrome, after
// the page has finished rendering and any "Just a moment…" challenge has
// cleared — and writes down what it saw. Nothing here is a claim: it is
// raw material, like harvest.json, for a person or an agent to read before
// a page is designed. Runs where Chrome can reach the internet (Actions,
// browse.yml); from the sandbox the challenge never clears.
//
// Writes clients/<slug>/browse.json (text of every page it read, links,
// socials, phones and emails it saw printed, structured data, an image
// inventory with real sizes) and clients/<slug>/browse/*.jpg (the home
// page at phone and desktop width) — the folder is named browse/, not
// site/, because .gitignore ignores any site/ directory.

const fs = require('fs');
const path = require('path');
const { chromium, EXEC } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';
const CHALLENGE = /just a moment|enable javascript and cookies|checking your browser|attention required/i;
const SOCIAL = /instagram\.com|facebook\.com|youtube\.com|youtu\.be|vimeo\.com|tiktok\.com|linkedin\.com|x\.com|twitter\.com|pinterest\.com|behance\.net/i;
const WANT = /about|service|work|portfolio|gallery|project|contact|pricing|rates|package|team|studio|film|video|photo|wedding|commercial|book/i;
const SKIP = /\.(pdf|zip|jpe?g|png|gif|svg|webp|mp4|mov)(\?|$)|mailto:|tel:|javascript:|#/i;

async function settle(page, { timeout = 25000 } = {}) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const title = await page.title().catch(() => '');
    const body = await page.evaluate(() => (document.body && document.body.innerText || '').slice(0, 400)).catch(() => '');
    if (!CHALLENGE.test(title) && !CHALLENGE.test(body)) break;
    await page.waitForTimeout(1000);
  }
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(800);
}

async function readPage(page) {
  return page.evaluate(() => {
    const abs = (u) => { try { return new URL(u, location.href).href; } catch { return ''; } };
    const text = (document.body && document.body.innerText || '').replace(/\n{3,}/g, '\n\n').trim();
    const links = [...document.querySelectorAll('a[href]')].map((a) => ({ href: abs(a.getAttribute('href')), text: (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 80) })).filter((l) => l.href);
    const imgs = [...document.querySelectorAll('img')].map((i) => {
      const r = i.getBoundingClientRect();
      return { src: abs(i.currentSrc || i.src || i.getAttribute('data-src') || ''), alt: (i.alt || '').trim().slice(0, 120), w: i.naturalWidth || 0, h: i.naturalHeight || 0, shown: Math.round(r.width) + 'x' + Math.round(r.height) };
    }).filter((i) => i.src && !/^data:/.test(i.src));
    const bg = [...document.querySelectorAll('*')].map((el) => getComputedStyle(el).backgroundImage).filter((v) => v && v !== 'none').map((v) => (v.match(/url\(["']?([^"')]+)/) || [])[1]).filter(Boolean).map(abs);
    const videos = [...document.querySelectorAll('video, video source, iframe')].map((v) => ({ tag: v.tagName.toLowerCase(), src: abs(v.src || v.getAttribute('src') || ''), poster: v.poster ? abs(v.poster) : '' })).filter((v) => v.src);
    const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map((s) => s.textContent.trim()).filter(Boolean);
    const meta = (n) => (document.querySelector(`meta[name="${n}"], meta[property="${n}"]`) || {}).content || '';
    const heads = [...document.querySelectorAll('h1, h2, h3')].map((h) => ({ tag: h.tagName.toLowerCase(), text: (h.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 160) })).filter((h) => h.text);
    const fonts = [...new Set([...document.querySelectorAll('h1, h2, p, a, body')].map((el) => getComputedStyle(el).fontFamily))].slice(0, 6);
    const colors = [...new Set([...document.querySelectorAll('body, header, h1, a, button, .btn, [class*=hero]')].flatMap((el) => { const s = getComputedStyle(el); return [s.color, s.backgroundColor]; }))].filter((c) => c && c !== 'rgba(0, 0, 0, 0)').slice(0, 12);
    return {
      url: location.href, title: document.title, description: meta('description'), ogImage: meta('og:image'), canonical: (document.querySelector('link[rel=canonical]') || {}).href || '',
      text, heads, links, images: imgs, backgroundImages: [...new Set(bg)], videos, jsonld: ld, fonts, colors,
    };
  });
}

function pick(links, base, max) {
  const host = new URL(base).hostname.replace(/^www\./, '');
  const seen = new Set([base.replace(/\/$/, '')]);
  const out = [];
  for (const l of links) {
    let u; try { u = new URL(l.href); } catch { continue; }
    if (u.hostname.replace(/^www\./, '') !== host) continue;
    if (SKIP.test(u.href)) continue;
    u.hash = ''; u.search = '';
    const key = u.href.replace(/\/$/, '');
    if (seen.has(key)) continue;
    if (!WANT.test(u.pathname + ' ' + l.text)) continue;
    seen.add(key);
    out.push(u.href);
    if (out.length >= max) break;
  }
  return out;
}

async function browse(slug, { url, pages = 6, log = console.log } = {}) {
  const dir = path.join(CLIENTS, slug);
  const f = path.join(dir, 'business.json');
  let b = {};
  if (fs.existsSync(f)) b = JSON.parse(fs.readFileSync(f, 'utf8'));
  const start = url || b.currentSite;
  if (!start) throw new Error(`${slug}: no URL — give one with --url`);
  fs.mkdirSync(path.join(dir, 'browse'), { recursive: true });

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const out = { slug, startedAt: new Date().toISOString(), start, pages: [], blocked: false };
  try {
    const ctx = await browser.newContext({ userAgent: UA, viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, locale: 'en-US' });
    const page = await ctx.newPage();
    await page.goto(start, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await settle(page);
    const home = await readPage(page);
    if (CHALLENGE.test(home.title) || CHALLENGE.test(home.text.slice(0, 300))) {
      out.blocked = true;
      log(`  ✗ ${slug}: the challenge never cleared — nothing read`);
    } else {
      out.pages.push(home);
      await page.screenshot({ path: path.join(dir, 'browse', 'desktop.jpg'), type: 'jpeg', quality: 72, fullPage: true }).catch(() => {});
      log(`  ✓ ${home.url}  "${home.title}"  ${home.text.length} chars, ${home.images.length} images, ${home.links.length} links`);

      for (const u of pick(home.links, home.url, pages)) {
        try {
          await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 30000 });
          await settle(page, { timeout: 12000 });
          const p = await readPage(page);
          out.pages.push(p);
          log(`  ✓ ${p.url}  "${p.title}"  ${p.text.length} chars, ${p.images.length} images`);
        } catch (e) {
          log(`  · ${u}: ${e.message.split('\n')[0]}`);
        }
      }

      const phone = await browser.newContext({ userAgent: UA.replace('Macintosh; Intel Mac OS X 14_0', 'iPhone; CPU iPhone OS 17_0 like Mac OS X'), viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
      const pp = await phone.newPage();
      await pp.goto(start, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await settle(pp);
      await pp.screenshot({ path: path.join(dir, 'browse', 'phone.jpg'), type: 'jpeg', quality: 72, fullPage: true }).catch(() => {});
      await phone.close();
    }
    await ctx.close();
  } finally {
    await browser.close();
  }

  // What a person wants at a glance, pulled up from the pages.
  const all = out.pages;
  const links = all.flatMap((p) => p.links);
  out.socials = [...new Set(links.map((l) => l.href).filter((h) => SOCIAL.test(h)))];
  out.emails = [...new Set(links.map((l) => l.href).filter((h) => /^mailto:/i.test(h)).map((h) => h.replace(/^mailto:/i, '').split('?')[0]))];
  out.phones = [...new Set(links.map((l) => l.href).filter((h) => /^tel:/i.test(h)).map((h) => h.replace(/^tel:/i, '')))];
  const imgs = new Map();
  for (const p of all) for (const i of p.images) if (!imgs.has(i.src) || (imgs.get(i.src).w < i.w)) imgs.set(i.src, { ...i, on: p.url });
  out.imageInventory = [...imgs.values()].sort((a, b) => (b.w * b.h) - (a.w * a.h)).slice(0, 80);
  out.videos = [...new Set(all.flatMap((p) => p.videos.map((v) => JSON.stringify(v))))].map((s) => JSON.parse(s));
  out.finishedAt = new Date().toISOString();

  fs.writeFileSync(path.join(dir, 'browse.json'), JSON.stringify(out, null, 2) + '\n');
  return out;
}

module.exports = { browse };

if (require.main === module) {
  const args = process.argv.slice(2);
  const slug = args.find((a) => !a.startsWith('--'));
  const url = (args.find((a) => a.startsWith('--url=')) || '').slice(6) || undefined;
  const pages = Number((args.find((a) => a.startsWith('--pages=')) || '').slice(8)) || 6;
  if (!slug) { console.error('usage: node tools/browse.js <slug> [--url=https://…] [--pages=6]'); process.exit(1); }
  browse(slug, { url, pages }).then((o) => {
    console.log(`\n  ${o.pages.length} page${o.pages.length === 1 ? '' : 's'} read · ${o.imageInventory.length} images · socials: ${o.socials.length} · emails: ${o.emails.join(', ') || 'none printed'} · phones: ${o.phones.join(', ') || 'none printed'}`);
    console.log(`  clients/${slug}/browse.json + browse/desktop.jpg, phone.jpg\n`);
  }).catch((e) => { console.error('browse failed:', e.message); process.exit(1); });
}
