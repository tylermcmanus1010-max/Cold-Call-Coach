// Builds site/ — the ONLY folder Cloudflare Pages should be told to serve.
//
// The repo itself has to stay private-safe: pricing, the suppression list,
// every other prospect's audit data, git history of past pitches. None of
// that belongs on a public URL. So this copies out just the one file a
// pitch link actually needs — clients/<slug>/index.html — into a flat
// site/<slug>/index.html, and nothing else. Point Cloudflare Pages' build
// output directory at "site", never at the repo root.
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
  // A bare 404 rather than Cloudflare's own — and rather than the folder
  // listing a static host will otherwise offer at site/ itself.
  fs.writeFileSync(path.join(OUT, 'index.html'),
    '<!doctype html><title>Not found</title><body style="font:16px system-ui;padding:40px">Nothing here.');
  fs.writeFileSync(path.join(OUT, '_headers'), '/*\n  X-Robots-Tag: noindex\n');

  console.log(`site/ built — ${n} page${n === 1 ? '' : 's'}, nothing else.`);
}

main();
