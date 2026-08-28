#!/usr/bin/env node
// Cold Call Coach — find a site, rebuild it, send it with a price. Repeat.
//
//   ./cc scout              build the lead list: pull businesses, audit every site
//   ./cc audit <url>        audit one site and print what it fails
//   ./cc new <slug>         scaffold a client folder by hand
//   ./cc build [slug]       render index.html + pitch.md (all clients if no slug)
//   ./cc tried <slug>       log a call attempt (no answer, gatekeeper, callback)
//   ./cc sent <slug>        mark as sent today
//   ./cc status <slug> <new|sent|replied|won|dead>
//   ./cc photo <slug> <img...>  add photos to a page (resized and embedded,
//                           so the file still opens with no internet)
//   ./cc check [slug]       run our own 12 checks against the pages WE built
//   ./cc reaudit [slug]     re-check leads in a real browser and drop the ones
//                           whose site turns out to be fine (--all to redo every one)
//   ./cc export [slug]      copy built pages to send/ named by business,
//                           ready to attach (all built clients if no slug)
//   ./cc list               show the pipeline
//   ./cc next [N]           who to call right now, in order, with the reason
//   ./cc sheet              rebuild the call sheet dashboard from clients/
//   ./cc host <slug>        check a client is really ready, then write
//                           sites/<slug>/ for the host to serve
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
  const skipped = [], generic = [];
  for (const s of list) {
    const b = load(s);
    if (!b.name) {
      if (slug) die(`clients/${s}/business.json is missing "name" — nothing can be built without it.`);
      skipped.push(`${s} (missing "name")`);
      continue;
    }
    // A missing tagline used to block the build entirely, which left vetted
    // leads with no page and nothing to call about. Derive a plain, true one
    // from what we already know and note it, rather than refusing to work.
    // Nothing here is a claim about the business — only what it is and where.
    if (!b.tagline) {
      const where = b.address?.city || 'San Diego';
      const what = (b.category || '').trim();
      b.tagline = what ? `${what} in ${where}.` : `Serving ${where}.`;
      generic.push(s);
    }
    const unknown = Object.keys(b.audit || {}).filter((k) => !checks.some((c) => c.key === k));
    if (unknown.length) console.warn(`  ! ${s}: unknown audit keys ignored: ${unknown.join(', ')}`);
    const p = pitch(b, pricing);
    fs.writeFileSync(path.join(dir(s), 'index.html'), render(b));
    fs.writeFileSync(path.join(dir(s), 'pitch.md'), p.sheet);
    // Ready to paste: subject on the first line, body underneath, no markdown.
    fs.writeFileSync(path.join(dir(s), 'email.txt'),
      `Subject: ${p.subject}\n\n${p.body}\n`);
    const failed = checks.filter((c) => (b.audit || {})[c.key] !== true).length;
    console.log(`✓ ${s} — index.html + pitch.md  (${checks.length - failed}/${checks.length} passing, ${failed} gaps to sell)`);
  }
  if (skipped.length) {
    console.log(`\n  ${skipped.length} not built:`);
    skipped.forEach((s) => console.log(`    · ${s}`));
  }
  if (generic.length) {
    console.log(`\n  ${generic.length} built with a placeholder tagline — fine to call on, worth`);
    console.log('  a better line before you send: ' + generic.slice(0, 6).join(', ')
      + (generic.length > 6 ? `, +${generic.length - 6} more` : ''));
  }
  if (list.length === 1) console.log(`\n  open clients/${list[0]}/index.html   ← check it on a phone first`);
}

// A cold-call list needs to remember who you rang and when, or you call the
// same shop twice on the same afternoon and never ring the other half.
function cmdTried(slug, note) {
  const b = load(slug);
  b.attempts = (b.attempts || 0) + 1;
  b.lastTried = new Date().toISOString().slice(0, 10);
  if (note) b.callNotes = [...(b.callNotes || []), `${b.lastTried}: ${note}`];
  save(slug, b);
  console.log(`✓ ${slug} — attempt ${b.attempts} logged${note ? ` (${note})` : ''}`);
  if (b.attempts >= 4) console.log('  Four tries is enough. ./cc status ' + slug + ' dead and move on.');
}

