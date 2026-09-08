// A fast, bounded stand-in for tools/harvest.js when all that's needed is a
// contact email. harvest.js is the right tool when a human is about to write
// sales copy — it launches a real browser twice and reads up to 9 pages,
// which is thorough but takes minutes per site. At 50 leads/day that does
// not fit in a working session. This does two plain HTTP fetches (homepage,
// then /contact if the homepage has nothing) with short timeouts, and reads
// mailto: links and email-shaped text out of the raw HTML. It will miss an
// email that only exists behind JavaScript — that lead just doesn't get an
// autofilled address, and falls to "no contact email found," same as if
// harvest.js had failed. It never guesses; it only reads what is on the page.

const { bestEmail } = require('./autofill');

const TIMEOUT = 8000;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

async function fetchText(url) {
  const res = await fetch(url, {
    signal: AbortSignal.timeout(TIMEOUT),
    redirect: 'follow',
    headers: { 'user-agent': UA, accept: 'text/html,*/*' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('content-type') || '';
  if (!/html/i.test(ct) && ct) throw new Error(`not html (${ct})`);
  return res.text();
}

function emailsIn(html) {
  const mailto = [...html.matchAll(/href\s*=\s*["']mailto:([^"'?]+)/gi)].map((m) => m[1]);
  const loose = html.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) || [];
  return [...mailto, ...loose];
}

async function findEmail(rawUrl, businessName) {
  const start = /^https?:\/\//i.test(rawUrl) ? rawUrl : 'https://' + rawUrl;
  let domain;
  try { domain = new URL(start).hostname.replace(/^www\./, ''); } catch { return null; }

  const tried = [];
  for (const path of ['', '/contact', '/contact-us'] ) {
    const url = start.replace(/\/+$/, '') + path;
    if (tried.includes(url)) continue;
    tried.push(url);
    try {
      const html = await fetchText(url);
      const found = bestEmail(emailsIn(html), domain, businessName);
      if (found) return found;
    } catch { /* try the next path */ }
  }
  return null;
}

module.exports = { findEmail };
