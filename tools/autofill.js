// The one piece of "fill in the sales copy" that's safe to automate:
// pulling a real contact email off the business's OWN site, found by
// harvest.js, into business.json. Nothing else — no invented reviews, no
// guessed hours, no assumed prices. Those stay soft/optional and simply
// don't appear on the page if nobody sat down and confirmed them, exactly
// like the 87 clients already in this repo that were built unharvested.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

// Directories, catch-alls and anything that is obviously not a person to
// write to. A pitch that lands in webmaster@ or noreply@ never gets read.
const BAD_LOCAL = /^(noreply|no-reply|donotreply|do-not-reply|webmaster|postmaster|abuse|privacy|legal|unsubscribe|mailer-daemon|test|example)$/i;
const BAD_DOMAIN = /wixpress\.com$|sentry\.io$|godaddy\.com$|schema\.org$|w3\.org$|example\.(com|org)$/i;
// "wcac_logo@2x.png" fits an email-shaped regex perfectly — @2x is a
// standard retina-image filename suffix, and "png" is 3 letters like a real
// TLD. Reject anything whose "domain" ends in a file extension rather than
// risk mailing an asset filename.
const FILE_EXT = /\.(png|jpe?g|gif|svg|webp|avif|ico|bmp|css|js|mjs|json|pdf|woff2?|ttf|eot|otf|mp4|webm|mov)$/i;

// A small local business very often runs its inbox on generic webmail
// rather than its own domain — real and common, trust it, but ONLY when the
// address itself reads as theirs. A generic-webmail address found on a page
// is otherwise no safer a guess than any other off-domain one: caught for
// real, "sudtipos@sudtipos.com" (a type foundry, not the cupcake shop it
// was found on) led straight to "impallari@gmail.com" (a font designer) the
// moment webmail alone was trusted — same wrong-recipient bug, new address.
const GENERIC_WEBMAIL = /^(gmail|yahoo|hotmail|outlook|icloud|aol|msn|live|proton(mail)?|mail)\.com$/i;
const GENERIC = new Set(['the', 'and', 'inc', 'llc', 'ltd', 'co', 'company', 'group', 'shop', 'store']);

// Does this local-part actually read as the business's own name? Same idea
// as browser-audit.js's namesBusiness() — a directory-scraped domain is
// wrong often enough that "found near their name" beats "found on their
// page" as a trust signal.
function localPartMatchesBusiness(localPart, businessName) {
  const flat = String(localPart || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const words = String(businessName || '').toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ').split(/\s+/)
    .filter((w) => w.length >= 3 && !GENERIC.has(w));
  if (!words.length || !flat) return false;
  return words.some((w) => flat.includes(w)) || flat.length >= 4 && businessName && String(businessName).toLowerCase().replace(/[^a-z0-9]/g, '').includes(flat);
}

function bestEmail(emails, businessDomain, businessName) {
  const clean = (emails || [])
    .map((e) => String(e).trim().toLowerCase())
    .filter((e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e))
    .filter((e) => !BAD_LOCAL.test(e.split('@')[0]))
    .filter((e) => !BAD_DOMAIN.test(e.split('@')[1] || ''))
    .filter((e) => !FILE_EXT.test(e));
  if (!clean.length) return null;

  const onDomain = businessDomain && clean.find((e) => e.endsWith('@' + businessDomain));
  if (onDomain) return onDomain;
  // No match on their own domain: only trust a generic-webmail address
  // whose local-part actually reads as this business's name. Anything else
  // found on the page is more likely to belong to whoever built or hosts
  // the site than to the business itself — skip rather than guess.
  return clean.find((e) => {
    const [local, domain] = e.split('@');
    return GENERIC_WEBMAIL.test(domain || '') && localPartMatchesBusiness(local, businessName);
  }) || null;
}

// Applies harvest.json -> business.json for one client. Returns what changed
// so a caller can decide whether this lead is even contactable.
function applyHarvest(slug) {
  const dir = path.join(ROOT, 'clients', slug);
  const bFile = path.join(dir, 'business.json');
  const hFile = path.join(dir, 'harvest.json');
  if (!fs.existsSync(bFile)) throw new Error(`no such client: ${slug}`);
  const b = JSON.parse(fs.readFileSync(bFile, 'utf8'));
  if (!fs.existsSync(hFile)) return { slug, gotEmail: Boolean(b.email), email: b.email || null };

  const h = JSON.parse(fs.readFileSync(hFile, 'utf8'));
  let changed = false;

  if (!b.email) {
    const domain = (() => {
      try { return new URL(/^https?:\/\//.test(h.from) ? h.from : 'https://' + h.from).hostname.replace(/^www\./, ''); }
      catch { return null; }
    })();
    const found = bestEmail(h.emails, domain);
    if (found) { b.email = found; changed = true; }
  }

  if (changed) fs.writeFileSync(bFile, JSON.stringify(b, null, 2) + '\n');
  return { slug, gotEmail: Boolean(b.email), email: b.email || null };
}

module.exports = { applyHarvest, bestEmail };
