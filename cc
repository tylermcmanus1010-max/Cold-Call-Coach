#!/usr/bin/env node
// Cold Call Coach — find a site, rebuild it, send it with a price. Repeat.
//
//   ./cc scout              build the lead list: pull businesses, audit every site
//   ./cc audit <url>        audit one site and print what it fails
//   ./cc new <slug>         scaffold a client folder by hand
//   ./cc build [slug]       render index.html + pitch.md (all clients if no slug)
//   ./cc sent <slug>        mark as sent today
//   ./cc status <slug> <new|sent|replied|won|dead>
//   ./cc list               show the pipeline
//
// scout options:
//   --source osm            OpenStreetMap (default, free, no key)
//   --source places         Google Places — adds star rating and review count.
//                           Needs GOOGLE_MAPS_API_KEY in your environment.
//   --source file --file leads/urls.txt    a list you gathered yourself
//   --limit N               only audit the first N (start with 50 to test)
//   --make N                scaffold client folders for the top N leads
//   --refresh               with --make, re-audit clients that already exist
//                           (updates the audit, keeps the copy you wrote)

const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const CLIENTS = path.join(ROOT, 'clients');
const LEADS = path.join(ROOT, 'leads');
const TPL = path.join(ROOT, 'tools/business.template.json');
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

function flags(argv) {
  const o = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const k = argv[i].slice(2);
    const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    o[k] = v;
  }
  return o;
}

async function cmdScout(argv) {
  const { scout, toCsv, toMarkdown, toBusinessJson } = require('./tools/scout');
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/scout.json'), 'utf8'));
  const o = flags(argv);
  const source = o.source || 'osm';

  if (source === 'places' && !process.env.GOOGLE_MAPS_API_KEY)
    die('--source places needs a key:  export GOOGLE_MAPS_API_KEY=…\n  Get one at https://console.cloud.google.com → Places API (New).\n  Or just use the default: ./cc scout');
  if (source === 'file' && !o.file) die('--source file needs --file <path>');

  const leads = await scout(cfg, {
    source, key: process.env.GOOGLE_MAPS_API_KEY, file: o.file,
    limit: o.limit ? Number(o.limit) : null,
  });

  if (!leads.length) return console.log('\nNo leads cleared the filters. Loosen config/scout.json → filters.');

  fs.mkdirSync(LEADS, { recursive: true });
  fs.writeFileSync(path.join(LEADS, 'leads.csv'), toCsv(leads));
  fs.writeFileSync(path.join(LEADS, 'leads.json'), JSON.stringify(leads, null, 2) + '\n');
  fs.writeFileSync(path.join(LEADS, 'leads.md'), toMarkdown(leads, cfg.area.name) + '\n');

  const w = Math.min(34, Math.max(12, ...leads.slice(0, 25).map((l) => (l.name || '').length)));
  console.log(`\n   #  ${'BUSINESS'.padEnd(w)}  GAPS  ★ / REVIEWS   CURRENT SITE`);
  console.log('  ' + '─'.repeat(w + 46));
  leads.slice(0, 25).forEach((l, i) => {
    const a = l.auditResult;
    const state = !l.website ? (l.source === 'osm' ? 'NO SITE LISTED (verify)' : 'NO WEBSITE')
      : !a.reachable ? (a.reason || 'unreachable').slice(0, 30) : (a.reason || l.website).slice(0, 30);
    const rev = l.reviewCount != null ? `${l.rating ?? '–'} / ${l.reviewCount}` : '–';
    console.log(`  ${String(i + 1).padStart(2)}  ${(l.name || '').slice(0, w).padEnd(w)}  ${String(a.gaps).padStart(4)}  ${rev.padEnd(12)}  ${state}`);
  });

  console.log(`\n✓ ${leads.length} lead${leads.length === 1 ? '' : 's'} → leads/leads.csv  (open it in a spreadsheet)`);

  const make = o.make ? Number(o.make) : 0;
  if (make) {
    let made = 0, refreshed = 0;
    for (const l of leads.slice(0, make)) {
      if (!l.slug) continue;
      const fresh = toBusinessJson(l, TPL);

      if (!fs.existsSync(dir(l.slug))) {
        fs.mkdirSync(dir(l.slug), { recursive: true });
        save(l.slug, fresh);
        made++;
      } else if (o.refresh) {
        // Re-audit an existing client without touching the copy you wrote.
        // Pitching from a stale audit is how you end up telling someone their
        // working site is broken.
        const existing = load(l.slug);
        save(l.slug, { ...existing, audit: fresh.audit, _scout: fresh._scout, currentSite: fresh.currentSite });
        refreshed++;
      }
    }
    console.log(`✓ scaffolded ${made} new client folder${made === 1 ? '' : 's'}` +
      (refreshed ? `, re-audited ${refreshed} existing` : '') + ', pre-filled with name, phone, address and audit');
    if (!o.refresh && made < make) console.log('  (some already existed — pass --refresh to re-audit them)');
    console.log(`  next: add headline + services + reviews, then ./cc build`);
  } else {
    console.log(`  next: ./cc scout --make 10   to scaffold the top 10 straight into clients/`);
  }
}

