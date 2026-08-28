// Re-checks clients we already scaffolded, in a real browser this time.
//
// Leads scaffolded before the browser auditor existed carry findings read off
// raw HTML. That misses anything JavaScript builds — hours, tap-to-call links,
// the mobile layout itself — so those pages look far worse than they are. Every
// one of those findings is unsafe to say to an owner who is holding the phone
// and looking at the site working.
//
// This replaces them with measured ones, and says plainly which leads stop
// being leads as a result. A business whose site is fine is not a lost lead —
// it is a call you no longer have to waste.

const fs = require('fs');
const path = require('path');
const checks = require('./checks');
const { auditRendered, chromium, EXEC } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');

// Below this many real failures there is nothing to sell, and pitching anyway
// is how you end up arguing with someone about their own website.
const WORTH_IT = 5;

function open() {
  const out = [];
  for (const slug of fs.readdirSync(path.join(ROOT, 'clients')).sort()) {
    const f = path.join(ROOT, 'clients', slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }
    if (['won', 'spec'].includes(b.status) || slug.startsWith('example-')) continue;
    out.push({ slug, f, b });
  }
  return out;
}

async function run({ only, all = false, log = console.log } = {}) {
  let list = open();
  if (only) list = list.filter((c) => c.slug === only);
  if (!all) list = list.filter((c) => (c.b._scout || {}).rendered !== true);
  list = list.filter((c) => c.b.currentSite);

  if (!list.length) return { checked: [], note: 'nothing to re-check' };

  // A sandboxed network refuses CONNECT with a 403, which is indistinguishable
  // from a site refusing us — and that reading gets written into the lead as
  // "dropped, site refused our check". One bad run would quietly poison the
  // whole list. Prove we can reach the open internet before touching anything.
  await assertOnline();

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const results = [];

  try {
    for (const { slug, f, b } of list) {
      let a;
      try { a = await auditRendered(b.currentSite, { browser, expectName: b.name }); }
      catch (e) { results.push({ slug, name: b.name, error: e.message }); continue; }

      const before = Object.values(b.audit || {}).filter((v) => v !== true).length;

      if (a.blocked) {
        // Refused, not broken. We cannot claim anything about a site we were
        // not allowed to see, and a site behind a firewall usually has someone
        // already looking after it. A lead already emailed keeps its status:
        // that is a conversation in progress, not ours to close.
        if (!['sent', 'replied'].includes(b.status)) b.status = 'dead';
        b._scout = { ...(b._scout || {}), rendered: true, currentSiteStatus: `blocked: ${a.reason}` };
        b.callNotes = [...(b.callNotes || []), `${today()}: dropped — site refused our check (${a.reason}), nothing we can honestly claim`];
        fs.writeFileSync(f, JSON.stringify(b, null, 2));
        results.push({ slug, name: b.name, before, after: null, verdict: 'blocked', reason: a.reason });
        continue;
      }

      b.audit = a.checks;
      b._scout = {
        ...(b._scout || {}),
        gaps: a.gaps, rendered: true, namesBusiness: a.namesBusiness,
        currentSiteStatus: a.reachable ? (a.reason || 'live') : `unreachable: ${a.reason}`,
        loadMs: a.ms ?? null, pageKb: a.kb ?? null,
      };

      // Only the checks we can actually prove decide whether there is a job
      // here. The soft ones are for our eyes and were never claimable.
      const hard = checks.filter((c) => !c.soft);
      const realGaps = hard.filter((c) => a.checks[c.key] !== true).length;

      let verdict = 'keep';
      // A lead he has already emailed is a live conversation, not a candidate.
      // Correcting its findings is right; deciding on his behalf that it is
      // dead deletes a deal he is waiting on a reply to.
      const inFlight = ['sent', 'replied'].includes(b.status);
      if (realGaps < WORTH_IT && a.reachable && !inFlight) {
        b.status = 'dead';
        b.callNotes = [...(b.callNotes || []), `${today()}: dropped — site checks out in a real browser (${realGaps} provable gaps), nothing worth selling`];
        verdict = 'dropped';
      } else if (realGaps < WORTH_IT && a.reachable && inFlight) {
        verdict = 'overclaimed';
      }
      fs.writeFileSync(f, JSON.stringify(b, null, 2));
      results.push({ slug, name: b.name, before, after: realGaps, verdict,
                     reachable: a.reachable, reason: a.reason, names: a.namesBusiness });
    }
  } finally {
    await browser.close();
  }

  return { checked: results };
}

const today = () => new Date().toISOString().slice(0, 10);

async function assertOnline() {
  const probe = 'https://example.com/';
  let res;
  try {
    res = await fetch(probe, { redirect: 'follow', signal: AbortSignal.timeout(15000) });
  } catch (e) {
    throw new Error(
      `no route to the open internet (${e.message}).\n` +
      '  Everything this touches would be recorded as the site refusing us, and\n' +
      '  live leads would be marked dead on a reading of the network, not the site.\n' +
      '  Run it where egress works: Actions tab -> Re-audit leads -> Run workflow.');
  }
  if (!res.ok) {
    throw new Error(
      `the network is answering ${res.status} for ${probe}, so it is filtering us, not the sites.\n` +
      '  Run it on GitHub Actions instead: Actions tab -> Re-audit leads -> Run workflow.');
  }
}

module.exports = run;
module.exports.assertOnline = assertOnline;
