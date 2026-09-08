// The do-not-contact list. Checked before every autonomous send, no exceptions.
//
// A business that says stop, threatens to escalate, or bounces hard goes on
// this list once and stays there — across every campaign, every area code,
// forever. Losing a lead by skipping it costs nothing. Emailing someone who
// told us to stop costs the whole operation.

const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'config', 'suppression.json');

function load() {
  try { return JSON.parse(fs.readFileSync(FILE, 'utf8')); }
  catch { return { entries: [] }; }
}

function save(data) {
  fs.writeFileSync(FILE, JSON.stringify(data, null, 2) + '\n');
}

const norm = (s) => String(s || '').trim().toLowerCase();
const domainOf = (email) => norm(email).split('@')[1] || '';
const digitsOf = (s) => String(s || '').replace(/[^\d]/g, '').replace(/^1/, '');

// True if ANY of email / site domain / phone matches a suppressed entry.
// Domain match catches "they gave a different address at the same company."
function isSuppressed({ email, domain, phone } = {}) {
  const data = load();
  const e = norm(email), d = norm(domain) || domainOf(email), p = digitsOf(phone);
  return data.entries.some((row) => {
    if (e && row.email && norm(row.email) === e) return true;
    if (d && row.domain && norm(row.domain) === d) return true;
    if (p && row.phone && digitsOf(row.phone) === p && p.length >= 10) return true;
    return false;
  });
}

function add({ email, domain, phone, reason, source, slug }) {
  const data = load();
  const e = norm(email), d = norm(domain) || domainOf(email);
  if (isSuppressed({ email, domain, phone })) return false;   // already on it
  data.entries.push({
    email: e || undefined, domain: d || undefined, phone: phone || undefined,
    slug: slug || undefined, reason: reason || 'opted out', source: source || 'unknown',
    at: new Date().toISOString().slice(0, 10),
  });
  save(data);
  return true;
}

function list() { return load().entries; }

module.exports = { isSuppressed, add, list };
