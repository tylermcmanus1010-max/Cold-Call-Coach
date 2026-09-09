// Real-browser photo harvest — the GitHub Actions counterpart to
// tools/photos.js. Runs where a real browser actually reaches the open
// internet (this repo's runners; not the coding sandbox — see
// .github/workflows/photos.yml). Loads the page in Chrome, waits for it to
// finish hydrating, then reads whatever <img> elements actually exist in
// the RENDERED DOM — catches GoDaddy Website Builder, React, Vue, anything
// that injects its real markup after load, which tools/photos.js's plain
// fetch cannot see (checked: zero images back from cupcakesalayola.com and
// darshanbakery.com via fetch; both are JS-rendered).
//
//   node tools/harvest-photos.js <slug> [--max=4]
//   node tools/harvest-photos.js --all [--max=4]      # every "new" client missing photos

const fs = require('fs');
const path = require('path');
const { chromium, EXEC } = require('./browser-audit');
const { embed } = require('./embed-photo');
const { keepDistinct } = require('./dedupe-images');
const { guessKind } = require('./photo-kind');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');

const SKIP = /logo|icon|favicon|sprite|pixel|spacer|placeholder|avatar|badge|banner-ad|wp-includes|gravatar|elementor-placeholder/i;

// Returns { url, alt, under } per image. The alt and the nearest heading
// above the image are the site's own word for what it shows — kept, because
// "Recent work" over a photo of a wall is a claim we cannot make, and this
// is the only cheap evidence of what the photo is of (see photo-kind.js).
async function realImageUrls(page, max) {
  const withSize = await page.evaluate(() => {
    const headingAbove = (el) => {
      // walk up until an ancestor contains a heading that precedes this image
      for (let n = el; n && n !== document.body; n = n.parentElement) {
        const hs = [...n.querySelectorAll('h1,h2,h3,h4')].filter((h) =>
          h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING);
        if (hs.length) return hs[hs.length - 1].textContent.trim().slice(0, 80);
      }
      return '';
    };
    return [...document.querySelectorAll('img')].map((el) => ({
      src: el.currentSrc || el.src || el.dataset.src || '',
      w: el.naturalWidth || el.width || 0,
      h: el.naturalHeight || el.height || 0,
      alt: (el.getAttribute('alt') || el.getAttribute('title') || '').trim().slice(0, 120),
      under: headingAbove(el),
    }));
  });
  const seen = new Set();
  const out = [];
  for (const { src, w, h, alt, under } of withSize) {
    if (!src || src.startsWith('data:') || seen.has(src)) continue;
    seen.add(src);
    if (SKIP.test(src)) continue;
    if (w && w < 200 && h && h < 200) continue;   // icon-sized, not a content photo
    out.push({ url: src, alt, under });
    if (out.length >= max) break;
  }
  return out;
}

async function fetchBuffer(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('content-type') || '';
  if (!/^image\//i.test(ct)) throw new Error(`not an image (${ct})`);
  return Buffer.from(await res.arrayBuffer());
}

async function harvestOne(slug, { max = 4, browser, log = console.log } = {}) {
  const bFile = path.join(CLIENTS, slug, 'business.json');
  const b = JSON.parse(fs.readFileSync(bFile, 'utf8'));
  if (!b.currentSite) { log(`  - ${slug}: no currentSite`); return { slug, added: 0 }; }
  if (b.photos?.length) { log(`  - ${slug}: already has photos`); return { slug, added: 0 }; }

  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let urls = [];
  try {
    await page.goto(b.currentSite, { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(500);   // last beat for anything that hydrates just after networkidle
    // Pull a wider pool than we need — a gallery slider showing the same
    // haircut three frames apart looks like variety in the DOM and isn't.
    // Dedup below picks the max distinct ones out of this pool instead.
    urls = await realImageUrls(page, max * 3);
  } catch (e) {
    log(`  ! ${slug}: ${e.message.split('\n')[0]}`);
    return { slug, added: 0 };
  } finally {
    await page.close();
  }
  if (!urls.length) { log(`  - ${slug}: no real photos found`); return { slug, added: 0 }; }

  const tmp = require('os').tmpdir();
  const downloaded = [];   // { file, buf, mime, meta: { url, alt, under } }
  for (const [i, meta] of urls.entries()) {
    const url = meta.url;
    try {
      const buf = await fetchBuffer(url);
      if (buf.length < 4000) continue;
      const ext = (url.match(/\.(jpe?g|png|webp)(\?|$)/i) || [, 'jpg'])[1].toLowerCase();
      const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
      const f = path.join(tmp, `harvest-${slug}-${i}.${ext}`);
      fs.writeFileSync(f, buf);
      downloaded.push({ file: f, buf, mime, meta });
    } catch { /* skip this one */ }
  }
  if (!downloaded.length) { log(`  - ${slug}: found image URLs but none downloaded cleanly`); return { slug, added: 0 }; }

  const distinctIdx = await keepDistinct(downloaded.map((d) => ({ buf: d.buf, mime: d.mime })), { browser });
  const kept = distinctIdx.slice(0, max).map((i) => downloaded[i]);
  const files = kept.map((d) => d.file);
  if (distinctIdx.length < downloaded.length) {
    log(`  · ${slug}: dropped ${downloaded.length - distinctIdx.length} near-duplicate photo(s)`);
  }

  const embedded = await embed(files);
  downloaded.forEach((d) => { try { fs.unlinkSync(d.file); } catch {} });

  // A guessed kind is a hint, not a verdict; untagged photos never sit under
  // "Recent work" until someone looks (./cc shot writes them out to look at).
  b.photos = embedded.map((e, i) => {
    const m = kept[i]?.meta || {};
    const kind = guessKind(m);
    return {
      src: e.src,
      alt: m.alt || `${b.name} — photo ${i + 1}`,
      ...(kind ? { kind } : {}),
      from: { url: m.url, alt: m.alt || '', under: m.under || '' },
    };
  });
  const tagged = b.photos.filter((p) => p.kind).length;
  if (tagged < b.photos.length) log(`  · ${slug}: ${b.photos.length - tagged} photo(s) need a look — ./cc shot ${slug}, then set kind`);
  fs.writeFileSync(bFile, JSON.stringify(b, null, 2) + '\n');
  log(`  + ${slug}: ${embedded.length} real photo(s) embedded`);
  return { slug, added: embedded.length };
}

async function main() {
  const argv = process.argv.slice(2);
  const all = argv.includes('--all');
  const max = Number((argv.find((a) => a.startsWith('--max=')) || '--max=4').split('=')[1]) || 4;
  const slug = argv.find((a) => !a.startsWith('--'));

  await require('./reaudit').assertOnline();

  const slugs = all
    ? fs.readdirSync(CLIENTS).filter((d) => {
        const f = path.join(CLIENTS, d, 'business.json');
        if (!fs.existsSync(f) || d.startsWith('example-')) return false;
        const b = JSON.parse(fs.readFileSync(f, 'utf8'));
        return b.status === 'new' && !b.photos?.length && b.currentSite;
      })
    : slug ? [slug] : (() => { throw new Error('usage: node tools/harvest-photos.js <slug> | --all'); })();

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const results = [];
  try {
    for (const s of slugs) results.push(await harvestOne(s, { max, browser }));
  } finally {
    await browser.close();
  }
  const added = results.filter((r) => r.added > 0).length;
  console.log(`\n${added}/${results.length} client(s) got real photos.`);
}

if (require.main === module) main().catch((e) => { console.error(e.message); process.exit(1); });

module.exports = { harvestOne };
