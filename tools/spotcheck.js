// Screenshot a candidate's current site so it can actually be looked at,
// not just scored. Saves to clients/<slug>/before.png.
//
//   node tools/spotcheck.js <slug>

const fs = require('fs');
const path = require('path');
const { screenshot } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');

async function main() {
  const slug = process.argv[2];
  if (!slug) { console.error('usage: node tools/spotcheck.js <slug>'); process.exit(1); }
  const bFile = path.join(ROOT, 'clients', slug, 'business.json');
  const b = JSON.parse(fs.readFileSync(bFile, 'utf8'));
  if (!b.currentSite) { console.error(`${slug} has no currentSite to screenshot`); process.exit(1); }

  await require('./reaudit').assertOnline();
  const out = path.join(ROOT, 'clients', slug, 'before.png');
  await screenshot(b.currentSite, out);
  console.log(out);
}

main().catch((e) => { console.error(e.message); process.exit(1); });
