// The morning dashboard: everyone we have actually reached, and who is next.
//
// Two lists on one page, rebuilt every morning by Actions and committed, so
// "where are we" is never in someone's head, a scratch folder, or a Gmail
// search.
//
//   Contacted — every business we have emailed, called or texted, what came
//               back, and what is owed next (a chase, a booked callback).
//   Up next   — the 25–50 we have NOT reached, in the order worth working: a
//               page already built beats a bare lead, and the board's own
//               ranking (worst site first, callable first) decides the rest.
//
// Nothing here is a new source of truth. It reads clients/, leads/, the send
// log and the suppression list, and reuses the rules the tools that write
// those files already enforce: board.js decides who is worth calling,
// campaign.js decides what a page still lacks before it may be sent, and
// brief.js knows when each kind of business answers the phone.

const fs = require('fs');
const path = require('path');
const board = require('./board');
const sendlog = require('./sendlog');
const suppress = require('./suppress');
const { unsendable } = require('./campaign');
const { windowFor, TZ } = require('./brief');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');
const hosting = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/hosting.json'), 'utf8'));

const today = () => new Date().toISOString().slice(0, 10);
const day = (s) => (s ? String(s).slice(0, 10) : '');
const daysBetween = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400e3);

function domainOf(url) {
  if (!url) return '';
  try { return new URL(/^https?:\/\//.test(url) ? url : 'https://' + url).hostname.replace(/^www\./, ''); }
  catch { return ''; }
}

function loadClient(slug) {
  try { return JSON.parse(fs.readFileSync(path.join(CLIENTS, slug, 'business.json'), 'utf8')); }
  catch { return null; }
}

// The page a pitch links to. liveUrl is authoritative when it is on the
// hosting domain; anything else (the githack era) is rebuilt from the slug.
function pageUrlFor(slug, b) {
  const dom = hosting.cloudflarePagesDomain;
  if (!dom) return null;
  if (b.liveUrl && b.liveUrl.includes(dom)) return b.liveUrl;
  return `https://${dom}/${slug}/`;
}

// A suppression entry names the business three ways at most; match on any.
function suppressionFor(slug, b) {
  const rows = suppress.list();
  const email = String(b.email || '').toLowerCase();
  const dom = domainOf(b.currentSite);
  return rows.find((r) =>
    (r.slug && r.slug === slug) ||
    (email && r.email && r.email.toLowerCase() === email) ||
    (dom && r.domain && r.domain.toLowerCase() === dom)) || null;
}

// "Contacted" means a real attempt reached out of this building: a logged
// send, a dialled number, a bounce, a callback they agreed to, or a name on
// the do-not-contact list (nobody asks us to stop before we have started).
function contactedWith(b, sends, sup) {
  if (sends.length) return true;
  if (['sent', 'replied', 'won'].includes(b.status)) return true;
  if (b.sentOn || b.emailBounced || b.callbackAt) return true;
  if ((b.attempts || 0) > 0) return true;
  if (sup) return true;
  return false;
}

function lastContactDate(b, sends) {
  const dates = [
    ...sends.map((s) => day(s.at)),
    day(b.sentOn), day(b.lastTried),
    ...(b.callNotes || []).map((n) => (String(n).match(/^(\d{4}-\d{2}-\d{2})/) || [])[1]),
  ].filter(Boolean).sort();
  return dates[dates.length - 1] || '';
}

function outcomeOf(b, sends, sup) {
  const status = b.status || 'new';
  if (sup && /stop|complain|escalat/i.test(sup.reason || '')) return { key: 'stopped', label: 'asked us to stop', tone: 'bad' };
  if (status === 'won') return { key: 'won', label: 'won', tone: 'good' };
  if (status === 'replied') return { key: 'replied', label: 'replied', tone: 'good' };
  if (b.emailBounced || sends.some((s) => s.outcome === 'bounce') || (sup && /bounce/i.test(sup.reason || ''))) {
    return { key: 'bounced', label: 'email bounced', tone: 'bad' };
  }
  if (status === 'dead') return { key: 'closed', label: 'closed out', tone: 'muted' };
  const lastSend = sends.map((s) => day(s.at)).concat(day(b.sentOn)).filter(Boolean).sort().pop();
  if (status === 'sent' || lastSend) {
    const d = lastSend ? daysBetween(lastSend, today()) : null;
    return { key: 'waiting', label: d == null ? 'sent' : d === 0 ? 'sent today' : `no reply · ${d}d`, tone: d >= 3 ? 'warn' : 'accent' };
  }
  if (b.attempts) return { key: 'noanswer', label: `no answer · ${b.attempts} ${b.attempts === 1 ? 'try' : 'tries'}`, tone: 'warn' };
  return { key: 'other', label: status, tone: 'muted' };
}

// What is owed, and when. A callback they asked for is a promise; a revisit
// date is their timing (Seth: "not quite there yet"), so it is soft; three
// days of silence after an email is the point CALL.md says to pick the
// phone up instead of sending another one.
function followUpFor(b, outcome, lastAt) {
  const t = today();
  if (b.callbackAt && !['won', 'dead'].includes(b.status)) {
    const d = day(b.callbackAt);
    return { at: d, time: String(b.callbackAt).slice(11).trim(), why: 'callback they asked for', overdue: d < t, today: d === t };
  }
  if (b.revisitAfter && !['won', 'dead'].includes(b.status)) {
    return { at: b.revisitAfter, why: 'revisit — their timing, not a no', overdue: false, today: b.revisitAfter <= t, soft: true };
  }
  if (outcome.key === 'waiting' && lastAt && daysBetween(lastAt, t) >= 3) {
    return { at: t, why: `emailed ${daysBetween(lastAt, t)} days ago, no reply — call, do not re-send`, overdue: true, today: true };
  }
  return null;
}

// Short chips for what campaign.js would refuse to send this page over.
function shortGaps(b) {
  const out = [];
  for (const why of unsendable(b)) {
    if (/not researched/.test(why)) out.push('not researched');
    else if (/no real hours/.test(why)) out.push('no hours');
    else if (/no real reviews/.test(why)) out.push('no reviews');
    else if (/bot challenge/.test(why)) out.push('site behind a bot check');
    else if (/never names them/.test(why)) out.push('URL may not be theirs');
    else if (/managed platform/.test(why)) out.push('on a managed platform');
    else if (/could not reach/.test(why)) out.push('site unreachable');
    else if (/license/.test(why)) out.push('license needs checking');
    else out.push(why.split(' — ')[0]);
  }
  return out;
}

function channelOf(b, sends) {
  const email = sends.length || b.sentOn || b.emailBounced;
  const call = (b.attempts || 0) > 0 || b.callbackAt;
  return email && call ? 'email + call' : email ? 'email' : call ? 'call' : 'other';
}

function contactLine(b, sends) {
  const bits = [];
  const lastSend = sends[sends.length - 1];
  if (lastSend) bits.push(`Emailed ${fmt(day(lastSend.at))} → ${lastSend.to}${sends.length > 1 ? ` (${sends.length} sends)` : ''}`);
  else if (b.sentOn) bits.push(`Emailed ${fmt(b.sentOn)}${b.email ? ' → ' + b.email : ''}`);
  else if (b.emailBounced) bits.push(`Emailed ${b.emailBounced} — bounced`);
  if (b.attempts) bits.push(`Called ×${b.attempts}${b.lastTried ? ', last ' + fmt(b.lastTried) : ''}`);
  return bits.join(' · ');
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmt(d) {
  if (!d) return '';
  const [, m, dd] = String(d).match(/^\d{4}-(\d{2})-(\d{2})/) || [];
  return m ? `${Number(dd)} ${MONTHS[Number(m) - 1]}` : String(d);
}

// Does the Worker actually serve this page yet? A page built on a branch is
// not live until it reaches main, and a link that 404s in front of an owner
// is worse than no link. Checked with a HEAD per page, in parallel, and
// answered honestly as unknown when the network is not there.
async function liveCheck(urls, { timeout = 8000, concurrency = 6 } = {}) {
  const out = new Map();
  const queue = [...new Set(urls)];
  const one = async () => {
    while (queue.length) {
      const u = queue.shift();
      try {
        const r = await fetch(u, { method: 'HEAD', redirect: 'follow', signal: AbortSignal.timeout(timeout) });
        out.set(u, r.ok);
      } catch { out.set(u, null); }
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, queue.length) }, one));
  return out;
}

function timeWindow(category, state) {
  const w = windowFor(category);
  const tz = TZ[state] || null;
  const clock = (h, m) => {
    const ap = h >= 12 ? 'pm' : 'am';
    const hh = h % 12 || 12;
    return m ? `${hh}:${String(m).padStart(2, '0')}${ap}` : `${hh}${ap}`;
  };
  return {
    name: w.name,
    why: w.why,
    tz,
    slots: w.slots,
    text: w.slots.map(([h1, m1, h2, m2]) => `${clock(h1, m1)}–${clock(h2, m2)}`).join(' or '),
  };
}

async function build({ limit = 50, offline = false } = {}) {
  const sendsBySlug = new Map();
  for (const s of sendlog.all()) {
    if (!sendsBySlug.has(s.slug)) sendsBySlug.set(s.slug, []);
    sendsBySlug.get(s.slug).push(s);
  }

  const rows = board.build();
  const byRowSlug = new Map(rows.filter((r) => r.source === 'pipeline').map((r) => [r.slug, r]));

  const contacted = [];
  const contactedSlugs = new Set();
  let builtPages = 0;
  let closedUnreached = 0;

  for (const slug of fs.readdirSync(CLIENTS).sort()) {
    if (slug.startsWith('example-')) continue;
    const b = loadClient(slug);
    if (!b || b.status === 'spec') continue;
    const built = fs.existsSync(path.join(CLIENTS, slug, 'index.html'));
    if (built) builtPages++;

    const sends = sendsBySlug.get(slug) || [];
    const sup = suppressionFor(slug, b);
    if (!contactedWith(b, sends, sup)) {
      if (b.status === 'dead') closedUnreached++;
      continue;
    }
    contactedSlugs.add(slug);

    const outcome = outcomeOf(b, sends, sup);
    const lastAt = lastContactDate(b, sends);
    const row = byRowSlug.get(slug);
    const notes = b.callNotes || [];
    contacted.push({
      slug,
      name: b.name || slug,
      category: b.category || '',
      city: b.address?.city || '',
      state: b.address?.state || (row ? row.state : ''),
      phone: row ? row.phone : board.prettyPhone(b.phone),
      email: b.email || '',
      site: b.currentSite || '',
      built,
      pageUrl: built ? pageUrlFor(slug, b) : null,
      live: null,
      status: b.status || 'new',
      warm: Boolean(b.pitchEmail),
      channel: channelOf(b, sends),
      line: contactLine(b, sends),
      sends: sends.map((s) => ({
        at: day(s.at), to: s.to, subject: s.subject, outcome: s.outcome || '',
        thread: s.threadId ? `https://mail.google.com/mail/u/0/#all/${s.threadId}` : '',
      })),
      attempts: b.attempts || 0,
      lastAt,
      daysSince: lastAt ? daysBetween(lastAt, today()) : null,
      outcome,
      followUp: followUpFor(b, outcome, lastAt),
      suppressed: sup ? { reason: sup.reason, at: sup.at } : null,
      lastNote: notes[notes.length - 1] || b._dead || b._status || '',
      gaps: built && !['dead', 'won'].includes(b.status) ? shortGaps(b) : [],
    });
  }

  // Most recent contact first; anything owed floats above that in its own list.
  contacted.sort((a, b) => (b.lastAt || '').localeCompare(a.lastAt || '') || a.name.localeCompare(b.name));

  const followUps = contacted
    .filter((c) => c.followUp)
    .map((c) => ({ ...c.followUp, slug: c.slug, name: c.name, phone: c.phone, category: c.category, pageUrl: c.pageUrl }))
    .sort((a, b) => a.at.localeCompare(b.at));

  // Up next: nobody we have reached, nobody the board would refuse to dial,
  // nobody on the do-not-contact list. Built pages first — the work is done,
  // it only needs a phone call — then the board's own order.
  const setAside = {};
  const candidates = [];
  for (const r of rows) {
    if (r.source === 'pipeline' && contactedSlugs.has(r.slug)) continue;
    if (r.status !== 'new') continue;
    if (r.blocked) { setAside[r.blocked] = (setAside[r.blocked] || 0) + 1; continue; }
    if (suppress.isSuppressed({ email: r.email, domain: domainOf(r.site), phone: r.phone })) {
      setAside['on the do-not-contact list'] = (setAside['on the do-not-contact list'] || 0) + 1;
      continue;
    }
    candidates.push(r);
  }
  candidates.sort((a, b) => (b.built ? 1 : 0) - (a.built ? 1 : 0));   // stable: keeps the board's order inside each half

  const next = candidates.slice(0, Math.max(limit, 25)).map((r, i) => {
    const b = r.source === 'pipeline' ? loadClient(r.slug) : null;
    return {
      rank: i + 1,
      slug: r.slug,
      source: r.source,
      name: r.name,
      category: r.category,
      city: r.city,
      state: r.state,
      stateDerived: r.stateDerived,
      phone: r.phone,
      email: r.email,
      site: r.site,
      parked: r.parked,
      passed: r.passed,
      of: r.of,
      audit: r.audit,
      rendered: r.rendered,
      flaw: r.flaw,
      checkUrl: r.checkUrl,
      built: r.built,
      pageUrl: r.built && b ? pageUrlFor(r.slug, b) : null,
      live: null,
      gaps: b && r.built ? shortGaps(b) : [],
      window: timeWindow(r.category, r.state),
    };
  });

  if (!offline) {
    const urls = [...contacted, ...next].map((c) => c.pageUrl).filter(Boolean);
    const live = await liveCheck(urls);
    for (const c of [...contacted, ...next]) if (c.pageUrl) c.live = live.get(c.pageUrl) ?? null;
  }

  const t = today();
  const weekAgo = new Date(Date.now() - 7 * 86400e3).toISOString().slice(0, 10);
  const sends = sendlog.all();
  const count = (k) => contacted.filter((c) => c.outcome.key === k).length;

  return {
    builtAt: t,
    domain: hosting.cloudflarePagesDomain,
    stats: {
      contacted: contacted.length,
      waiting: count('waiting'),
      replied: count('replied') + count('won'),
      won: count('won'),
      bounced: count('bounced') + count('stopped'),
      noAnswer: count('noanswer'),
      due: followUps.filter((f) => f.overdue || f.today).length,
      next: next.length,
      pool: candidates.length,
      measured: rows.length,
      builtPages,
      live: [...contacted, ...next].filter((c) => c.live === true).length,
      sentThisWeek: sends.filter((s) => day(s.at) >= weekAgo).length,
      closedUnreached,
    },
    contacted,
    followUps,
    next,
    setAside: Object.entries(setAside).sort((a, b) => b[1] - a[1]),
  };
}

module.exports = { build, fmt };
