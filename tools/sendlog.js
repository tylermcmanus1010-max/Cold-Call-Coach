// One line per pitch actually sent. This is how the daily reply-check knows
// which Gmail threads to look at, and how the campaign knows today's count
// against the daily cap — counted from this log, not from client status,
// because status can be edited by hand without it meaning "sent today."

const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'outreach', 'sent-log.jsonl');

function append(row) {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.appendFileSync(FILE, JSON.stringify({ at: new Date().toISOString(), ...row }) + '\n');
}

function all() {
  if (!fs.existsSync(FILE)) return [];
  return fs.readFileSync(FILE, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}

function sentToday() {
  const today = new Date().toISOString().slice(0, 10);
  return all().filter((r) => r.at.slice(0, 10) === today);
}

// Sent rows we haven't yet resolved with a reply/opt-out/no-reply outcome —
// what the daily reply check needs to look at.
function openThreads() {
  return all().filter((r) => !r.resolved);
}

function markResolved(threadId, outcome) {
  const rows = all();
  const out = rows.map((r) => (r.threadId === threadId ? { ...r, resolved: true, outcome } : r));
  fs.writeFileSync(FILE, out.map((r) => JSON.stringify(r)).join('\n') + (out.length ? '\n' : ''));
}

module.exports = { append, all, sentToday, openThreads, markResolved };
