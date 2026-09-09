// Prepares the next batch of ready-to-send pitches. Works the existing
// backlog (clients already scaffolded with status "new") first, worst sites
// first, same ranking scout itself uses. Does NOT send anything — sending is
// a separate, deliberate step (see the campaign-day instructions), so a bug
// here produces a bad queue, never a bad send.
//
// Every candidate is checked against the suppression list twice: once before
// touching their site, and again after harvest may have discovered a new
// email/domain for them. Anyone with no discoverable contact email is
// skipped, not guessed at — an invented address either bounces or, worse,
// reaches the wrong person.

const fs = require('fs');
const path = require('path');
const suppress = require('./suppress');
const { findEmail } = require('./quicklook');
const render = require('./render');
const pitch = require('./pitch');

const ROOT = path.join(__dirname, '..');
const CLIENTS = path.join(ROOT, 'clients');
const pricing = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/pricing.json'), 'utf8'));

// Link, not attachment (2026-09-08 decision): a real inline attachment has
// to pass through as literal base64 text, which measured at 100K+ tokens per
// email — not sustainable at any real daily volume, and a single mistyped
// character corrupts the file. A link costs nothing and can't be corrupted
// in transit.
//
// That link is served by cloudflarePagesDomain in config/hosting.json.
// Cloudflare's Git integration works with a PRIVATE repo, and
// tools/publish.js builds a site/ folder containing ONLY rendered pages —
// no pricing, no suppression list, no other prospect's audit data. Point
// the build output directory at "site" (build command
// `node tools/publish.js`), never at the repo root.
//
// There is deliberately NO fallback. The old one served this repo's own
// committed HTML off a raw-file CDN, which only works while the repo is
// PUBLIC — and a public repo hands a stranger every other prospect's page,
// config/pricing.json, config/suppression.json and outreach/sent-log.jsonl
// along with it. A missing domain is a setup error worth stopping for, not
// something to paper over by quietly publishing the whole repo.
const hosting = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/hosting.json'), 'utf8'));
const liveUrlFor = (slug) => {
  if (!hosting.cloudflarePagesDomain) {
    throw new Error(
      'config/hosting.json has no cloudflarePagesDomain, so there is nowhere to\n' +
      'host the page this email links to. Set it to the domain serving site/\n' +
      '(see tools/publish.js) and run again.');
  }
  return `https://${hosting.cloudflarePagesDomain}/${slug}/`;
};

// A tagline is the <h1> when there is no headline, so it has to read as one:
// short, and about the business rather than about the domain it sits on.
const JUNK_TAGLINE = /domain|website builder|coming soon|under construction|lorem|godaddy|wix\.com|squarespace|for sale|parked|click here|default description/i;
const usableTagline = (t) => !!t && String(t).trim().length <= 90 && !JUNK_TAGLINE.test(t);

const loadClient = (slug) => JSON.parse(fs.readFileSync(path.join(CLIENTS, slug, 'business.json'), 'utf8'));
const saveClient = (slug, b) => fs.writeFileSync(path.join(CLIENTS, slug, 'business.json'), JSON.stringify(b, null, 2) + '\n');

