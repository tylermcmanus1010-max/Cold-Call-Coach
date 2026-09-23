// Builds site/ — the ONLY folder the Worker serves (mcmanuswebco.com).
//
// The repo itself has to stay private-safe: pricing, the suppression list,
// every other prospect's audit data, git history of past pitches. None of
// that belongs on a public URL. So this copies out just the one file a
// pitch link actually needs — clients/<slug>/index.html — into a flat
// site/<slug>/index.html, and nothing else. Point Cloudflare Pages' build
// output directory at "site", never at the repo root.
//
// The one exception is site/dash/ — the morning dashboard, which lists every
// prospect and so is exactly what must not be public. It is only ever
// served through worker.js, which refuses it without DASH_KEY; the asset
// layer never answers for /dash/ on its own (see wrangler.toml).
//
//   node tools/publish.js

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');
const OUT = path.join(ROOT, 'site');

function main() {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  const slugs = fs.readdirSync(CLIENTS).filter((d) =>
    fs.existsSync(path.join(CLIENTS, d, 'index.html')));

  let n = 0;
  for (const slug of slugs) {
    const dir = path.join(OUT, slug);
    fs.mkdirSync(dir, { recursive: true });
    fs.copyFileSync(path.join(CLIENTS, slug, 'index.html'), path.join(dir, 'index.html'));
    n++;
  }
  // The root is our own site — home/index.html, self-contained like every
  // client page — served at mcmanuswebco.com. Without it, a bare 404 rather
  // than Cloudflare's own, and rather than a folder listing.
  const home = path.join(ROOT, 'home', 'index.html');
  const withHome = fs.existsSync(home);
  if (withHome) fs.copyFileSync(home, path.join(OUT, 'index.html'));
  else fs.writeFileSync(path.join(OUT, 'index.html'),
    '<!doctype html><title>Not found</title><body style="font:16px system-ui;padding:40px">Nothing here.');

  // Pitch pages are for one prospect each and never for search; the
  // dashboard is private. The home page is the one thing here that should
  // be indexed, so the noindex is per path, not /*.
  // Security headers on every response. The pages are self-contained by
  // design (inline CSS and JS, photos as data: URIs, no requests out), so the
  // policy can be strict: nothing loads from anywhere but this origin, the
  // site cannot be framed, and browsers must not sniff types. The dashboard
  // is the one exception: it pulls two Google Fonts, so its rule swaps in a
  // policy that allows exactly those two hosts and nothing else.
  const csp = [
    "default-src 'self'", "script-src 'self' 'unsafe-inline'", "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:", "font-src 'self' data:", "media-src 'self' data:", "connect-src 'self'",
    "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'",
    'upgrade-insecure-requests',
  ];
  const dashCsp = csp.map((d) => d.startsWith('style-src') ? d + ' https://fonts.googleapis.com'
    : d.startsWith('font-src') ? d + ' https://fonts.gstatic.com' : d);
  const security = [
    `Content-Security-Policy: ${csp.join('; ')}`,
    'Strict-Transport-Security: max-age=31536000; includeSubDomains',
    'X-Content-Type-Options: nosniff',
    'X-Frame-Options: DENY',
    'Referrer-Policy: strict-origin-when-cross-origin',
    'Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()',
    'Cross-Origin-Opener-Policy: same-origin',
  ];
  fs.writeFileSync(path.join(OUT, '_headers'), [
    '/*\n' + security.map((h) => '  ' + h).join('\n'),
    ...slugs.map((slug) => `/${slug}/*\n  X-Robots-Tag: noindex`),
    `/dash/*\n  X-Robots-Tag: noindex\n  ! Content-Security-Policy\n  Content-Security-Policy: ${dashCsp.join('; ')}`,
  ].join('\n\n') + '\n');

  const dash = path.join(ROOT, 'dashboard', 'index.html');
  const withDash = fs.existsSync(dash);
  if (withDash) {
    fs.mkdirSync(path.join(OUT, 'dash'), { recursive: true });
    fs.copyFileSync(dash, path.join(OUT, 'dash', 'index.html'));
  }

  console.log(`site/ built — ${n} page${n === 1 ? '' : 's'}${withHome ? ', the home page at /' : ''}${withDash ? ', plus the dashboard behind DASH_KEY at /dash/' : ''}, nothing else.`);
}

main();
