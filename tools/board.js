// Builds the call board: every business we know about, in one page, ranked.
//
// This is a *calling* tool, not a report. Every row has to answer three
// questions in the second before Tyler taps a number: who are they, what is
// the one thing I can say out loud, and is this actually worth a call.
//
// The honesty rules from CALL.md are enforced here rather than trusted to
// whoever reads the page:
//
//   - Only the seven hard checks can ever be shown as a claim. The five soft
//     ones (hours, address, services, reviews, cta) are recorded but marked
//     unclaimable, because a page scan cannot prove them — we once told a
//     florist she had no hours while she was looking at her hours.
//   - A lead whose page never names the business is flagged OPEN THIS FIRST.
//     Six wrong URLs in one week all failed that way.
//   - No email is ever constructed. If business.json has no address, the row
//     says "call for it" and offers no mailto.
//   - A load time is only printed when it was measured; "very slow" otherwise.

const fs = require('fs');
const path = require('path');
const checks = require('./checks');
const stateFromPhone = require('./area-codes');

const ROOT = path.join(__dirname, '..');
const HARD = checks.filter((c) => !c.soft);
const SOFT = checks.filter((c) => c.soft);
const HARD_KEYS = HARD.map((c) => c.key);

// What to say out loud, worst first. The order is sales order, not severity:
// the top of this list is what makes an owner go "wait, really?" on the phone.
const FLAW = [
  ['mobile',   'Breaks on a phone',            'Pull it up on your own phone — that is what your customers see.'],
  ['https',    'Not secure — no HTTPS',        'Chrome shows visitors a "Not secure" warning before they read a word.'],
  ['speed',    'Very slow to load',            'Someone with an emergency does not wait. They tap the next name down.'],
  ['phoneTap', 'Number is not tappable',       'On a phone your number is text, not a button. They have to memorise it.'],
  ['social',   'No preview when shared',       'Text your link to someone and it arrives as a bare grey box.'],
  ['meta',     'No title or description',      'Google is guessing what to print under your name in the results.'],
  ['seo',      'No Google business markup',    'Google has nothing structured to read, so your listing is thinner than it should be.'],
];

// Domain marketplaces and the default parking path. A parked domain is not a
// website with faults — it is a business with no website, whose name is being
// sold back to them. Reporting "breaks on a phone" about a for-sale page is the
// same error as judging a CAPTCHA, and it throws away the strongest pitch we
// have.
const PARKED_HOST = /(^|\.)(hugedomains|afternic|sedo|dan|domainmarket|buydomains|undeveloped)\.com$/i;

function parkedOf(row) {
  const u = row.site || '';
  if (!u) return null;
  let host = '', pathname = '';
  try { const x = new URL(u); host = x.hostname; pathname = x.pathname; } catch { return null; }
  if (PARKED_HOST.test(host)) return 'the domain is for sale on a marketplace';
  if (/^\/lander\/?$/i.test(pathname)) return 'the domain sits on a registrar placeholder';
  if (/domain_profile|domain-for-sale/i.test(u)) return 'the domain is for sale on a marketplace';
  // Deliberately not read from callNotes or _status: those describe the lead,
  // not this URL. RT Roofing's notes say a *different* domain of his is parked,
  // and matching them labelled his working site a placeholder.
  return null;
}

// Bot-challenge interstitials answer 200 and render like a page, so every
// check runs against the challenge instead of the site. Judging one means
// telling a plumber his phone number is untappable when what we measured was
// a CAPTCHA.
const CHALLENGE = /\/\.well-known\/sgcaptcha|cdn-cgi\/challenge|__cf_chl|incapsula|distil_r_captcha|_Incapsula_Resource/i;

// Institutions have no owner who can buy a website: a campus clinic answers to
// a university, a city facility to a council. Their .edu and .gov domains are
// the reliable tell.
const INSTITUTION = /(^|\.)(edu|gov|mil)$|\b(university|college|campus|school district|municipal|county of|city of)\b/i;

// A failed navigation leaves the browser's own error page in finalUrl.
// chrome-error://chromewebdata is not a website, and every check run against
// it describes Chrome.
const NOT_A_PAGE = /^(chrome-error|about|data|chrome|edge):/i;

