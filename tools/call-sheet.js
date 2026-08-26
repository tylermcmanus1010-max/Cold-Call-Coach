// Builds the call sheet from clients/*/business.json.
//
// The sheet used to be hand-assembled, which meant every change was a rewrite
// and the only copy lived in a scratch folder. Now clients/ is the single
// source of truth: ./cc tried, ./cc sent and ./cc status all write there, the
// dashboard writes back there too, and this file turns that into the page.
//
// The page is a quine — it carries its own source so it can republish itself
// when you tap a button. tools/sheet-shell.html is that source with the state
// blob swapped for a placeholder.

const fs = require('fs');
const path = require('path');
const pitch = require('./pitch');

const ROOT = path.join(__dirname, '..');
const SHELL = path.join(__dirname, 'sheet-shell.html');
const pricing = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/pricing.json'), 'utf8'));

// What we ask him to screenshot off a Google listing, per gap. These are the
// soft checks — the ones a page scan can never prove, so only the owner or
// their listing can fill them in.
const NEEDS = {
  hours: 'hours',
  address: 'address',
  reviews: 'review count and rating',
  services: 'service list',
};

const digits = (s) => String(s || '').replace(/[^0-9]/g, '');

// The opener is the whole call. It has to name the town, ask the franchise
// question before anything else, and promise nothing is owed.
function phoneScript(b) {
  if (b.callScript) return b.callScript;
  const town = b.address?.city || 'San Diego';
  const trade = (b.category || 'business').toLowerCase();
  const noSite = !b.currentSite;
  const problem = noSite
    ? "I went looking for your website and couldn't find one."
    : 'I had a look at your website on my phone.';
  return `Hi, my name's Tyler — I build websites for businesses here in ${town}. `
    + 'Quick question first, are you independent or part of a franchise? … '
    + `${problem} I'm not selling you anything on the phone. I build one free sample site a week `
    + `for a local ${trade}, and I did yours. Can I email it so you can look at it on your phone? `
    + 'Nothing owed either way.';
}

function leadFor(slug, b) {
  const out = pitch(b, pricing);
  const built = fs.existsSync(path.join(ROOT, 'clients', slug, 'index.html'));

  // Only ask for what the page is actually missing, and only for things a
  // screenshot can answer.
  const needs = [];
  if (!(b.hours && b.hours.length)) needs.push(NEEDS.hours);
  if (!(b.address && b.address.street)) needs.push(NEEDS.address);
  if (!(b.reviews && b.reviews.count)) needs.push(NEEDS.reviews);
  if (!(b.services && b.services.length)) needs.push(NEEDS.services);

  const q = encodeURIComponent(`${b.name} ${b.address?.city || 'San Diego'} CA`);

  return {
    slug,
    name: b.name || slug,
    phone: b.phone || '',
    city: b.address?.city || '',
    cat: b.category || '',
    site: b.currentSite || '',
    status: b.status || 'new',
    attempts: b.attempts || 0,
    lastTried: b.lastTried || '',
    sentOn: b.sentOn || '',
    built,
    file: `${slug}.html`,
    script: phoneScript(b),
    subject: out.subject || '',
    body: out.body || '',
    needs,
    note: (b.callNotes || []).slice(-1)[0] || '',
    maps: `https://www.google.com/search?q=${q}`,
  };
}

function buildState() {
  const dir = path.join(ROOT, 'clients');
  const leads = [];
  const skipped = [];

  for (const slug of fs.readdirSync(dir).sort()) {
    const f = path.join(dir, slug, 'business.json');
    if (!fs.existsSync(f)) continue;
    let b;
    try { b = JSON.parse(fs.readFileSync(f, 'utf8')); }
    catch (e) { skipped.push(`${slug} (unreadable business.json)`); continue; }

    // A lead with no phone number is not a call. Keep it visible only if it is
    // already in flight, so nothing silently disappears off the sheet.
    if (!digits(b.phone) && (b.status || 'new') === 'new') { skipped.push(`${slug} (no phone)`); continue; }

    try { leads.push(leadFor(slug, b)); }
    catch (e) { skipped.push(`${slug} (${e.message})`); }
  }

  return { state: { leads, updated: new Date().toISOString().slice(0, 10) }, skipped };
}

function build() {
  const { state, skipped } = buildState();
  const shell = fs.readFileSync(SHELL, 'utf8');
  if (!shell.includes('__STATE__')) throw new Error('sheet-shell.html has lost its __STATE__ placeholder');

  // </script> inside a string would close the block the state sits in.
  const json = JSON.stringify(state).replace(/<\//g, '<\\/');
  const html = shell.replace('__STATE__', json);

  // The sheet is a quine: if its script will not parse, the page renders blank
  // and takes his whole call list with it. Same guard the site builder uses.
  for (const [, attrs, js] of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (/^\s*$/.test(js)) continue;
    const type = (attrs.match(/type\s*=\s*["']([^"']+)/i) || [])[1];
    if (type && !/javascript|module/i.test(type)) continue;
    try { new Function(js); }
    catch (e) { throw new Error(`call sheet script will not parse — ${e.message}`); }
  }

  return { html, state, skipped };
}

module.exports = build;
module.exports.buildState = buildState;
