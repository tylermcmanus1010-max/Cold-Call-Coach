// Screenshots a page the way a prospect will actually see it, so the design
// can be judged by eye and not by reading CSS.
//
// Most of what has been wrong with our pages was invisible in the source and
// obvious in a picture: a button with unreset borders, a measure tuned for
// desktop forcing four lines on a phone, a caption colliding with the art
// above it. So this shoots a client's page (or any URL) at phone width in
// viewport-sized folds — what a thumb sees between swipes — plus the whole
// page, and the desktop first fold. Put the output next to design/reference/
// and ask whether it belongs there.
//
//   node tools/shot.js <slug | url> [outdir]
//
// Behind the agent proxy in the sandbox, Chromium's own TLS handshake is
// dropped by the intercepting egress (its post-quantum ClientHello is too
// large for it); Playwright's Node-side request client gets through fine.
// So when HTTPS_PROXY is set, every request the browser makes is fetched
// Node-side and handed back — the browser never opens a socket. Anywhere
// else (a laptop, GitHub Actions) it is a plain page load.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.join(__dirname, '..');

// Same browser resolution as browser-audit.js: look everywhere before
// demanding an env var.
const EXEC = (() => {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const cp = require('child_process');
  const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers',
                 path.join(require('os').homedir(), '.cache/ms-playwright')].filter(Boolean);
  for (const root of roots) {
    let dirs = [];
    try { dirs = fs.readdirSync(root).filter((d) => d.startsWith('chromium')); } catch { continue; }
    dirs.sort((a, b) => (+(b.match(/(\d+)$/) || [])[1] || 0) - (+(a.match(/(\d+)$/) || [])[1] || 0));
    for (const d of dirs) {
      for (const rel of ['chrome-linux/chrome', 'chrome-linux/headless_shell',
                         'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) {
        const f = path.join(root, d, rel);
        if (fs.existsSync(f)) return f;
      }
    }
  }
  for (const bin of ['google-chrome', 'chromium', 'chromium-browser']) {
    try { return cp.execSync(`command -v ${bin}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim() || undefined; }
    catch { /* not installed */ }
  }
  return undefined;
})();

const PHONE = { width: 390, height: 844 };
const DESK = { width: 1440, height: 900 };
const MAX_FOLDS = 8;   // past this a page is long enough that the full shot tells the story

const isUrl = (s) => /^(https?|file):\/\//i.test(s);

// A slug becomes the built page on disk; anything with a scheme is taken as-is.
function resolveTarget(target) {
  if (isUrl(target)) return { url: target, name: safeName(target) };
  const file = path.join(ROOT, 'clients', target, 'index.html');
  if (!fs.existsSync(file)) throw new Error(`no built page at clients/${target}/index.html — run ./cc build ${target} first`);
  return { url: 'file://' + file, name: target };
}

function safeName(u) {
  try { const x = new URL(u); return (x.hostname.replace(/^www\./, '') + x.pathname).replace(/[^a-z0-9.-]+/gi, '-').replace(/^-|-$/g, ''); }
  catch { return u.replace(/[^a-z0-9.-]+/gi, '-'); }
}

// Everything the browser asks for is fetched here in Node and handed back.
// Third-party hosts the egress refuses fail fast instead of hanging `load`.
async function routeThroughNode(page) {
  await page.route('**/*', async (route) => {
    const u = route.request().url();
    if (/^(data|blob|file):/.test(u)) return route.continue();
    try { return await route.fulfill({ response: await route.fetch({ timeout: 15000 }) }); }
    catch { return route.abort(); }
  });
}

// Scroll-reveal pages are blank below the fold until scrolled. Walk the page
// once so everything has fired, then go back to the top.
async function settle(page) {
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 400) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 90));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(900);
}

async function open(browser, url, viewport, scale, mobile) {
  const ctx = await browser.newContext({
    viewport, deviceScaleFactor: scale, isMobile: mobile, hasTouch: mobile,
    ignoreHTTPSErrors: true,
    proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
    userAgent: mobile
      ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
      : undefined,
  });
  const page = await ctx.newPage();
  if (process.env.HTTPS_PROXY && /^https?:/i.test(url)) await routeThroughNode(page);
  try { await page.goto(url, { waitUntil: 'load', timeout: 60000 }); }
  catch { /* a straggling third-party request; the DOM is there */ }
  await page.waitForTimeout(isUrl(url) && !url.startsWith('file:') ? 3000 : 600);
  await settle(page);
  return { ctx, page };
}

// A page that scrolls sideways on a phone is broken, whatever else it does.
async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

async function shoot(target, outDir) {
  const { url, name } = resolveTarget(target);
  const out = outDir || path.join(ROOT, 'shots', name);
  fs.mkdirSync(out, { recursive: true });
  for (const f of fs.readdirSync(out)) if (f.endsWith('.png')) fs.unlinkSync(path.join(out, f));

  const browser = await chromium.launch({ executablePath: EXEC,
    args: ['--no-sandbox', '--disable-background-networking', '--disable-component-update'] });
  const files = [];
  const report = { url, out, files, height: 0, overflow390: 0, overflow320: 0 };
  try {
    // Phone: the folds, then the whole thing.
    let { ctx, page } = await open(browser, url, PHONE, 2, true);
    report.height = await page.evaluate(() => document.body.scrollHeight);
    report.overflow390 = await overflow(page);
    const folds = Math.min(MAX_FOLDS, Math.ceil(report.height / PHONE.height));
    for (let i = 0; i < folds; i++) {
      await page.evaluate((y) => window.scrollTo(0, y), i * PHONE.height);
      await page.waitForTimeout(500);
      const f = path.join(out, `phone-${String(i + 1).padStart(2, '0')}.png`);
      await page.screenshot({ path: f }); files.push(f);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    const full = path.join(out, 'phone-full.png');
    await page.screenshot({ path: full, fullPage: true }); files.push(full);
    await ctx.close();

    // 320 is the floor. Measure only; the 390 shots already show the layout.
    ({ ctx, page } = await open(browser, url, { width: 320, height: 693 }, 1, true));
    report.overflow320 = await overflow(page);
    await ctx.close();

    // Desktop first fold, at 1x so the file is small enough to look at.
    ({ ctx, page } = await open(browser, url, DESK, 1, false));
    const desk = path.join(out, 'desktop-01.png');
    await page.screenshot({ path: desk }); files.push(desk);
    await ctx.close();
  } finally {
    await browser.close();
  }
  return report;
}

module.exports = { shoot, resolveTarget };

if (require.main === module) {
  const [target, outDir] = process.argv.slice(2);
  if (!target) { console.error('Usage: node tools/shot.js <slug | url> [outdir]'); process.exit(2); }
  shoot(target, outDir).then((r) => {
    console.log(`${r.url}\n  ${r.height}px tall at 390 · ${r.files.length} shots → ${path.relative(ROOT, r.out)}/`);
    if (r.overflow390 > 0) console.log(`  ⚠️  scrolls sideways at 390px by ${r.overflow390}px`);
    if (r.overflow320 > 0) console.log(`  ⚠️  scrolls sideways at 320px by ${r.overflow320}px`);
    if (!r.overflow390 && !r.overflow320) console.log('  no horizontal overflow at 320 or 390');
    for (const f of r.files) console.log('  ' + path.relative(ROOT, f));
  }).catch((e) => { console.error('✗ ' + e.message); process.exit(1); });
}