// Every build writes clients/<slug>/index.html. Attaching six of those to six
// emails means six files called index.html — export names them by business.
// For a salon, a bakery or a nail bar the work IS the product. A page with no
// photographs cannot compete with a booking platform that has a gallery.
async function cmdPhoto(slug, files) {
  if (!slug || !files.length) die('Usage: ./cc photo <slug> <image.jpg> [more.jpg ...]');
  const b = load(slug);
  const { embed } = require('./tools/embed-photo');
  const missing = files.filter((f) => !fs.existsSync(f));
  if (missing.length) die('Cannot find: ' + missing.join(', '));

  console.log(`Resizing and embedding ${files.length} image${files.length === 1 ? '' : 's'}…`);
  const done = await embed(files);
  b.photos = [...(b.photos || []), ...done.map((d) => ({ src: d.src, alt: `${b.name} — ${d.file}` }))];
  save(slug, b);

  const kb = (n) => Math.round(n / 1024) + 'KB';
  done.forEach((d) => console.log(`  ${d.file}: ${kb(d.before)} → ${kb(d.after)}`));
  const total = b.photos.reduce((n, p) => n + p.src.length, 0);
  console.log(`✓ ${b.photos.length} photo${b.photos.length === 1 ? '' : 's'} on the page, ${kb(total)} total`);
  if (total > 4 * 1024 * 1024) console.log('  ⚠️  Over 4MB — some mail servers will bounce it. Drop a couple.');
  console.log(`  next: ./cc build ${slug}`);
}

// We sell a twelve-point audit. Shipping a page that fails it is indefensible.
async function cmdCheck(slug) {
  const { selfCheck } = require('./tools/self-check');
  const list = (slug ? [slug] : all()).filter((s) =>
    fs.existsSync(path.join(dir(s), 'index.html')));
  if (!list.length) die('Nothing built yet.');
  console.log(`Auditing ${list.length} of our own pages with the same checks we sell…\n`);
  const res = await selfCheck(list, ROOT);
  const w = Math.max(10, ...res.map((r) => r.slug.length));
  let weak = 0;
  for (const r of res.sort((a, b) => a.pass - b.pass)) {
    const ok = r.failed.length === 0;
    if (!ok) weak++;
    console.log(`  ${ok ? '✅' : '⚠️ '} ${r.slug.padEnd(w)}  ${r.pass}/${checks.length}` +
      (ok ? '' : `  missing: ${r.failed.join(', ')}`));
  }
  console.log(`\n  ${res.length - weak} of ${res.length} pass everything we pitch.`);
  if (weak) console.log('  The rest are missing content only the business can give you —\n' +
    '  hours, address, reviews. Get them off their Google listing before sending.');
}

function cmdExport(slug) {
  const SEND = path.join(ROOT, 'send');
  const list = slug ? [slug] : all();
  fs.mkdirSync(SEND, { recursive: true });
  let n = 0;
  for (const s of list) {
    const html = path.join(dir(s), 'index.html');
    if (!fs.existsSync(html)) continue;
    fs.copyFileSync(html, path.join(SEND, `${s}.html`));
    const email = path.join(dir(s), 'email.txt');
    if (fs.existsSync(email)) fs.copyFileSync(email, path.join(SEND, `${s}-email.txt`));
    n++;
  }
  // Hours and reviews are the two the owner will notice missing, because they
  // are the two we just told him mattered. Pricing is optional — plenty of
  // trades and practices do not publish it.
  const thin = list.filter((s) => {
    const b = load(s);
    return !(b.hours || []).length || !(b.reviews || []).length;
  });
  console.log(`✓ ${n} page${n === 1 ? '' : 's'} → send/`);
  if (thin.length) {
    console.log(`\n  ⚠️  ${thin.length} of these fail checks we sell — no hours or no reviews on the page:`);
    thin.slice(0, 12).forEach((s) => {
      const b = load(s);
      const miss = [!(b.hours || []).length && 'hours', !(b.reviews || []).length && 'reviews']
        .filter(Boolean).join(' + ');
      console.log(`      ${s} (${miss})`);
    });
    console.log('      Both are on their Google listing. Run ./cc check to see the full picture.');
  }
  console.log('  each named after the business, so they do not collide in a downloads folder');
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
             tries: b.attempts ? `${b.attempts}× ${b.lastTried}` : '',
             value: tier ? pricing.currency + tier.price.toLocaleString('en-US') : '' };
  });
  if (!rows.length) return console.log('No clients yet. Run: ./cc scout --make 10');
  const ws = Math.max(8, ...rows.map((r) => r.slug.length));
  console.log(`\n${'BUSINESS'.padEnd(ws)}  STATUS    GAPS  QUOTE     CALLED         SENT`);
  console.log('─'.repeat(ws + 49));
  for (const r of rows) {
    console.log(`${r.slug.padEnd(ws)}  ${r.status.padEnd(8)}  ${String(r.gaps).padStart(4)}  ${r.value.padEnd(8)}  ${r.tries.padEnd(13)}  ${r.sent}`);
  }
  const open = rows.filter((r) => ['new', 'sent', 'replied'].includes(r.status));
  console.log(`\n${rows.length} total · ${open.length} still open · ${rows.filter((r) => r.status === 'won').length} won\n`);
}

