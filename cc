#!/usr/bin/env node
// Cold Call Coach — find a site, rebuild it, send it with a price. Repeat.
//
//   ./cc new <slug>     scaffold a client folder
//   ./cc build [slug]   render index.html + pitch.md (all clients if no slug)
//   ./cc sent <slug>    mark as sent today
//   ./cc status <slug> <new|sent|replied|won|dead>
//   ./cc list           show the pipeline

const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const CLIENTS = path.join(ROOT, 'clients');
const render = require('./tools/render');
const pitch = require('./tools/pitch');
const checks = require('./tools/checks');
const pricing = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/pricing.json'), 'utf8'));

const STATUSES = ['new', 'sent', 'replied', 'won', 'dead'];
const die = (m) => { console.error('✗ ' + m); process.exit(1); };
const dir = (slug) => path.join(CLIENTS, slug);
const load = (slug) => {
  const f = path.join(dir(slug), 'business.json');
  if (!fs.existsSync(f)) die(`No client "${slug}". Run: ./cc new ${slug}`);
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); }
  catch (e) { die(`${slug}/business.json is not valid JSON — ${e.message}`); }
};
const save = (slug, b) =>
  fs.writeFileSync(path.join(dir(slug), 'business.json'), JSON.stringify(b, null, 2) + '\n');
const all = () => fs.existsSync(CLIENTS)
  ? fs.readdirSync(CLIENTS).filter((d) => fs.existsSync(path.join(CLIENTS, d, 'business.json'))).sort()
  : [];

function cmdNew(slug) {
  if (!slug) die('Usage: ./cc new <slug>');
  if (fs.existsSync(dir(slug))) die(`clients/${slug} already exists`);
  const tpl = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools/business.template.json'), 'utf8'));
  tpl.slug = slug;
  tpl.name = slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  fs.mkdirSync(dir(slug), { recursive: true });
  save(slug, tpl);
  console.log(`✓ clients/${slug}/business.json

Next:
  1. Fill it in from their site / Google listing / Yelp (10 min)
  2. Set audit.* to true for anything their current site already does right
  3. ./cc build ${slug}`);
}

function cmdBuild(slug) {
  const list = slug ? [slug] : all();
  if (!list.length) die('No clients yet. Run: ./cc new <slug>');
  for (const s of list) {
    const b = load(s);
    if (!b.name || !b.tagline) die(`${s}: "name" and "tagline" are required`);
    const unknown = Object.keys(b.audit || {}).filter((k) => !checks.some((c) => c.key === k));
    if (unknown.length) console.warn(`  ! ${s}: unknown audit keys ignored: ${unknown.join(', ')}`);
    fs.writeFileSync(path.join(dir(s), 'index.html'), render(b));
    fs.writeFileSync(path.join(dir(s), 'pitch.md'), pitch(b, pricing));
    const failed = checks.filter((c) => (b.audit || {})[c.key] !== true).length;
    console.log(`✓ ${s} — index.html + pitch.md  (${checks.length - failed}/${checks.length} passing, ${failed} gaps to sell)`);
  }
  if (list.length === 1) console.log(`\n  open clients/${list[0]}/index.html   ← check it on a phone first`);
}

function cmdStatus(slug, status) {
  if (!STATUSES.includes(status)) die(`Status must be one of: ${STATUSES.join(', ')}`);
  const b = load(slug);
  b.status = status;
  if (status === 'sent' && !b.sentOn) b.sentOn = new Date().toISOString().slice(0, 10);
  save(slug, b);
  console.log(`✓ ${slug} → ${status}`);
}

function cmdList() {
  const rows = all().map((s) => {
    const b = load(s);
    const gaps = checks.filter((c) => (b.audit || {})[c.key] !== true).length;
    const tier = pricing.tiers[b.tier || pricing.defaultTier];
    return {
      slug: s,
      status: b.status || 'new',
      gaps,
      sent: b.sentOn || '',
      value: tier ? pricing.currency + tier.price.toLocaleString('en-US') : '',
    };
  });
  if (!rows.length) return console.log('No clients yet. Run: ./cc new <slug>');
  const w = (k, min) => Math.max(min, ...rows.map((r) => String(r[k]).length));
  const ws = w('slug', 8);
  console.log(`\n${'BUSINESS'.padEnd(ws)}  STATUS    GAPS  QUOTE     SENT`);
  console.log('─'.repeat(ws + 34));
  for (const r of rows) {
    console.log(`${r.slug.padEnd(ws)}  ${r.status.padEnd(8)}  ${String(r.gaps).padStart(4)}  ${r.value.padEnd(8)}  ${r.sent}`);
  }
  const open = rows.filter((r) => ['new', 'sent', 'replied'].includes(r.status));
  console.log(`\n${rows.length} total · ${open.length} still open · ${rows.filter((r) => r.status === 'won').length} won\n`);
}

const [cmd, ...args] = process.argv.slice(2);
switch (cmd) {
  case 'new': cmdNew(args[0]); break;
  case 'build': cmdBuild(args[0]); break;
  case 'sent': cmdStatus(args[0], 'sent'); break;
  case 'status': cmdStatus(args[0], args[1]); break;
  case 'list': cmdList(); break;
  default:
    for (const line of fs.readFileSync(__filename, 'utf8').split('\n').slice(1)) {
      if (!line.startsWith('//')) break;
      console.log(line.replace(/^\/\/ ?/, ''));
    }
}
