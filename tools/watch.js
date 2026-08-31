// Watches sites over time and reports what CHANGED.
//
// An audit tells you what a site is like today. That is worth something once,
// at the pitch. What a paying client is actually buying for $60 a month is
// somebody noticing — before they do — that their site went down on a Sunday,
// that their certificate expired, that a plugin update tripled the load time,
// or that their domain quietly lapsed.
//
// So this stores a snapshot each run and reports only the differences. A run
// where nothing changed says nothing, because an alert that fires every day is
// an alert nobody reads.

const fs = require('fs');
const path = require('path');
const checks = require('./checks');
const { auditRendered, chromium, EXEC } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');
const STORE = path.join(ROOT, 'watch');
const HARD = checks.filter((c) => !c.soft);
const KEEP = 60;                       // snapshots per site

// How bad is it. Anything 'critical' is worth waking someone for; the rest can
// wait for the morning summary.
const CRITICAL = new Set(['down', 'parked', 'insecure', 'stripped']);

function monitored() {
  const out = [];
  for (const slug of fs.readdirSync(path.join(ROOT, 'clients')).sort()) {
    const f = path.join(ROOT, 'clients', slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }
    if (slug.startsWith('example-')) continue;

    // A paying client's live site is what we are responsible for. A prospect's
    // own site is watched too, because a site that gets fixed is a lead to drop
    // and a site that breaks is a reason to call today.
    const url = b.status === 'won' ? (b.liveUrl || b.currentSite) : b.currentSite;
    if (!url) continue;
    if (['dead'].includes(b.status)) continue;
    out.push({ slug, name: b.name || slug, url, paying: b.status === 'won', phone: b.phone || '' });
  }
  return out;
}

const snapFile = (slug) => path.join(STORE, `${slug}.json`);

function history(slug) {
  const f = snapFile(slug);
  if (!fs.existsSync(f)) return [];
  try { return JSON.parse(fs.readFileSync(f, 'utf8')).snapshots || []; }
  catch { return []; }
}

function snapshotOf(a) {
  return {
    at: new Date().toISOString(),
    reachable: a.reachable, blocked: Boolean(a.blocked), reason: a.reason || null,
    ms: a.ms ?? null, kb: a.kb ?? null,
    checks: Object.fromEntries(HARD.map((c) => [c.key, (a.checks || {})[c.key] === true])),
    parked: /parked|placeholder|for sale/i.test(a.reason || ''),
  };
}

// What is worth telling someone about, given what it looked like last time.
function diff(prev, now, site) {
  const events = [];
  const say = (kind, text) => events.push({ kind, text, critical: CRITICAL.has(kind), site });

  if (now.blocked) {
    // A site that starts refusing us is usually a firewall or a bot rule, not a
    // fault. Say it once, quietly, and stop measuring it.
    if (!prev || !prev.blocked) say('blocked', `now refuses our check (${now.reason}) — we can no longer measure it`);
    return events;
  }

  if (now.reachable === false) {
    if (!prev || prev.reachable !== false) say('down', `is not loading — ${now.reason || 'unreachable'}`);
    return events;                     // nothing else is measurable
  }
  if (prev && prev.reachable === false && now.reachable) say('recovered', 'is back up');

  if (now.parked && (!prev || !prev.parked)) {
    say('parked', 'now shows a parked or for-sale page — the domain may have lapsed');
  }

  if (prev) {
    for (const c of HARD) {
      const was = prev.checks?.[c.key], is = now.checks[c.key];
      if (was === true && is === false) {
        say(c.key === 'https' ? 'insecure' : 'regressed', `${c.label.toLowerCase()} stopped working`);
      } else if (was === false && is === true) {
        say('improved', `${c.label.toLowerCase()} now passes`);
      }
    }

    // Slower is only news if it is much slower and actually slow.
    if (prev.ms && now.ms && now.ms > prev.ms * 2 && now.ms > 5000) {
      say('slower', `went from ${(prev.ms / 1000).toFixed(1)}s to ${(now.ms / 1000).toFixed(1)}s`);
    }
    // A page that loses half its weight has usually lost half its content.
    if (prev.kb && now.kb && now.kb < prev.kb * 0.5 && prev.kb > 20) {
      say('stripped', `dropped from ${prev.kb}KB to ${now.kb}KB — content may be missing`);
    }
  }

  return events;
}

async function run({ only, log = console.log } = {}) {
  await require('./reaudit').assertOnline();
  fs.mkdirSync(STORE, { recursive: true });

  let sites = monitored();
  if (only) sites = sites.filter((s) => s.slug === only);
  if (!sites.length) return { events: [], checked: 0 };

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const events = [];
  let checked = 0;

  try {
    for (const site of sites) {
      let a;
      try { a = await auditRendered(site.url, { browser, expectName: site.name }); }
      catch (e) { log(`  ! ${site.slug}: ${e.message.split('\n')[0]}`); continue; }

      const past = history(site.slug);
      const prev = past[past.length - 1] || null;
      const now = snapshotOf(a);

      for (const ev of diff(prev, now, site)) events.push(ev);

      past.push(now);
      fs.writeFileSync(snapFile(site.slug), JSON.stringify({
        slug: site.slug, name: site.name, url: site.url, paying: site.paying,
        snapshots: past.slice(-KEEP),
      }, null, 2));
      checked++;
      log(`  ${prev ? '·' : '+'} ${site.slug}`);
    }
  } finally {
    await browser.close();
  }

  // A client who pays us comes first, then anything critical.
  events.sort((x, y) => (y.site.paying - x.site.paying) || (y.critical - x.critical));
  return { events, checked };
}

module.exports = run;
module.exports.monitored = monitored;
module.exports.history = history;