async function cmdAudit(url) {
  if (!url) die('Usage: ./cc audit <url>');
  const { audit } = require('./tools/audit');
  const r = await audit(url);
  console.log(`\n${r.finalUrl || url}`);
  const stats = r.ms != null ? `loaded in ${r.ms}ms · ${r.kb}KB` : 'no page';
  console.log(r.blocked ? `  COULD NOT CHECK — ${r.reason}`
    : r.reachable ? `  ${stats}${r.reason ? ' · ' + r.reason : ''}`
    : `  UNREACHABLE — ${r.reason}`);
  if (r.blocked) return console.log('\n  Not a lead. We were refused, so we cannot say anything is wrong with it —\n  and a site behind a firewall usually has someone already maintaining it.\n');
  console.log();
  for (const c of checks) console.log(`  ${r.checks[c.key] ? '✅' : '❌'}  ${c.label}`);
  console.log(`\n  ${r.gaps}/${checks.length} failing — ${r.gaps >= 5 ? 'worth a rebuild' : 'probably not worth your time'}\n`);
}

function cmdNew(slug) {
  if (!slug) die('Usage: ./cc new <slug>');
  if (fs.existsSync(dir(slug))) die(`clients/${slug} already exists`);
  const tpl = JSON.parse(fs.readFileSync(TPL, 'utf8'));
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
  if (!list.length) die('No clients yet. Run: ./cc scout --make 10   or   ./cc new <slug>');
  const skipped = [];
  for (const s of list) {
    const b = load(s);
    if (!b.name || !b.tagline) {
      // Building every client should not stop at the first unfinished one —
      // that silently left the others on a stale template for a whole session.
      const missing = !b.name ? '"name"' : '"tagline"';
      if (slug) die(
        `clients/${s}/business.json is missing ${missing}.\n` +
        `  If scout scaffolded this, that is on purpose — write the headline and tagline yourself,\n` +
        `  they are the two lines that actually sell the page.`);
      skipped.push(`${s} (missing ${missing})`);
      continue;
    }
    const unknown = Object.keys(b.audit || {}).filter((k) => !checks.some((c) => c.key === k));
    if (unknown.length) console.warn(`  ! ${s}: unknown audit keys ignored: ${unknown.join(', ')}`);
    fs.writeFileSync(path.join(dir(s), 'index.html'), render(b));
    fs.writeFileSync(path.join(dir(s), 'pitch.md'), pitch(b, pricing));
    const failed = checks.filter((c) => (b.audit || {})[c.key] !== true).length;
    console.log(`✓ ${s} — index.html + pitch.md  (${checks.length - failed}/${checks.length} passing, ${failed} gaps to sell)`);
  }
  if (skipped.length) {
    console.log(`\n  ${skipped.length} not built yet — write a headline and tagline for each:`);
    skipped.forEach((s) => console.log(`    · ${s}`));
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
    return { slug: s, status: b.status || 'new', gaps, sent: b.sentOn || '',
             value: tier ? pricing.currency + tier.price.toLocaleString('en-US') : '' };
  });
  if (!rows.length) return console.log('No clients yet. Run: ./cc scout --make 10');
  const ws = Math.max(8, ...rows.map((r) => r.slug.length));
  console.log(`\n${'BUSINESS'.padEnd(ws)}  STATUS    GAPS  QUOTE     SENT`);
  console.log('─'.repeat(ws + 34));
  for (const r of rows) {
    console.log(`${r.slug.padEnd(ws)}  ${r.status.padEnd(8)}  ${String(r.gaps).padStart(4)}  ${r.value.padEnd(8)}  ${r.sent}`);
  }
  const open = rows.filter((r) => ['new', 'sent', 'replied'].includes(r.status));
  console.log(`\n${rows.length} total · ${open.length} still open · ${rows.filter((r) => r.status === 'won').length} won\n`);
}

const [cmd, ...args] = process.argv.slice(2);
(async () => {
  switch (cmd) {
    case 'scout': await cmdScout(args); break;
    case 'audit': await cmdAudit(args[0]); break;
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
})().catch((e) => die(e.message));
