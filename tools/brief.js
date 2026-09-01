// Who can you actually call, right now, given where they are.
//
// The board is a national list, and that changes what an early alarm is worth.
// At 5am in San Diego it is 8am in Wilmington and 7am in Milwaukee — the exact
// hour a plumber answers, sitting in the van before the first job. A list
// sorted by how broken a site is will hand him a dentist in Chula Vista who
// will not pick up for four hours.
//
// So this sorts by whether they can hear the phone.

const { build } = require('./board');

// Nobody in these states is in the same hour. Arizona does not observe DST,
// which between March and November puts it on Pacific time, not Mountain.
const TZ = {
  CA: 'America/Los_Angeles', WA: 'America/Los_Angeles',
  AZ: 'America/Phoenix',
  CO: 'America/Denver',
  OK: 'America/Chicago', WI: 'America/Chicago', TN: 'America/Chicago',
  NE: 'America/Chicago', IL: 'America/Chicago', TX: 'America/Chicago',
  DE: 'America/New_York', NC: 'America/New_York', OH: 'America/New_York',
  FL: 'America/New_York', NJ: 'America/New_York', IN: 'America/New_York',
  NY: 'America/New_York', PA: 'America/New_York', GA: 'America/New_York',
};

// When each kind of business is by the phone, in their own local time.
// Learned the expensive way: three calls logged at 5pm last week all went to
// voicemail, every one of them to a business that answers in the morning.
const WINDOWS = [
  { test: /plumb|roof|electric|hvac|contractor|construct|carpenter|painter|glaz|floor|tiler|locksmith|garden|landscap|metal|window/i,
    name: 'trades', slots: [[7, 0, 8, 30], [16, 0, 17, 30]],
    why: 'in the van, before the first job or after the last' },
  { test: /bakery|baker|patisserie|caterer|butcher/i,
    name: 'bakery', slots: [[6, 0, 9, 0], [14, 0, 16, 0]],
    why: 'bakers have been in for hours by 6am and are quiet before the counter opens' },
  { test: /car|auto|tyre|tire|smog|transmission|body/i,
    name: 'auto', slots: [[8, 0, 9, 30], [15, 30, 17, 0]],
    why: 'the shop opens at 8 and the bays are not full yet' },
  { test: /dentist|dental|orthodont|doctor|medical|veterin|vet|clinic|optician/i,
    name: 'clinic', slots: [[9, 0, 11, 0]],
    why: 'after they open, before the waiting room fills' },
  { test: /hair|beauty|nail|salon|massage|spa|barber|lash|cosmetic/i,
    name: 'salon', slots: [[10, 0, 11, 30], [14, 0, 16, 0]],
    why: 'between the morning and afternoon books' },
  { test: /lawyer|account|insurance|estate|financial|law/i,
    name: 'office', slots: [[9, 0, 11, 30], [14, 0, 16, 30]],
    why: 'office hours, avoiding lunch' },
  { test: /fitness|gym|yoga|training/i,
    name: 'fitness', slots: [[10, 0, 16, 0]],
    why: 'the owner is in between the early and evening classes' },
];

const DEFAULT_WINDOW = { name: 'business', slots: [[9, 0, 11, 30], [14, 0, 16, 30]], why: 'ordinary business hours' };

function windowFor(category) {
  return WINDOWS.find((w) => w.test.test(category || '')) || DEFAULT_WINDOW;
}

// Their local wall-clock time, as minutes past midnight, at a given instant.
function localMinutes(when, state) {
  const tz = TZ[state];
  if (!tz) return null;
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hour: 'numeric', minute: 'numeric', weekday: 'short', hour12: false,
  }).formatToParts(when);
  const get = (t) => parts.find((p) => p.type === t)?.value;
  const h = Number(get('hour')) % 24;
  return { minutes: h * 60 + Number(get('minute')), day: get('weekday'), tz };
}

function statusAt(row, when) {
  const loc = localMinutes(when, row.state);
  if (!loc) return { open: false, note: 'we do not know what time it is where they are' };

  const w = windowFor(row.category);
  const weekend = loc.day === 'Sat' || loc.day === 'Sun';
  const hhmm = `${String(Math.floor(loc.minutes / 60)).padStart(2, '0')}:${String(loc.minutes % 60).padStart(2, '0')}`;

  if (weekend) return { open: false, local: hhmm, day: loc.day, note: `${loc.day} where they are`, w };

  for (const [h1, m1, h2, m2] of w.slots) {
    const a = h1 * 60 + m1, b = h2 * 60 + m2;
    if (loc.minutes >= a && loc.minutes <= b) {
      return { open: true, local: hhmm, day: loc.day, w, until: b - loc.minutes };
    }
  }
  // How long until the next window opens today.
  const next = w.slots.map(([h, m]) => h * 60 + m).filter((a) => a > loc.minutes).sort((x, y) => x - y)[0];
  return { open: false, local: hhmm, day: loc.day, w, opensIn: next != null ? next - loc.minutes : null };
}

function brief(when = new Date(), { limit = 25 } = {}) {
  const rows = build().filter((r) => !r.blocked && r.phone);

  const scored = rows.map((r) => {
    const s = statusAt(r, when);
    return { ...r, when: s };
  });

  const open = scored.filter((r) => r.when.open)
    // Most broken first among those who can actually answer, and a parked
    // domain is the easiest call there is.
    .sort((a, b) => (b.parked ? 1 : 0) - (a.parked ? 1 : 0) || a.passed - b.passed);

  const soon = scored.filter((r) => !r.when.open && r.when.opensIn != null && r.when.opensIn <= 180)
    .sort((a, b) => a.when.opensIn - b.when.opensIn || a.passed - b.passed);

  return { open: open.slice(0, limit), soon: soon.slice(0, limit), checked: scored.length, at: when };
}

module.exports = { brief, statusAt, windowFor, TZ };
