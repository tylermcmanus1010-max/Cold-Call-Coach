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
// in transit. jsdelivr's raw-file CDN (fronted by githack, no setup, no
// auth) serves this repo's own committed HTML with the right content-type,
// so the built page opens and renders exactly like an attachment would.
// This repo is PUBLIC, so the same link pattern would let anyone enumerate
// every other prospect's pitch page, plus config/pricing.json and
// config/suppression.json — flagged to the user, not yet resolved.
const REPO_OWNER = 'tylermcmanus1010-max';
const REPO_NAME = 'Cold-Call-Coach';
const REPO_BRANCH = 'claude/zen-johnson-yw623l';
const liveUrlFor = (slug) =>
  `https://rawcdn.githack.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/clients/${slug}/index.html`;

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

    if (!b.email && b.currentSite) {
      try {
        const found = await findEmail(b.currentSite);
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

    if (!b.tagline) {
      const where = b.address?.city || 'San Diego';
      const what = (b.category || '').trim();
      b.tagline = what ? `${what} in ${where}.` : `Serving ${where}.`;
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

module.exports = { prepare };

if (require.main === module) {
  const need = Number((process.argv.find((a) => a.startsWith('--need=')) || '--need=10').split('=')[1]) || 10;
  prepare({ need, log: (...a) => process.stderr.write(a.join(' ') + '\n') })
    .then((out) => { process.stdout.write(JSON.stringify(out, null, 2) + '\n'); })
    .catch((e) => { console.error('campaign prepare failed:', e); process.exit(1); });
}