function cmdNext(args) {
  const rank = require('./tools/next');
  const list = rank();
  const n = Number(args.find((a) => /^\d+$/.test(a))) || 8;
  const now = require('./tools/next').marketNow();

  if (!list.length) {
    console.log('\n  Nobody left to call. Run the scout, or ./cc reaudit if leads look stale.\n');
    return;
  }

  const good = list.filter((l) => l.inWindow !== false);
  console.log(`\n  ${now.label} in San Diego — ${list.length} callable, ${good.length} in a sensible window\n`);

  for (const l of list.slice(0, n)) {
    const when = l.warm ? `BOOKED ${l.callbackAt}`.trim()
      : l.inWindow === true ? 'good time now'
      : l.inWindow === false ? `wrong time — try ${l.windows}`
      : '';
    console.log(`  ${l.phone.padEnd(18)}${l.name.slice(0, 34)}`);
    console.log(`  ${' '.repeat(18)}${l.why}`);
    console.log(`  ${' '.repeat(18)}${l.vertical}${when ? ' · ' + when : ''}${l.attempts ? ` · tried ${l.attempts}x` : ''}`);
    if (l.maybeNotTheirs) console.log(`  ${' '.repeat(18)}⚠ the page never names them — open it before you pitch`);
    console.log();
  }
  const later = list.slice(n).length;
  if (later) console.log(`  …and ${later} more. ./cc next 20 to see them.\n`);
}

async function cmdReaudit(args) {
  const only = args.find((a) => !a.startsWith('--'));
  const all = args.includes('--all');
  const run = require('./tools/reaudit');
  console.log('\nRe-checking in a real browser. Findings read off raw HTML cannot see');
  console.log('JavaScript-built hours, tap-to-call links or the mobile layout, so they');
  console.log('are not safe to say to an owner holding the phone.\n');

  const { checked, note } = await run({ only, all });
  if (note) return console.log(`  ${note}\n`);

  const kept = checked.filter((r) => r.verdict === 'keep');
  const dropped = checked.filter((r) => r.verdict === 'dropped');
  const blocked = checked.filter((r) => r.verdict === 'blocked');
  const errored = checked.filter((r) => r.error);

  for (const r of checked.filter((x) => x.verdict === 'keep')) {
    const moved = r.before !== r.after ? `  (we had said ${r.before})` : '';
    console.log(`  ✓ ${r.slug.padEnd(46)} ${r.after} provable gaps${moved}`);
  }
  if (dropped.length) {
    console.log(`\n  ${dropped.length} dropped — their site is genuinely fine:`);
    dropped.forEach((r) => console.log(`    · ${r.slug} (we had said ${r.before} broken; really ${r.after})`));
  }
  const notTheirs = checked.filter((r) => r.names === false && r.verdict !== 'dropped');
  if (notTheirs.length) {
    console.log(`\n  ⚠️  ${notTheirs.length} where the page never names the business —`);
    console.log('     an expired domain resold, a listing on someone else\'s site, a stale');
    console.log('     address. The findings are accurate about the page; the page may not');
    console.log('     be theirs. Open these on a phone before you pitch them:');
    notTheirs.forEach((r) => console.log(`    · ${r.slug}`));
  }

  const over = checked.filter((r) => r.verdict === 'overclaimed');
  if (over.length) {
    console.log(`\n  ⚠️  ${over.length} you have already emailed, whose site is actually fine:`);
    over.forEach((r) => console.log(`    · ${r.slug} — we claimed ${r.before}, a browser says ${r.after}`));
    console.log('     Left as sent. If they push back, that is why.');
  }
  if (blocked.length) {
    console.log(`\n  ${blocked.length} refused our check, so we can claim nothing:`);
    blocked.forEach((r) => console.log(`    · ${r.slug} — ${r.reason}`));
  }
  if (errored.length) {
    console.log(`\n  ${errored.length} could not be checked:`);
    errored.forEach((r) => console.log(`    · ${r.slug} — ${r.error}`));
  }
  console.log(`\n  ${kept.length} still worth calling. Run ./cc build && ./cc sheet.\n`);
}