// Generic words shared by half the businesses in any town. A domain matching
// only on these tells us nothing about whether the site is theirs.
const GENERIC = new Set(['salon','hair','dental','dentist','group','center','centre','clinic','studio',
  'services','service','company','shop','store','plumbing','roofing','bakery','beauty','nail','nails',
  'spa','care','health','auto','repair','insurance','law','yoga','fitness','design','designs','inc','llc',
  'the','and','san','diego','wilmington','dover','california','delaware']);

// Does the domain look like it belongs to this business? A weak signal, so it
// raises a "check this" flag rather than dropping the lead — but six wrong
// URLs in one week is a rate worth catching before the call, not during it.
function domainLooksUnrelated(name, site) {
  if (!name || !site) return false;
  let sld = '';
  try {
    sld = new URL(site).hostname.replace(/^www\./, '').split('.').slice(0, -1).join('');
  } catch { return false; }
  if (!sld) return false;
  const tokens = name.toLowerCase().match(/[a-z]{4,}/g) || [];
  const real = tokens.filter((t) => !GENERIC.has(t));
  if (!real.length) return false;                 // nothing distinctive to match on
  return !real.some((t) => sld.includes(t) || t.includes(sld));
}

// OSM writes numbers six different ways. One shape reads faster on a phone.
function prettyPhone(s) {
  const d = String(s || '').replace(/[^0-9]/g, '').replace(/^1(?=\d{10}$)/, '');
  return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : (s || '');
}

const digits = (s) => String(s || '').replace(/[^0-9]/g, '');
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// A number nobody local answers. A call centre cannot buy a website.
const TOLL_FREE = /^1?8(00|33|44|55|66|77|88)/;

function scoreOf(audit) {
  const passed = HARD_KEYS.filter((k) => audit && audit[k] === true).length;
  return { passed, of: HARD_KEYS.length };
}

function biggestFlaw(audit, parked) {
  if (parked) {
    return {
      key: 'parked',
      label: 'No real website — ' + parked,
      why: 'Anyone who Googles you lands on a page selling your own name back to you.',
    };
  }
  for (const [key, label, why] of FLAW) {
    if (audit && audit[key] === false) return { key, label, why };
  }
  return null;
}

// Everything that would make a call a waste of his time, said plainly.
function disqualify(r) {
  const notes = (r.notes || []).join(' ') + ' ' + (r.statusNote || '');
  if (r.status === 'dead') return 'closed out';
  if (CHALLENGE.test(r.site || '')) return 'behind a bot check — we measured a CAPTCHA, not their site';
  if (NOT_A_PAGE.test(r.site || '')) return 'the page never loaded — we measured a browser error';
  let siteHost = '';
  try { siteHost = new URL(r.site).hostname; } catch { /* no usable URL */ }
  if (INSTITUTION.test(r.name || '')) return 'an institution, not an owner-run business';
  // A barber shop listed against bcb.az.gov is not a government body; the
  // directory simply gave us somebody else's domain.
  if (INSTITUTION.test(siteHost)) return 'the listed domain belongs to a school or government body';
  if (/Doctible|WEO Media|Vagaro|Booksy|Squarespace|Wix|Shopify|managed platform|agency/i.test(notes))
    return 'has an agency';
  if (r.phone && TOLL_FREE.test(digits(r.phone))) return 'toll-free — call centre';
  if (r.namesBusiness === false) return 'URL may not be theirs';
  if (r.attempts >= 4) return `${r.attempts} attempts — past the four-strike rule`;
  // No number and no address is not a lead, it is a name. The listing has to
  // carry a way to reach them, because we do not invent one.
  if (!r.phone && !r.email) return 'no number in the listing — Google them to recover it';
  return null;
}

function fromClients() {
  const out = [];
  const dir = path.join(ROOT, 'clients');
  if (!fs.existsSync(dir)) return out;

  for (const slug of fs.readdirSync(dir).sort()) {
    const f = path.join(dir, slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    if (slug.startsWith('example-')) continue;
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }
    const sc = b._scout || {};

    out.push({
      source: 'pipeline',
      slug,
      name: b.name || slug,
      category: b.category || '',
      city: (b.address && b.address.city) || '',
      state: (b.address && b.address.state) || '',
      phone: b.phone || '',
      email: b.email || '',
      site: b.currentSite || '',
      status: b.status || 'new',
      statusNote: b._status || '',
      owner: b.owner || '',
      audit: b.audit || {},
      // Findings read off raw HTML are not safe to put in front of an owner;
      // only a real browser run counts.
      rendered: sc.rendered === true,
      namesBusiness: sc.namesBusiness,
      loadMs: sc.loadMs || null,
      attempts: (b.callNotes || []).length,
      notes: b.callNotes || [],
      built: fs.existsSync(path.join(dir, slug, 'index.html')),
    });
  }
  return out;
}

