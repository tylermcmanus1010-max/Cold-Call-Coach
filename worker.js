// The only code in front of site/. Everything under /dash/ is the morning
// dashboard — every prospect, their numbers, what we said to them — and it
// is served only to a request carrying DASH_KEY. Nothing else is touched:
// wrangler.toml runs this script first for /dash paths alone, so a pitch
// page is served straight from the asset layer exactly as before, and a bug
// here cannot take a pitch link down with it.
//
// Set the key once, in the Worker's settings (Variables and Secrets →
// DASH_KEY), or `npx wrangler secret put DASH_KEY`. Open
// https://<domain>/dash/?key=<the key> once on the phone; the cookie keeps
// it open after that. No key configured means /dash/ is a 404, not a page.
//
// POST /dash/log is the tap-to-log endpoint: a caller taps "No answer" or
// "Sent" on a card and this writes straight to clients/<slug>/business.json
// in the repo through the GitHub API, so it is real the moment they tap it —
// not tomorrow's rebuild. It needs a second secret, GH_TOKEN: a
// fine-grained personal access token scoped to ONLY this repo, with
// Contents: Read and write and nothing else — `npx wrangler secret put
// GH_TOKEN`, or set it in the Worker's Variables and Secrets. Without it,
// /dash/ still works for reading; logging just answers "off" until it is
// set.

const COOKIE = 'dash';
const REPO = 'tylermcmanus1010-max/Cold-Call-Coach';
const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{0,80})$/;
const ACTIONS = new Set(['tried', 'sent', 'replied', 'won', 'dead', 'note', 'callback']);

function cookieValue(request, name) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return decodeURIComponent(v.join('='));
  }
  return '';
}

function sameSecret(given, expected) {
  const a = new TextEncoder().encode(given);
  const b = new TextEncoder().encode(expected);
  if (a.length !== b.length || !a.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

const notFound = () => new Response('Not found', {
  status: 404,
  headers: { 'content-type': 'text/plain', 'cache-control': 'no-store' },
});

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
});

// Workers' btoa/atob are byte-string only; a name or note with a curly quote
// or an emoji in it is not Latin-1, so it has to go through UTF-8 bytes by
// hand or the round trip corrupts it.
function b64encode(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
function b64decode(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

async function ghFetch(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'cold-call-coach-dashboard',
      'x-github-api-version': '2022-11-28',
      ...(init.headers || {}),
    },
  });
}

// Same fields ./cc tried and ./cc status write, same shapes board.js and
// campaign.js already read — a tap here has to mean the same thing a
// terminal command means, or the two disagree the next time someone looks.
async function handleLog(request, env) {
  if (!env.GH_TOKEN) return json({ ok: false, error: 'call logging is not set up yet (no GH_TOKEN) — ask Tyler' }, 501);

  let body;
  try { body = await request.json(); } catch { return json({ ok: false, error: 'bad request' }, 400); }

  const slug = String(body.slug || '');
  const action = String(body.action || '');
  const note = String(body.note || '').trim().slice(0, 500);
  const at = String(body.at || '').trim().slice(0, 40);

  if (!SLUG_RE.test(slug)) return json({ ok: false, error: 'bad slug' }, 400);
  if (!ACTIONS.has(action)) return json({ ok: false, error: 'unknown action' }, 400);
  if (action === 'note' && !note) return json({ ok: false, error: 'note text is empty' }, 400);
  if (action === 'callback' && !at) return json({ ok: false, error: 'callback time is empty' }, 400);

  const branch = env.GITHUB_BRANCH || 'main';
  const path = `clients/${slug}/business.json`;
  const today = new Date().toISOString().slice(0, 10);

  // A second caller tapping the same second loses the race on GitHub's sha
  // check, not silently — refetch and reapply rather than clobber their write.
  for (let attempt = 0; attempt < 3; attempt++) {
    const getRes = await ghFetch(env, `/contents/${encodeURIComponent(path).replace(/%2F/g, '/')}?ref=${branch}`);
    if (getRes.status === 404) return json({ ok: false, error: `no such client "${slug}"` }, 404);
    if (!getRes.ok) return json({ ok: false, error: `GitHub read failed (${getRes.status})` }, 502);
    const file = await getRes.json();

    let b;
    try { b = JSON.parse(b64decode(file.content)); }
    catch { return json({ ok: false, error: `${slug}/business.json is not valid JSON` }, 500); }

    const notes = Array.isArray(b.callNotes) ? b.callNotes.slice() : [];
    const stamp = (text) => notes.push(`${today}: ${text}`);

    if (action === 'tried') { b.attempts = (b.attempts || 0) + 1; b.lastTried = today; if (note) stamp(note); }
    else if (action === 'sent') { b.status = 'sent'; b.sentOn = today; if (note) stamp(note); }
    else if (action === 'replied') { b.status = 'replied'; if (note) stamp(note); }
    else if (action === 'won') { b.status = 'won'; if (note) stamp(note); }
    else if (action === 'dead') { b.status = 'dead'; if (note) stamp(note); }
    else if (action === 'note') { stamp(note); }
    else if (action === 'callback') { b.callbackAt = at; if (note) stamp(note); }
    b.callNotes = notes;

    const putRes = await ghFetch(env, `/contents/${path}`, {
      method: 'PUT',
      body: JSON.stringify({
        message: `Call log: ${slug} — ${action}`,
        content: b64encode(JSON.stringify(b, null, 2) + '\n'),
        sha: file.sha,
        branch,
        committer: { name: 'Cold Call Coach dashboard', email: 'dashboard@mcmanuswebco.invalid' },
      }),
    });

    if (putRes.ok) {
      return json({
        ok: true,
        patch: {
          status: b.status, attempts: b.attempts || 0, lastTried: b.lastTried || '',
          sentOn: b.sentOn || '', callbackAt: b.callbackAt || '', lastNote: notes[notes.length - 1] || '',
        },
      });
    }
    if (putRes.status === 409 && attempt < 2) continue;
    return json({ ok: false, error: `GitHub write failed (${putRes.status})` }, 502);
  }
  return json({ ok: false, error: 'too many conflicting writes at once — try again' }, 409);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!/^\/dash(\/|$)/.test(url.pathname)) return env.ASSETS.fetch(request);

    const expected = env.DASH_KEY || '';
    const fromQuery = url.searchParams.get('key') || '';
    const given = fromQuery || cookieValue(request, COOKIE);
    if (!expected || !sameSecret(given, expected)) return notFound();

    if (request.method === 'POST' && url.pathname === '/dash/log') return handleLog(request, env);

    // Serve the asset without the key in the URL, so it never lands in a
    // referrer, a screenshot, or a share sheet.
    url.searchParams.delete('key');
    const res = await env.ASSETS.fetch(new Request(url.toString(), request));
    const headers = new Headers(res.headers);
    headers.set('cache-control', 'private, no-store');
    headers.set('x-robots-tag', 'noindex, nofollow');
    if (fromQuery) {
      headers.append('set-cookie',
        `${COOKIE}=${encodeURIComponent(expected)}; Path=/dash; HttpOnly; Secure; SameSite=Lax; Max-Age=31536000`);
    }
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
  },
};