function cmdHost(slug, flags) {
  if (!slug) die('Usage: ./cc host <slug>   — prepare the folder a host serves');
  const host = require('./tools/host');
  const r = host(slug, { force: flags.includes('--force') });

  if (r.blocked) {
    console.log(`\n✗ ${slug} is not ready to go live.\n`);
    r.stop.forEach((s) => console.log(`    · ${s}`));
    console.log('\n  These are the things that embarrass you in front of a paying client.');
    console.log('  Fix them, or ./cc host ' + slug + ' --force if you truly mean it.\n');
    process.exitCode = 1;
    return;
  }

  console.log(`\n✓ sites/${slug}/ — ${r.files.join(', ')}`);
  console.log(`  serving at ${r.b.liveUrl}`);
  if (r.warn.length) {
    console.log('\n  Worth knowing, not blocking:');
    r.warn.forEach((w) => console.log(`    · ${w}`));
  }
  console.log('\n  Next: DELIVERY.md — put it up on the temporary URL first, get their');
  console.log('  approval there, and only then touch their DNS.\n');
}

function cmdSheet() {
  const build = require('./tools/call-sheet');
  const { html, state, skipped } = build();
  const out = path.join(__dirname, 'call-sheet.html');
  fs.writeFileSync(out, html);

  const by = state.leads.reduce((m, l) => (m[l.status] = (m[l.status] || 0) + 1, m), {});
  const ready = state.leads.filter((l) => ['new', 'tried'].includes(l.status) && l.built).length;
  console.log(`\n✓ call-sheet.html — ${state.leads.length} leads`);
  console.log(`  ${ready} ready to call · ${by.sent || 0} awaiting reply · ${by.won || 0} won · ${by.dead || 0} dead`);

  const thin = state.leads.filter((l) => ['new', 'tried'].includes(l.status) && l.needs.length >= 3);
  if (thin.length) {
    console.log(`\n  ${thin.length} pages are still thin — screenshot their Google listing first:`);
    for (const l of thin.slice(0, 8)) console.log(`    · ${l.name} — needs ${l.needs.join(', ')}`);
    if (thin.length > 8) console.log(`    · …and ${thin.length - 8} more`);
  }
  if (skipped.length) console.log(`\n  Left off: ${skipped.join(', ')}`);
  console.log('');
}

const [cmd, ...args] = process.argv.slice(2);
(async () => {
  switch (cmd) {
    case 'scout': await cmdScout(args); break;
    case 'audit': await cmdAudit(args[0]); break;
    case 'new': cmdNew(args[0]); break;
    case 'build': cmdBuild(args[0]); break;
    case 'tried': cmdTried(args[0], args.slice(1).join(' ')); break;
    case 'sent': cmdStatus(args[0], 'sent'); break;
    case 'status': cmdStatus(args[0], args[1]); break;
    case 'photo': await cmdPhoto(args[0], args.slice(1)); break;
    case 'check': await cmdCheck(args[0]); break;
    case 'export': cmdExport(args[0]); break;
    case 'list': cmdList(); break;
    case 'sheet': cmdSheet(); break;
    case 'host': cmdHost(args[0], args.slice(1)); break;
    case 'reaudit': await cmdReaudit(args); break;
    case 'next': cmdNext(args); break;
    default:
      for (const line of fs.readFileSync(__filename, 'utf8').split('\n').slice(1)) {
        if (!line.startsWith('//')) break;
        console.log(line.replace(/^\/\/ ?/, ''));
      }
  }
})().catch((e) => die(e.message));
