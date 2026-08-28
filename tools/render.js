// Renders business.json -> one self-contained index.html.
// No build step, no dependencies, no external requests: the file works
// from a double-click, an email attachment, or any host.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const digits = (s) => String(s || '').replace(/[^\d+]/g, '');

function mapsUrl(a) {
  if (!a) return '';
  const q = [a.street, a.city, a.state, a.zip].filter(Boolean).join(', ');
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(q);
}

function addressLine(a) {
  if (!a) return '';
  return [a.street, [a.city, a.state].filter(Boolean).join(', '), a.zip].filter(Boolean).join(' · ');
}

function jsonld(b) {
  const a = b.address || {};
  const data = {
    '@context': 'https://schema.org',
    '@type': b.schemaType || 'LocalBusiness',
    name: b.name,
    description: b.tagline,
    telephone: b.phone,
    url: b.liveUrl || b.newUrl || undefined,
    address: a.street ? {
      '@type': 'PostalAddress',
      streetAddress: a.street, addressLocality: a.city,
      addressRegion: a.state, postalCode: a.zip, addressCountry: 'US',
    } : undefined,
    areaServed: (b.serviceArea || []).map((n) => ({ '@type': 'Place', name: n })),
    openingHours: (b.hours || []).map((h) => h.schema).filter(Boolean),
    priceRange: b.priceRange || undefined,
    aggregateRating: b.rating ? {
      '@type': 'AggregateRating',
      ratingValue: String(b.rating.value),
      reviewCount: String(b.rating.count),
    } : undefined,
  };
  // JSON-LD sits in a <script> block: escaping "<" as \u003c keeps the JSON
  // valid while making it impossible to open or close a tag from business data.
  return JSON.stringify(data, (k, v) => (v === undefined ? undefined : v), 2)
    .replace(/</g, '\\u003c');
}

function stars(n) {
  const full = Math.round(Number(n) || 0);
  return '<span class="stars" aria-label="' + esc(n) + ' out of 5">' +
    '★★★★★'.slice(0, full).padEnd(5, '☆') + '</span>';
}

// A barbershop should not read like an endodontist. Each trade gets its own
// voice — typeface class, weight, corner radius, letter-spacing and hero
// treatment — built from system fonts so the page still makes no network
// request and still opens instantly from an email attachment.
const VOICES = {
  trade: {   // plumbers, roofers, auto, smog, contractors
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 800, tracking: '-.035em', radius: '6px', caseLabel: 'uppercase',
    labelTrack: '.16em', heroSize: 'clamp(36px,7vw,66px)', rule: '3px',
  },
  care: {    // dentists, doctors, clinics
    display: '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif',
    weight: 600, tracking: '-.015em', radius: '16px', caseLabel: 'uppercase',
    labelTrack: '.14em', heroSize: 'clamp(33px,5.6vw,54px)', rule: '1px',
  },
  beauty: {  // salons, nails, spa, florists
    display: '"Iowan Old Style",Palatino,Georgia,serif',
    weight: 500, tracking: '.005em', radius: '2px', caseLabel: 'uppercase',
    labelTrack: '.26em', heroSize: 'clamp(34px,6vw,58px)', rule: '1px',
  },
  food: {    // bakeries, cafés, gyms, shops
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 750, tracking: '-.03em', radius: '20px', caseLabel: 'uppercase',
    labelTrack: '.1em', heroSize: 'clamp(35px,6.4vw,60px)', rule: '2px',
  },
};

function voiceOf(b) {
  if (b.voice && VOICES[b.voice]) return b.voice;
  const c = (b.category || '').toLowerCase();
  if (/dent|endodont|medical|doctor|clinic|health|vet|chiro|ortho/.test(c)) return 'care';
  if (/salon|nail|spa|beauty|hair|barber|massage|florist|flower/.test(c)) return 'beauty';
  if (/baker|café|cafe|coffee|restaurant|deli|food|climb|fitness|gym|shop|store|apparel/.test(c)) return 'food';
  if (/plumb|roof|auto|repair|smog|tyre|tire|electric|hvac|contractor|construct|landscap|clean/.test(c)) return 'trade';
  return 'trade';
}

