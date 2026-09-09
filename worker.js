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

const COOKIE = 'dash';

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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!/^\/dash(\/|$)/.test(url.pathname)) return env.ASSETS.fetch(request);

    const expected = env.DASH_KEY || '';
    const fromQuery = url.searchParams.get('key') || '';
    const given = fromQuery || cookieValue(request, COOKIE);
    if (!expected || !sameSecret(given, expected)) return notFound();

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
