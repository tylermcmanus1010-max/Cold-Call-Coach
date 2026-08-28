// Who to call, right now, in order.
//
// Ranking a lead by how broken its website is gets the order wrong. A booked
// callback beats a stranger with twice the gaps, a trade beats a salon, and
// none of it matters if the business is shut — three calls went to voicemail
// at 5pm because the list did not know what time it was.

const fs = require('fs');
const path = require('path');
const checks = require('./checks');

const ROOT = path.join(__dirname, '..');

// The businesses are in San Diego and the machine may be anywhere — a runner
// on UTC read 5pm Thursday as midnight Friday and called every window wrong.
const MARKET_TZ = process.env.MARKET_TZ || 'America/Los_Angeles';

function marketNow(d = new Date()) {
  const p = new Intl.DateTimeFormat('en-US', {
    timeZone: MARKET_TZ, weekday: 'short', hour: 'numeric', minute: '2-digit',
    hour12: false, year: 'numeric', month: 'short', day: 'numeric',
  }).formatToParts(d).reduce((o, x) => (o[x.type] = x.value, o), {});
  const days = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    day: days[p.weekday],
    hours: +p.hour % 24,
    minutes: +p.minute,
    label: `${p.weekday} ${((+p.hour % 12) || 12)}:${p.minute} ${+p.hour < 12 ? 'am' : 'pm'}`,
  };
}
const HARD = checks.filter((c) => !c.soft);

// Best window to catch each kind of business, and the hours to avoid. From
// CALL.md, which came from actually calling them.
const WINDOWS = [
  { re: /plumb|roof|electric|hvac|contractor|construct|carpenter|painter|glaz|upholster|floor|tiler|locksmith|garden|metal|window/i,
    label: 'trades', hours: [[7, 8], [16, 17]], avoid: 'mid-morning, they are on a job' },
  { re: /auto|car|tyre|tire|smog|mechanic/i,
    label: 'auto', hours: [[7, 9], [16, 17]], avoid: 'lunchtime' },
  { re: /dentist|dental|endodont|doctor|medical|clinic|vet|chiro|ortho|optician/i,
    label: 'medical', hours: [[9, 11], [14, 16]], avoid: 'Monday morning and lunch' },
  { re: /salon|nail|lash|hair|barber|beauty|spa|massage/i,
    label: 'salons', hours: [[10, 11]], avoid: 'Friday, Saturday and lunchtime', badDays: [5, 6] },
  { re: /baker|cafe|café|restaurant|deli|food|caterer|butcher/i,
    label: 'food', hours: [[14, 16]], avoid: 'any mealtime' },
  { re: /lawyer|attorney|account|insurance|estate|financial|office/i,
    label: 'professional', hours: [[9, 11], [14, 16]], avoid: 'Monday morning' },
  { re: /fitness|gym|yoga|climb|training|studio/i,
    label: 'fitness', hours: [[10, 12], [17, 19]], avoid: 'the 6am and 6pm class rush' },
  { re: /florist|flower|shop|store|retail|hardware|furniture|apparel|pet|tailor|cleaner|laundry/i,
    label: 'retail', hours: [[10, 12], [14, 16]], avoid: 'opening and closing, and Saturdays' },
];

const windowFor = (cat) => WINDOWS.find((w) => w.re.test(cat || '')) || null;

// 800, 888, 877, 866, 855, 844, 833 — a toll-free line means a call centre or
// a multi-location outfit. Whoever answers cannot buy a website.
const TOLL_FREE = /^\+?1?[^0-9]*8(00|33|44|55|66|77|88)/;

// Trades and clinics buy. Businesses whose whole product is how things look
// tend to already have someone doing their website.
const VERTICAL_WEIGHT = { trades: 3, auto: 3, medical: 2, professional: 2, retail: 1, food: 1, fitness: 1, salons: 0 };

function openNow(w, now) {
  if (!w) return null;
  if (now.day === 0 || now.day === 6) return false;   // weekend
  if (w.badDays && w.badDays.includes(now.day)) return false;
  const h = now.hours + now.minutes / 60;
  return w.hours.some(([a, b]) => h >= a && h < b);
}

function rank({ now = marketNow() } = {}) {
  const out = [];
  for (const slug of fs.readdirSync(path.join(ROOT, 'clients')).sort()) {
    const f = path.join(ROOT, 'clients', slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }

    if (['dead', 'won', 'spec', 'sent'].includes(b.status) || slug.startsWith('example-')) continue;
    if (!b.phone) continue;
    if (TOLL_FREE.test(b.phone)) continue;
    if ((b.attempts || 0) >= 4) continue;          // four tries is enough
    if ((b._scout || {}).rendered !== true) continue;  // never claim unverified findings

    const w = windowFor(b.category);
    const gaps = HARD.filter((c) => (b.audit || {})[c.key] !== true).length;
    const warm = b.status === 'replied' || Boolean(b.callbackAt);
    const inWindow = openNow(w, now);

    // A booked callback outranks everything. After that: is it a good time,
    // is it a vertical that buys, and only then how broken the site is.
    const score = (warm ? 1000 : 0)
      + (inWindow === true ? 200 : inWindow === false ? 0 : 100)
      + (VERTICAL_WEIGHT[w?.label] ?? 1) * 20
      + gaps * 5
      - (b.attempts || 0) * 15;

    out.push({
      slug, name: b.name, phone: b.phone, cat: b.category || '',
      gaps, warm, callbackAt: b.callbackAt || '', interested: b.status === 'replied', attempts: b.attempts || 0,
      vertical: w?.label || 'other', inWindow, avoid: w?.avoid || '',
      windows: w ? w.hours.map(([a, c]) => `${a}–${c}`).join(', ') : '',
      why: reason(b, gaps),
      maybeNotTheirs: (b._scout || {}).namesBusiness === false,
      score,
    });
  }
  return out.sort((a, b) => b.score - a.score);
}

// One line he can actually say, drawn only from what we measured.
function reason(b, gaps) {
  const sc = b._scout || {};
  const a = b.audit || {};
  if (/placeholder|parked/i.test(sc.currentSiteStatus || '')) return 'no real website — domain sits on a placeholder';
  if (sc.loadMs > 8000) {
    // Three runs put one site at 19s, 29s and 99s. A number that swings that
    // far is not a number to say out loud — let the owner time it themselves.
    const r = (sc.loadMsReadings || []).concat(sc.loadMs);
    const spread = Math.max(...r) / Math.min(...r);
    return r.length > 1 && spread > 2
      ? 'site is very slow on a phone — have them time it themselves'
      : `site takes ${(sc.loadMs / 1000).toFixed(0)} seconds to load`;
  }
  if (sc.pageKb != null && sc.pageKb < 10 && a.mobile !== true) return `page is ${sc.pageKb}KB — almost nothing on it`;
  if (a.mobile !== true) return 'does not work properly on a phone';
  if (a.phoneTap !== true) return 'phone number is not tappable';
  if (a.seo !== true) return 'no Google business markup';
  return `${gaps} of ${HARD.length} provable checks failing`;
}

module.exports = rank;
module.exports.windowFor = windowFor;
module.exports.marketNow = marketNow;