function render(b) {
  const tel = digits(b.phone);
  const a = b.address || {};
  const accent = b.theme?.accent || '#0f6b5c';
  const v = VOICES[voiceOf(b)];

  // A menu earns its layout only when there is something to choose between.
  const cents = (p) => {
    const m = String(p || '').match(/(\d+(?:\.\d{1,2})?)/);
    return m ? Math.round(parseFloat(m[1]) * 100) : 0;
  };
  const mins = (d) => {
    const m = String(d || '').match(/(\d+)\s*(h|hr|hour|m|min)/i);
    if (!m) return 0;
    return /^h/i.test(m[2]) ? +m[1] * 60 : +m[1];
  };
  const groups = (() => {
    const out = new Map();
    for (const s of b.services || []) {
      const k = s.group || '';
      if (!out.has(k)) out.set(k, []);
      out.get(k).push(s);
    }
    return [...out.entries()];
  })();
  const ink = b.theme?.ink || '#12181c';
  const hero = b.theme?.heroImage;

  const nav = [
    b.services?.length && ['Services', '#services'],
    b.photos?.length && ['Work', '#work'],
    b.team?.length && ['Team', '#team'],
    b.about && ['About', '#about'],
    b.reviews?.length && ['Reviews', '#reviews'],
    ['Contact', '#contact'],
  ].filter(Boolean);

  return `<!doctype html>
<html lang="en" class="v-${voiceOf(b)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(b.name)}${b.category ? ' — ' + esc(b.category) : ''}${a.city ? ' in ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</title>
<meta name="description" content="${esc(b.tagline)}${b.phone ? ' Call ' + esc(b.phone) + '.' : ''}">
<meta property="og:type" content="website">${b.liveUrl ? `
<link rel="canonical" href="${esc(b.liveUrl)}">
<meta property="og:url" content="${esc(b.liveUrl)}">` : ''}
<meta property="og:title" content="${esc(b.name)}">
<meta property="og:description" content="${esc(b.tagline)}">
<meta name="twitter:card" content="summary_large_image">${b.logo ? `
<meta property="og:image" content="${esc(b.logo)}">` : ''}
<meta name="theme-color" content="${esc(accent)}">
<link rel="icon" href="${b.logo ? esc(b.logo) : 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="${accent}"/><text x="16" y="22" font-size="17" font-family="system-ui,sans-serif" font-weight="700" fill="#fff" text-anchor="middle">${(b.name || '?').trim()[0].toUpperCase()}</text></svg>`
)}">
<script type="application/ld+json">
${jsonld(b)}
</script>
<script>document.documentElement.className+=' js';</script>
<style>
  :root{
    --accent:${accent};
    --accent-ink:#fff;
    --ink:${ink};
    --muted:#5b6770;
    --line:#e3e8ea;
    --bg:#fff;
    --soft:#f6f8f8;
    --radius:${v.radius};
    --wrap:1080px;
    --display:${v.display};
    --display-weight:${v.weight};
    --tracking:${v.tracking};
    --label-case:${v.caseLabel};
    --label-track:${v.labelTrack};
    --hero-size:${v.heroSize};
    --rule:${v.rule};
    --ease:cubic-bezier(.2,.7,.2,1);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    margin:0;background:var(--bg);color:var(--ink);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}
  a{color:inherit}
  h1,h2,h3{line-height:1.14;margin:0;font-family:var(--display);
    font-weight:var(--display-weight);letter-spacing:var(--tracking);text-wrap:balance}
  h2{font-size:clamp(24px,3.4vw,33px);margin-bottom:10px}
  p{margin:0 0 14px}
  /* the header is sticky, so an anchored jump must leave room for it or the
     first line of the section lands underneath. */
  section{padding:64px 0;border-top:1px solid var(--line);scroll-margin-top:72px}
  .eyebrow{font-size:11.5px;font-weight:700;letter-spacing:var(--label-track);
    text-transform:var(--label-case);color:var(--accent);margin-bottom:14px}
  .lede{color:var(--muted);max-width:60ch;font-size:17px}

  /* a supplied logo leads the hero. Stacked wordmarks (name inside the art)
     are unreadable in a 66px header bar, so they belong here at full size. */
  .hero .logo{display:block;max-width:min(100%,var(--logo-w,300px));height:auto;
    margin:0 0 24px;mix-blend-mode:multiply}
  /* multiply needs something light behind it; on a full-bleed accent hero the
     logo keeps its own white card instead. */
  .v-trade .hero .logo{mix-blend-mode:normal;background:#fff;border-radius:8px;padding:10px}
  .v-care .hero .logo,.v-food .hero .logo{margin-left:auto;margin-right:auto}

  /* header */
  header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .bar{display:flex;align-items:center;gap:18px;height:66px}
  .brand{font-family:var(--display);font-weight:var(--display-weight);letter-spacing:var(--tracking);
    font-size:18px;text-decoration:none;margin-right:auto;display:flex;align-items:center;gap:10px;
    min-width:0}
  /* the bar is a fixed height, so a long name has to shrink rather than wrap */
  .brand .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  @media (max-width:520px){ .brand{font-size:16px} }
  @media (max-width:400px){ .brand{font-size:15px} }
  .mark{width:30px;height:30px;border-radius:8px;background:var(--accent);color:#fff;display:grid;place-items:center;font-size:15px;flex:none}
  /* a stacked logo is unreadable in a 66px bar, so the header takes a compact
     mark and sets the name in type beside it. */
  .mark-img{width:30px;height:30px;object-fit:contain;flex:none;display:block}
  nav{display:flex;gap:22px}
  nav a{color:var(--muted);text-decoration:none;font-size:15px;font-weight:500}
  nav a:hover{color:var(--ink)}
  .btn{
    display:inline-flex;align-items:center;justify-content:center;gap:8px;
    padding:12px 20px;border-radius:999px;font-weight:650;font-size:15px;
    text-decoration:none;border:1px solid transparent;white-space:nowrap;
  }
  .btn-primary{background:var(--accent);color:var(--accent-ink)}
  .btn-primary:hover{filter:brightness(.92)}
  .btn-ghost{border-color:var(--line);background:#fff;color:var(--ink)}
  .btn-ghost:hover{border-color:var(--muted)}

  /* hero */
  .hero{padding:74px 0 66px;position:relative;overflow:hidden}
  .hero::before{
    content:"";position:absolute;inset:0;z-index:-1;
    background:
      radial-gradient(760px 420px at 78% -8%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%),
      linear-gradient(180deg, var(--soft), #fff);
  }
  ${hero ? `.hero::after{content:"";position:absolute;inset:0;z-index:-2;background:url("${esc(hero)}") center/cover;opacity:.14}` : ''}
  .hero h1{font-size:var(--hero-size);max-width:17ch;text-wrap:balance}
  h2{text-wrap:balance}
  /* a measure set for desktop is a straitjacket on a 390px screen — it forces
     breaks the width itself would not. Let the phone use what it has. */
  .hero .lede{margin:18px 0 28px;font-size:19px}
  .actions{display:flex;flex-wrap:wrap;gap:12px}
  .hero-note{margin-top:20px;font-size:14px;color:var(--muted);
    padding-top:16px;border-top:var(--rule) solid color-mix(in srgb, var(--accent) 35%, transparent);
    display:inline-block}

  /* trust strip */
  /* Cell borders rather than a gap over a coloured container: an odd number of
     highlights used to leave the container colour showing as an empty grey box. */
  .trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;margin-top:44px;background:#fff}
  .trust div{background:#fff;padding:20px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
  .trust b{display:block;font-size:26px;letter-spacing:-.02em}
  .trust span{font-size:13px;color:var(--muted)}

  /* menu — grouped, priced, and selectable, the way a booking platform does it */
  .menu{margin-top:26px;display:flex;flex-direction:column;gap:26px}
  .mgroup h3{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
    color:var(--accent);margin:0 0 10px;padding-left:10px;border-left:3px solid var(--accent)}
  .rows{border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:#fff}
  /* a button carries a chunky default border on every side — left unreset it
     turns a clean list into a stack of boxes. */
  .row-svc{display:flex;align-items:flex-start;gap:13px;padding:14px 16px;
    border:0;border-bottom:1px solid var(--line);border-radius:0;
    width:100%;text-align:left;background:#fff;font:inherit;color:inherit;-webkit-appearance:none;appearance:none}
  .row-svc:last-child{border-bottom:0}
  .js .row-svc{cursor:pointer}
  .js .row-svc:hover{background:color-mix(in srgb, var(--accent) 4%, #fff)}
  .row-svc .tick{flex:none;width:21px;height:21px;margin-top:1px;border-radius:6px;
    border:1.5px solid var(--line);display:grid;place-items:center;
    font-size:11px;color:#fff;background:#fff}
  html:not(.js) .row-svc .tick{display:none}
  .row-svc.on{background:color-mix(in srgb, var(--accent) 7%, #fff)}
  .row-svc.on .tick{background:var(--accent);border-color:var(--accent)}
  .row-svc.on .tick::after{content:"\\2713"}
  /* these are spans, because a <button> may only hold phrasing content —
     so each one has to be told to take its own line. */
  .svc-main{flex:1;min-width:0;display:block}
  .svc-name{display:block;font-size:15.5px;font-weight:650;letter-spacing:-.01em;line-height:1.3}
  .svc-desc{display:block;font-size:12.5px;line-height:1.45;color:var(--muted);margin-top:3px}
  .svc-meta{flex:none;display:block;text-align:right;padding-left:4px}
  .svc-price{display:block;font-size:15.5px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.3}
  .svc-price .svc-unit{font-size:12px;font-weight:600;color:var(--muted)}
  .svc-dur{display:block;font-size:12px;color:var(--muted);margin-top:3px;white-space:nowrap}

  /* the running basket — appears once something is chosen */
  .basket{position:fixed;left:0;right:0;bottom:0;z-index:70;background:var(--accent);color:#fff;
    padding:12px 16px calc(12px + env(safe-area-inset-bottom));display:none;
    box-shadow:0 -8px 24px -12px rgba(0,0,0,.4)}
  .basket.up{display:flex;align-items:center;gap:14px}
  .basket .sum{flex:1;min-width:0;font-size:13.5px;line-height:1.3}
  .basket .sum b{display:block;font-size:16px;font-variant-numeric:tabular-nums}
  .basket .btn{background:#fff;color:var(--accent);border-color:#fff;white-space:nowrap}
  .basket .clear{background:transparent;color:rgba(255,255,255,.85);border:0;font-size:13px;
    text-decoration:underline;padding:6px}

  /* team */
  .team{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:26px}
  .member{border:1px solid var(--line);border-radius:var(--radius);padding:18px;text-align:center;background:#fff}
  /* a one-person business is a selling point, but a lone card floating in a
     full-width box reads as an unfinished page. Lay it on its side instead. */
  .team.solo{grid-template-columns:1fr}
  .team.solo .member{display:flex;align-items:center;gap:16px;text-align:left;padding:16px 18px}
  .team.solo .member .av{margin:0}
  .member .av{width:52px;height:52px;border-radius:50%;margin:0 auto 10px;display:grid;place-items:center;
    background:color-mix(in srgb, var(--accent) 12%, #fff);color:var(--accent);font-weight:700;font-size:19px}
  .member b{display:block;letter-spacing:-.01em}
  .member span{font-size:12.5px;color:var(--muted)}

  /* services */
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px;margin-top:30px}
  .card{border:1px solid var(--line);border-radius:var(--radius);padding:22px;background:#fff}
  .card h3{font-size:18px;margin-bottom:6px}
  .card p{color:var(--muted);font-size:15px;margin:0}
  .price{display:inline-block;margin-top:14px;font-weight:700;font-size:14px;color:var(--accent);background:color-mix(in srgb, var(--accent) 10%, #fff);padding:5px 11px;border-radius:999px}

  /* about */
  .split{display:grid;grid-template-columns:1.15fr .85fr;gap:44px;align-items:start}
  .panel{background:var(--soft);border:1px solid var(--line);border-radius:var(--radius);padding:24px}
  .panel h3{font-size:15px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:14px}
  .rows{display:flex;flex-direction:column;gap:9px;font-size:15px}
  .row{display:flex;justify-content:space-between;gap:16px}
  .row span:first-child{color:var(--muted)}
  ul.ticks{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:10px}
  ul.ticks li{padding-left:28px;position:relative;color:var(--muted)}
  ul.ticks li::before{content:"\\2713";position:absolute;left:0;top:4px;width:18px;height:18px;border-radius:50%;
    background:var(--accent);color:#fff;font-size:11px;font-weight:700;line-height:18px;text-align:center}

  /* gallery — for businesses whose work IS the product */
  .shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:28px}
  .shots figure{margin:0;border-radius:var(--radius);overflow:hidden;background:var(--soft);
    border:1px solid var(--line);aspect-ratio:1/1}
  .shots img{width:100%;height:100%;object-fit:cover;display:block}
  .shots figure:first-child{grid-column:span 2;grid-row:span 2;aspect-ratio:1/1}
  @media (max-width:520px){ .shots figure:first-child{grid-column:span 2;grid-row:auto} }

  /* reviews */
  .stars{color:#e8a33d;letter-spacing:2px}
  .quote{border:1px solid var(--line);border-radius:var(--radius);padding:24px;background:#fff}
  .quote p{font-size:16px}
  .quote footer{font-size:14px;color:var(--muted);font-weight:600}

  /* contact */
  .contact{background:var(--soft)}
  .cta-box{border:1px solid var(--line);border-radius:var(--radius);background:#fff;padding:32px;text-align:center}
  .cta-box h2{margin-bottom:8px}
  .cta-box .actions{justify-content:center;margin-top:22px}
  .big-phone{font-size:clamp(28px,5vw,40px);font-weight:800;letter-spacing:-.02em;text-decoration:none;display:inline-block;margin:6px 0}

  footer.site{padding:30px 0;color:var(--muted);font-size:14px;display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between}

  /* sticky mobile call bar */
  .callbar{display:none}
  @media (max-width:760px){
    nav{display:none}
    .hero{padding:44px 0 40px}
    .split{grid-template-columns:1fr;gap:28px}
    section{padding:48px 0}
    body{padding-bottom:74px}
    .callbar{
      display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;gap:10px;padding:10px 14px;
      background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border-top:1px solid var(--line);
    }
    .callbar .btn{flex:1}
    .bar .btn span.label{display:none}
  }
  /* ── hero shape per voice ─────────────────────────────────────────────────
     Type alone could not separate two sans voices without loading web fonts,
     which would break the "no external requests" promise in the pitch. So the
     hero is structurally different instead. */

  /* TRADE — a full-bleed block of colour. Reads like a work truck. */
  .v-trade .hero{background:var(--accent);padding-top:56px}
  .v-trade .hero::before{opacity:.18}
  .v-trade .hero h1{color:#fff}
  .v-trade .hero .eyebrow{color:rgba(255,255,255,.72)}
  .v-trade .hero .lede{color:rgba(255,255,255,.88)}
  .v-trade .hero-note{color:rgba(255,255,255,.75);border-top-color:rgba(255,255,255,.32)}
  .v-trade .hero .btn-primary{background:#fff;color:var(--accent);border-color:#fff}
  .v-trade .hero .btn-ghost{background:transparent;color:#fff;border-color:rgba(255,255,255,.55)}
  .v-trade .trust{border-color:rgba(255,255,255,.3);margin-top:38px}

  /* CARE — centred and unhurried. Calm is the product. */
  .v-care .hero{padding:84px 0 70px;text-align:center}
  .v-care .hero h1,.v-care .hero .lede{margin-left:auto;margin-right:auto}
  .v-care .hero .actions{justify-content:center}
  .v-care .hero-inner{max-width:44rem;margin:0 auto}

  /* BEAUTY — editorial: a rule down the side, deep top margin, nothing rushed. */
  .v-beauty .hero{padding:92px 0 68px}
  .v-beauty .hero-inner{border-left:2px solid var(--accent);padding-left:26px}
  .v-beauty .hero h1{max-width:14ch}

  /* Measures tuned for a desktop column are a straitjacket on a 390px screen:
     they force line breaks the width itself would never make. This has to sit
     after the per-voice rules — it matches their specificity, so order decides. */
  @media (max-width:640px){
    .hero h1,.v-trade .hero h1,.v-care .hero h1,.v-beauty .hero h1,.v-food .hero h1{max-width:none}
  }
  .v-beauty .eyebrow{padding-bottom:14px;border-bottom:1px solid var(--line);display:inline-block}

  /* FOOD — the copy sits on a warm card, like something on a counter. */
  .v-food .hero{padding:40px 0 52px}
  .v-food .hero-inner{background:color-mix(in srgb, var(--accent) 8%, #fff);
    border:1px solid color-mix(in srgb, var(--accent) 18%, var(--line));
    border-radius:26px;padding:36px 32px}
  .v-food .trust{margin-top:20px}

  @media (max-width:760px){
    .v-food .hero-inner{padding:26px 20px;border-radius:20px}
    .v-beauty .hero-inner{padding-left:18px}
    .v-care .hero{padding:52px 0 44px}
    .v-beauty .hero{padding:56px 0 44px}
  }

  /* ── motion ──────────────────────────────────────────────────────────────
     A short load sequence in the hero, then sections arrive as you reach them.
     Everything below is opt-out: with reduced motion the page renders finished. */
  @media (prefers-reduced-motion:no-preference){
    /* Scoped to .js — set by an inline script before paint. With scripting off
       or blocked (some mail clients preview attachments that way) nothing is
       ever hidden, and the page simply renders finished. */
    .js .rise{opacity:0;transform:translateY(14px)}
    .js .in .rise,.js .rise.in{opacity:1;transform:none;
      transition:opacity .62s var(--ease),transform .62s var(--ease)}
    .js .hero .rise{transition-delay:calc(var(--i,0) * 90ms)}
    .card{transition:transform .28s var(--ease),border-color .28s var(--ease),box-shadow .28s var(--ease)}
    .card:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 45%,var(--line));
      box-shadow:0 10px 24px -14px rgba(16,32,40,.35)}
    .btn{transition:transform .18s var(--ease),filter .18s var(--ease)}
    .btn:active{transform:scale(.97)}
    .trust div{transition:background .3s var(--ease)}
    .trust div:hover{background:color-mix(in srgb,var(--accent) 5%,#fff)}
    .js .callbar{transform:translateY(110%);transition:transform .38s var(--ease)}
    .js .callbar.up{transform:none}
    .tel-pulse{position:relative}
  }
  @media (prefers-reduced-motion:reduce){
    .rise,.js .rise{opacity:1;transform:none}
    .callbar,.js .callbar{transform:none}
  }

  @media print{header,.callbar{position:static}.rise{opacity:1;transform:none}}
</style>
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="#top">${
      b.mark ? `<img class="mark-img" src="${esc(b.mark)}" alt="">`
      : b.logo ? ''
      : `<span class="mark">${esc((b.name || '?').trim()[0].toUpperCase())}</span>`
    }<span class="nm">${esc(b.shortName || b.name)}</span></a>
    <nav>${nav.map(([t, h]) => `<a href="${h}">${esc(t)}</a>`).join('')}</nav>
    ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call <span class="label">${esc(b.phone)}</span></a>` : ''}
  </div>
</header>

<main id="top">

<div class="hero">
  <div class="wrap">
    <div class="hero-inner">
    ${b.logo ? `<img class="logo rise" style="--i:0" src="${esc(b.logo)}" alt="${esc(b.name)}" width="${esc(b.logoWidth || 300)}">` : ''}
    ${b.category ? `<div class="eyebrow rise" style="--i:0">${esc(b.category)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</div>` : ''}
    <h1 class="rise" style="--i:1">${esc(b.headline || b.tagline)}</h1>
    ${b.subhead ? `<p class="lede rise" style="--i:2">${esc(b.subhead)}</p>` : ''}
    <div class="actions rise" style="--i:3">
      ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">${esc(b.cta?.primary || 'Call ' + b.phone)}</a>` : ''}
      ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Get directions</a>` : ''}
    </div>
    ${b.heroNote ? `<div class="hero-note rise" style="--i:4">${esc(b.heroNote)}</div>` : ''}
    </div>
    ${b.highlights?.length ? `<div class="trust rise" style="--i:5">${b.highlights.map((h) =>
      `<div><b>${esc(h.value)}</b><span>${esc(h.label)}</span></div>`).join('')}</div>` : ''}
  </div>
</div>

${b.services?.length ? `
<section id="services">
  <div class="wrap">
    <div class="eyebrow">Services</div>
    <h2>${esc(b.servicesHeading || 'What we do')}</h2>
    ${b.servicesLede ? `<p class="lede">${esc(b.servicesLede)}</p>` : ''}
    ${''/* Every service list is a menu people choose from, not a row of cards.
           Prices and durations show when the business has given them; when it
           has not, the choosing and the request still work. We never invent a
           number to fill the column. */}
    ${`<div class="menu">${groups.map(([name, items]) => `
        <div class="mgroup">
          ${name ? `<h3>${esc(name)}</h3>` : ''}
          <div class="rows">
            ${items.map((s) => `<button type="button" class="row-svc" data-price="${esc(cents(s.price))}" data-mins="${esc(mins(s.duration))}" data-unit="${esc(s.unit || '')}" data-name="${esc(s.name)}">
              <span class="tick" aria-hidden="true"></span>
              <span class="svc-main">
                <span class="svc-name">${esc(s.name)}</span>
                ${s.desc ? `<span class="svc-desc">${esc(s.desc)}</span>` : ''}
              </span>
              <span class="svc-meta">
                ${s.price ? `<span class="svc-price">${esc(s.price)}${s.unit ? `<span class="svc-unit">${esc(s.unit)}</span>` : ''}</span>` : ''}
                ${s.duration ? `<span class="svc-dur">${esc(s.duration)}</span>` : ''}
              </span>
            </button>`).join('')}
          </div>
        </div>`).join('')}</div>`}
  </div>
</section>` : ''}

${b.team?.length ? `
<section id="team">
  <div class="wrap">
    <div class="eyebrow">Our team</div>
    <h2>${esc(b.teamHeading || 'Who you will see')}</h2>
    ${b.teamLede ? `<p class="lede">${esc(b.teamLede)}</p>` : ''}
    <div class="team${b.team.length === 1 ? ' solo' : ''}">
      ${b.team.map((m) => `<div class="member">
        <div class="av">${esc((m.name || '?').trim()[0].toUpperCase())}</div>
        <b>${esc(m.name)}</b>
        ${m.role ? `<span>${esc(m.role)}</span>` : ''}
      </div>`).join('')}
    </div>
  </div>
</section>` : ''}

${b.photos?.length ? `
<section id="work">
  <div class="wrap">
    <div class="eyebrow">${esc(b.galleryEyebrow || 'Our work')}</div>
    <h2>${esc(b.galleryHeading || 'Recent work')}</h2>
    ${b.galleryLede ? `<p class="lede">${esc(b.galleryLede)}</p>` : ''}
    <div class="shots">
      ${b.photos.map((p, i) => `<figure><img src="${esc(p.src || p)}" alt="${esc(p.alt || b.name + ' — photo ' + (i + 1))}" loading="lazy"></figure>`).join('')}
    </div>
  </div>
</section>` : ''}

${b.about ? `
<section id="about">
  <div class="wrap split">
    <div>
      <div class="eyebrow">About</div>
      <h2>${esc(b.aboutHeading || 'About ' + b.name)}</h2>
      ${String(b.about).split('\n\n').map((p) => `<p class="lede">${esc(p)}</p>`).join('')}
      ${b.points?.length ? `<ul class="ticks">${b.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>` : ''}
    </div>
    <div class="panel">
      ${b.hours?.length ? `<h3>Hours</h3><div class="rows">${b.hours.map((h) =>
        `<div class="row"><span>${esc(h.days)}</span><span>${esc(h.time)}</span></div>`).join('')}</div>` : ''}
      ${b.serviceArea?.length ? `<h3 style="margin-top:22px">Service area</h3><p style="color:var(--muted);font-size:15px;margin:0">${esc(b.serviceArea.join(' · '))}</p>` : ''}
      ${a.street ? `<h3 style="margin-top:22px">Find us</h3>
        <p style="font-size:15px;margin:0 0 12px">${esc(addressLine(a))}</p>
        <a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Open in Maps</a>` : ''}
    </div>
  </div>
</section>` : ''}

${b.reviews?.length ? `
<section id="reviews">
  <div class="wrap">
    <div class="eyebrow">Reviews</div>
    <h2>${esc(b.reviewsHeading || 'What customers say')}</h2>
    ${b.rating ? `<p class="lede">${stars(b.rating.value)} ${esc(b.rating.value)} from ${esc(b.rating.count)} reviews${b.rating.source ? ' on ' + esc(b.rating.source) : ''}.</p>` : ''}
    <div class="grid">
      ${b.reviews.map((r) => `<blockquote class="quote">
        ${r.stars ? stars(r.stars) : stars(5)}
        <p>“${esc(r.text)}”</p>
        <footer>— ${esc(r.author)}${r.source ? ', ' + esc(r.source) : ''}</footer>
      </blockquote>`).join('')}
    </div>
  </div>
</section>` : ''}

<section id="contact" class="contact">
  <div class="wrap">
    <div class="cta-box">
      <h2>${esc(b.ctaHeading || 'Ready when you are')}</h2>
      <p class="lede" style="margin:0 auto">${esc(b.ctaLede || 'Call and talk to a real person.')}</p>
      ${b.phone ? `<a class="big-phone" href="tel:${esc(tel)}" style="color:var(--accent)">${esc(b.phone)}</a>` : ''}
      <div class="actions">
        ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call now</a>` : ''}
        ${b.email ? `<a class="btn btn-ghost" href="mailto:${esc(b.email)}">Email us</a>` : ''}
        ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Directions</a>` : ''}
      </div>
    </div>
  </div>
</section>

</main>

<footer class="site">
  <div class="wrap" style="display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;width:100%">
    <span>© ${new Date().getFullYear()} ${esc(b.name)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</span>
    <span>${esc(b.phone || '')}${b.license ? ' · ' + esc(b.license) : ''}</span>
  </div>
</footer>

${b.services?.length ? `<div class="basket" id="basket" hidden>
  <div class="sum"><b id="bkTotal"></b><span id="bkMeta"></span></div>
  <button type="button" class="clear" id="bkClear">Clear</button>
  <a class="btn" id="bkGo" href="#">Request</a>
</div>` : ''}

${b.phone ? `<div class="callbar">
  <a class="btn btn-primary" href="tel:${esc(tel)}">Call ${esc(b.phone)}</a>
  ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Map</a>` : ''}
</div>` : ''}

<script>
(function(){
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero');

  // Motion is a preference. Booking is a function. Reducing one must never
  // remove the other — an early return here once disabled the whole menu.
  if (reduce) {
    document.querySelectorAll('.rise').forEach(function(el){ el.classList.add('in'); });
  } else {
    requestAnimationFrame(function(){ hero && hero.classList.add('in'); });

    var targets = document.querySelectorAll('section .eyebrow, section h2, section .lede, .card, .quote, .panel, .cta-box, ul.ticks li');
    targets.forEach(function(el){ el.classList.add('rise'); });
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (!e.isIntersecting) return;
          e.target.classList.add('in');
          io.unobserve(e.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
      targets.forEach(function(el){ io.observe(el); });
    } else {
      targets.forEach(function(el){ el.classList.add('in'); });
    }
  }

  // Choose services, see the running total, then send the request as a text or
  // an email. No backend, no booking account — it composes the message and the
  // customer sends it from their own phone.
  var basket = document.getElementById('basket');
  if (basket) {
    var picked = [];
    var TEL = ${JSON.stringify(digits(b.phone || ''))};
    var MAIL = ${JSON.stringify(b.email || '')};
    var BOOKURL = ${JSON.stringify(b.booking?.url || '')};
    var BIZ = ${JSON.stringify(b.name || '')};
    // A quote trade is not a booking trade. Nobody books a re-roof; they ask
    // someone to come and look at it.
    var QUOTES = ${JSON.stringify(!(b.services || []).some((s) => s.price))};
    // Some trades travel to the customer; for everyone else the customer
    // travels to them. "When could you come out?" to a dentist is nonsense.
    var VISITS = ${JSON.stringify(/plumb|roof|electric|hvac|contractor|construct|carpenter|painter|glaz|floor|tiler|locksmith|garden|landscap|pool|spa service|hot tub|clean|pest|gutter|window|upholster|mov|haul/i.test(b.category || ''))};

    var money = function(c){ return '$' + (c/100).toFixed(2).replace(/\.00$/,''); };
    // People book in hours and minutes, not decimals. "3.3 hr" is not a time.
    var time = function(m){
      if (m < 60) return m + ' min';
      var h = Math.floor(m / 60), r = m % 60;
      return h + ' hr' + (r ? ' ' + r + ' min' : '');
    };

    var paint = function(){
      if (!picked.length) {
        basket.hidden = true; basket.classList.remove('up');
        document.body.style.paddingBottom = '';
        return;
      }
      // A $145/mo plan and a $395 one-off job cannot be added into one number.
      // Sum each unit separately: "$395 + $145/mo", never a meaningless $540.
      var sums = {}, order = [];
      picked.forEach(function(p){
        var u = p.unit || '';
        if (!(u in sums)) { sums[u] = 0; if (u) order.push(u); }
        sums[u] += p.price;
      });
      var parts = [];
      if (sums['']) parts.push(money(sums['']));
      order.forEach(function(u){ if (sums[u]) parts.push(money(sums[u]) + u); });
      var priced = parts.join(' + ');

      // Time on site only means something for a one-off visit; a monthly plan
      // is not "about 90 minutes".
      var dur = picked.reduce(function(n,p){ return n + (p.unit ? 0 : p.mins); }, 0);

      basket.hidden = false; basket.classList.add('up');
      document.getElementById('bkTotal').textContent =
        picked.length + (picked.length === 1 ? ' service' : ' services') + (priced ? ' · ' + priced : '');
      document.getElementById('bkMeta').textContent = dur ? 'about ' + time(dur) : '';

      var lines = picked.map(function(p){
        return '• ' + p.name + (p.price ? ' (' + money(p.price) + (p.unit || '') + ')' : '');
      }).join('\\n');
      var msg = 'Hi ' + BIZ + ', ' +
                (!QUOTES ? 'I would like to book:'
                 : VISITS ? 'could I get an estimate for:'
                 : 'could I book in for:') + '\\n' + lines +
                (priced ? '\\n\\nTotal: ' + priced : '') +
                (dur ? '\\nAbout ' + time(dur) + ' on site' : '') +
                '\\n\\n' + (!QUOTES ? 'What times do you have?'
                                : VISITS ? 'When could you come out?'
                                : 'When could you fit me in?');
      var go = document.getElementById('bkGo');
      if (BOOKURL) { go.href = BOOKURL; go.textContent = 'Book online'; }
      else if (QUOTES && TEL) { go.href = 'sms:' + TEL + '?&body=' + encodeURIComponent(msg);
                                go.textContent = VISITS ? 'Get a quote' : 'Request appointment'; }
      else if (TEL) { go.href = 'sms:' + TEL + '?&body=' + encodeURIComponent(msg); go.textContent = 'Text this'; }
      else if (MAIL) { go.href = 'mailto:' + MAIL + '?subject=' + encodeURIComponent('Booking request') +
                        '&body=' + encodeURIComponent(msg); go.textContent = 'Email this'; }
      else { go.href = '#'; go.textContent = 'Call us'; }
    };

    document.querySelectorAll('.row-svc').forEach(function(el){
      el.addEventListener('click', function(){
        var name = el.dataset.name;
        var i = picked.findIndex(function(p){ return p.name === name; });
        if (i > -1) { picked.splice(i,1); el.classList.remove('on'); }
        else { picked.push({ name: name, price: +el.dataset.price || 0, mins: +el.dataset.mins || 0,
                             unit: el.dataset.unit || '' });
               el.classList.add('on'); }
        paint();
      });
    });
    document.getElementById('bkClear').addEventListener('click', function(){
      picked = [];
      document.querySelectorAll('.row-svc.on').forEach(function(el){ el.classList.remove('on'); });
      paint();
    });
  }

  // The call bar stays out of the way until you have actually started reading.
  var bar = document.querySelector('.callbar');
  if (bar) {
    var show = function(){
      var busy = basket && !basket.hidden;
      bar.classList.toggle('up', (reduce || scrollY > 220) && !busy);
    };
    if (basket) new MutationObserver(show).observe(basket, { attributes: true });
    addEventListener('scroll', show, { passive: true }); show();
  }
})();
</script>
</body>
</html>
`;
};

// A single stray backslash in the emitted <script> once shipped a page whose
// entire booking system was dead on arrival — and nothing said a word, because
// broken JavaScript in a browser just quietly does nothing. No page leaves this
// file again without its script being parsed first.
module.exports = function renderChecked(b) {
  const html = render(b);
  for (const [, attrs, js] of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (/^\s*$/.test(js)) continue;
    const type = (attrs.match(/type\s*=\s*["']([^"']+)/i) || [])[1];
    if (type && !/javascript|module/i.test(type)) continue;   // JSON-LD is not code
    try { new Function(js); } catch (e) {
      throw new Error(`${b.slug || b.name || 'page'}: emitted page script will not parse — ${e.message}`);
    }
  }
  return html;
};
module.exports.unchecked = render;