function domainOf(url) {
  if (!url) return null;
  try { return new URL(/^https?:\/\//.test(url) ? url : 'https://' + url).hostname.replace(/^www\./, ''); }
  catch { return null; }
}

function suppressed(b) {
  return suppress.isSuppressed({ email: b.email, domain: domainOf(b.currentSite), phone: b.phone });
}

// What a page needs before it can be sent with nobody looking. The README
// has said it for months — "a page needs hours and reviews before it goes
// out" — and ./cc check flags both; on the autonomous path that has to be a
// stop, not a warning, because the ten sent on 8 Sep all lacked reviews.
// Every reason here is one ./cc research fills from Google or their own
// site, so "not sendable" means "research it", not "give up".
const PLACEHOLDER_HOURS_SIG = require('./render').PLACEHOLDER_HOURS_SIG;
function unsendable(b) {
  const why = [];
  const kind = b.siteKind;
  if (!kind) why.push('not researched yet — ./cc research fills siteKind, hours and reviews');
  else if (kind === 'challenge') why.push('their site sits behind a bot challenge — we never saw it, nothing to claim');
  else if (kind === 'notTheirs') why.push('the page at currentSite never names them — probably not their site');
  else if (kind === 'platform') why.push(`on a managed platform (${b.sitePlatform || 'Wix/Squarespace/Vagaro…'}) — someone is already paid to look after it`);
  else if (kind === 'unreachable') why.push('research could not reach their site — rerun research.yml on Actions before deciding anything');
  const hoursSig = (b.hours || []).map((h) => h.schema || '').filter(Boolean).join('|');
  const realHours = (b.hours || []).some((h) => h.time) && hoursSig !== PLACEHOLDER_HOURS_SIG;
  if (!realHours) why.push('no real hours');
  if (!(b.reviews || []).some((r) => r && r.text)) why.push('no real reviews');
  // Not populated automatically — research.js only points out a CSLB-shaped
  // number for a human to check by hand (see tools/research.js). If someone
  // records the answer here after checking, a bad one is worse than no claim.
  if (b.licenseCheck && /expired|revoked|suspended|inactive/i.test(b.licenseCheck.status)) {
    why.push(`license on file is ${b.licenseCheck.status} (${b.licenseCheck.source || 'checked by hand'}) — verify before pitching, do not send as-is`);
  }
  return why;
}

async function prepare({ need = 10, log = console.log } = {}) {
  const slugs = fs.existsSync(CLIENTS)
    ? fs.readdirSync(CLIENTS).filter((d) =>
        fs.existsSync(path.join(CLIENTS, d, 'business.json')) && !d.startsWith('example-'))
    : [];

  const candidates = slugs
    .map((slug) => ({ slug, b: loadClient(slug) }))
    .filter(({ b }) => b.status === 'new')
    .sort((x, y) => (y.b._scout?.score || 0) - (x.b._scout?.score || 0));

  const ready = [];
  const skipped = [];

  for (const { slug } of candidates) {
    if (ready.length >= need) break;
    let b = loadClient(slug);   // re-read: an earlier iteration in this same run may have changed nothing here, but this keeps the loop honest if the function is ever re-entered

    if (suppressed(b)) {
      b.status = 'dead'; saveClient(slug, b);
      skipped.push({ slug, why: 'suppressed' });
      continue;
    }

    // A hand-written pitchEmail means Tyler already wrote this one himself —
    // pitch.js's own comment calls it out: "a referral, someone who already
    // asked... templating around every case is worse than writing it." That
    // copy can reference things (a name, a prior call, an attachment) that
    // don't hold for a blind autonomous send. This lead stays Tyler's to send.
    if (b.pitchEmail) {
      skipped.push({ slug, why: 'has hand-written pitchEmail — warm lead, needs a human, not the autonomous queue' });
      continue;
    }

    // A raw-HTML scan cannot see JavaScript-rendered hours, phone links or
    // layout — pitch.js itself refuses to let those findings become claims in
    // front of an owner (see its "unverified" check). Same rule here: never
    // auto-send a pitch built on an audit that was not run in a real browser.
    if (b._scout && b._scout.rendered === false) {
      skipped.push({ slug, why: 'audit not browser-rendered — unsafe to claim findings, needs a human look' });
      continue;
    }

    const gaps = unsendable(b);
    if (gaps.length) { skipped.push({ slug, why: gaps.join('; ') }); continue; }

    if (!b.email && b.currentSite) {
      try {
        const found = await findEmail(b.currentSite, b.name);
        if (found) { b.email = found; saveClient(slug, b); }
      } catch (e) {
        skipped.push({ slug, why: 'contact lookup failed: ' + e.message.split('\n')[0] });
        continue;
      }
    }

    if (!b.email) { skipped.push({ slug, why: 'no contact email found on their site' }); continue; }

    if (suppressed(b)) {   // the harvest may just have surfaced a suppressed address/domain
      b.status = 'dead'; saveClient(slug, b);
      skipped.push({ slug, why: 'suppressed (found after harvest)' });
      continue;
    }

    // A meta description is not a headline. Scout puts the site's own
    // description in tagline; when that is a paragraph, or a parked domain's
    // "get a new domain name" blurb, it must not become the <h1>. The real,
    // merely long, ones are kept as `description` for the page's meta tags.
    if (!usableTagline(b.tagline)) {
      if (b.tagline && !JUNK_TAGLINE.test(b.tagline) && !b.description) b.description = b.tagline;
      const where = b.address?.city || 'San Diego';
      const what = (b.category || '').trim();
      // Sentence-case the category for the <h1>; a lowercase acronym would come out as "Hvac".
      const NOUN = { beauty: 'Beauty salon', 'fitness centre': 'Fitness center' };   // OSM tags that are not business nouns
      const shown = !what ? '' : NOUN[what.toLowerCase()] || (/^(hvac|ac|dds|dmd|cpa|llc|rv|atv|ev|it)$/i.test(what) ? what.toUpperCase() : what[0].toUpperCase() + what.slice(1));
      b.tagline = what ? `${shown} in ${where}.` : `Serving ${where}.`;
    }
    b.liveUrl = liveUrlFor(slug);   // pitch.js adds "you can also see it here: {liveUrl}" once this is set
    saveClient(slug, b);

    const html = render(b);
    fs.writeFileSync(path.join(CLIENTS, slug, 'index.html'), html);
    const p = pitch(b, pricing);
    fs.writeFileSync(path.join(CLIENTS, slug, 'pitch.md'), p.sheet);
    fs.writeFileSync(path.join(CLIENTS, slug, 'email.txt'), `Subject: ${p.subject}\n\n${p.body}\n`);

    ready.push({
      slug, to: b.email, name: b.name, subject: p.subject, body: p.body, link: b.liveUrl,
    });
    log(`  + ${slug} -> ${b.email}  (${b.liveUrl})`);
  }

  return { ready, skipped };
}

module.exports = { prepare, unsendable };

if (require.main === module) {
  const need = Number((process.argv.find((a) => a.startsWith('--need=')) || '--need=10').split('=')[1]) || 10;
  prepare({ need, log: (...a) => process.stderr.write(a.join(' ') + '\n') })
    .then((out) => { process.stdout.write(JSON.stringify(out, null, 2) + '\n'); })
    .catch((e) => { console.error('campaign prepare failed:', e); process.exit(1); });
}
