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

function bestEmail(emails, businessDomain) {
  const clean = (emails || [])
    .map((e) => String(e).trim().toLowerCase())
    .filter((e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e))
    .filter((e) => !BAD_LOCAL.test(e.split('@')[0]))
    .filter((e) => !BAD_DOMAIN.test(e.split('@')[1] || ''))
    .filter((e) => !FILE_EXT.test(e));
  if (!clean.length) return null;
  // An address on their own domain is a real inbox someone at the business
  // reads; a gmail/yahoo catch-all scraped off a page is worth less but
  // still better than nothing.
  const onDomain = businessDomain && clean.find((e) => e.endsWith('@' + businessDomain));
  return onDomain || clean[0];
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