function fromLeads() {
  const out = [];
  const dir = path.join(ROOT, 'leads');
  if (!fs.existsSync(dir)) return out;

  for (const region of fs.readdirSync(dir)) {
    const f = path.join(dir, region, 'leads.json');
    if (!fs.existsSync(f)) continue;
    let list;
    try { list = JSON.parse(fs.readFileSync(f, 'utf8')); } catch { continue; }

    for (const l of list) {
      const a = l.auditResult || {};
      // Test fixtures and anything we could not actually reach are not leads.
      if (/localhost|127\.0\.0\.1|example\.com/i.test(l.website || '')) continue;
      out.push({
        source: region,
        slug: l.slug || '',
        name: l.name || '',
        category: l.category || '',
        city: (l.address && l.address.city) || '',
        state: (l.address && l.address.state) || '',
        phone: l.phone || '',
        email: '',                       // OSM has none, and we never invent one
        site: a.finalUrl || l.website || '',
        status: 'new',
        statusNote: '',
        owner: '',
        audit: a.checks || {},
        rendered: a.rendered === true,
        namesBusiness: a.verified === false ? false : (a.verified === true ? true : undefined),
        loadMs: a.ms || null,
        attempts: 0,
        notes: [],
        built: false,
        reachable: a.reachable,
        reason: a.reason || '',
      });
    }
  }
  return out;
}

function build() {
  const seen = new Set();
  const rows = [];

  // The pipeline wins any tie: it carries call notes and a corrected URL.
  for (const r of [...fromClients(), ...fromLeads()]) {
    // OSM writes "+1-619-466-6854" and the pipeline writes "(619) 466-6854".
    // Same business, and without dropping the country code it was listed twice.
    const tel = digits(r.phone).replace(/^1(?=\d{10}$)/, '');
    const host = (r.site || '').replace(/^https?:\/\/(www\.)?/, '').replace(/\/.*$/, '');
    const key = tel || host || r.name.toLowerCase().replace(/[^a-z0-9]/g, '');
    // A business listed twice under two numbers is still one phone call.
    const byName = r.name.toLowerCase().replace(/[^a-z0-9]/g, '') + '@' + (r.city || '').toLowerCase();
    if (!key || seen.has(key) || seen.has(byName) || (host && seen.has(host))) continue;
    seen.add(key);
    seen.add(byName);
    if (host) seen.add(host);

    // A national list without a state is not usable; the area code is on the
    // number he is about to dial. Marked derived so it is never mistaken for
    // something the listing said.
    const derivedState = !r.state ? stateFromPhone(r.phone) : '';
    const sc = scoreOf(r.audit);
    const parked = parkedOf(r);
    const flaw = biggestFlaw(r.audit, parked);
    rows.push({
      ...r,
      phone: prettyPhone(r.phone),
      state: r.state || derivedState,
      stateDerived: Boolean(derivedState),
      parked,
      passed: parked ? 0 : sc.passed,   // a placeholder passes nothing on their behalf
      of: sc.of,
      flaw,
      checkUrl: r.namesBusiness === false || domainLooksUnrelated(r.name, r.site),
      softMissing: SOFT.filter((c) => r.audit && r.audit[c.key] === false).map((c) => c.label),
      blocked: disqualify(r),
    });
  }

  // Callable first, then most broken, then whether we can actually measure it.
  rows.sort((a, b) =>
    (a.blocked ? 1 : 0) - (b.blocked ? 1 : 0) ||
    (b.rendered ? 1 : 0) - (a.rendered ? 1 : 0) ||
    (a.passed - b.passed) ||
    (b.phone ? 1 : 0) - (a.phone ? 1 : 0));

  return rows;
}

module.exports = { build, HARD, SOFT, FLAW, esc, digits, prettyPhone, parkedOf, domainLooksUnrelated };
