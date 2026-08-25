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
    url: b.newUrl || undefined,
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

module.exports = function render(b) {
  const tel = digits(b.phone);
  const a = b.address || {};
  const accent = b.theme?.accent || '#0f6b5c';
  const ink = b.theme?.ink || '#12181c';
  const hero = b.theme?.heroImage;

  const nav = [
    b.services?.length && ['Services', '#services'],
    b.about && ['About', '#about'],
    b.reviews?.length && ['Reviews', '#reviews'],
    ['Contact', '#contact'],
  ].filter(Boolean);

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(b.name)}${b.category ? ' — ' + esc(b.category) : ''}${a.city ? ' in ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</title>
<meta name="description" content="${esc(b.tagline)}${b.phone ? ' Call ' + esc(b.phone) + '.' : ''}">
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(b.name)}">
<meta property="og:description" content="${esc(b.tagline)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="${esc(accent)}">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="${accent}"/><text x="16" y="22" font-size="17" font-family="system-ui,sans-serif" font-weight="700" fill="#fff" text-anchor="middle">${(b.name || '?').trim()[0].toUpperCase()}</text></svg>`
)}">
<script type="application/ld+json">
${jsonld(b)}
</script>
<style>
  :root{
    --accent:${accent};
    --accent-ink:#fff;
    --ink:${ink};
    --muted:#5b6770;
    --line:#e3e8ea;
    --bg:#fff;
    --soft:#f6f8f8;
    --radius:14px;
    --wrap:1080px;
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
  h1,h2,h3{line-height:1.15;letter-spacing:-.02em;margin:0}
  h2{font-size:clamp(24px,3.4vw,33px);margin-bottom:10px}
  p{margin:0 0 14px}
  section{padding:64px 0;border-top:1px solid var(--line)}
  .eyebrow{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:12px}
  .lede{color:var(--muted);max-width:60ch;font-size:17px}

  /* header */
  header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .bar{display:flex;align-items:center;gap:18px;height:66px}
  .brand{font-weight:800;letter-spacing:-.02em;font-size:18px;text-decoration:none;margin-right:auto;display:flex;align-items:center;gap:10px}
  .mark{width:30px;height:30px;border-radius:8px;background:var(--accent);color:#fff;display:grid;place-items:center;font-size:15px;flex:none}
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
  .hero h1{font-size:clamp(34px,6vw,58px);max-width:16ch}
  .hero .lede{margin:18px 0 28px;font-size:19px}
  .actions{display:flex;flex-wrap:wrap;gap:12px}
  .hero-note{margin-top:20px;font-size:14px;color:var(--muted)}

  /* trust strip */
  /* Cell borders rather than a gap over a coloured container: an odd number of
     highlights used to leave the container colour showing as an empty grey box. */
  .trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;margin-top:44px;background:#fff}
  .trust div{background:#fff;padding:20px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
  .trust b{display:block;font-size:26px;letter-spacing:-.02em}
  .trust span{font-size:13px;color:var(--muted)}

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
  @media print{header,.callbar{position:static}}
</style>
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="#top"><span class="mark">${esc((b.name || '?').trim()[0].toUpperCase())}</span>${esc(b.name)}</a>
    <nav>${nav.map(([t, h]) => `<a href="${h}">${esc(t)}</a>`).join('')}</nav>
    ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call <span class="label">${esc(b.phone)}</span></a>` : ''}
  </div>
</header>

<main id="top">

<div class="hero">
  <div class="wrap">
    ${b.category ? `<div class="eyebrow">${esc(b.category)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</div>` : ''}
    <h1>${esc(b.headline || b.tagline)}</h1>
    ${b.subhead ? `<p class="lede">${esc(b.subhead)}</p>` : ''}
    <div class="actions">
      ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">${esc(b.cta?.primary || 'Call ' + b.phone)}</a>` : ''}
      ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Get directions</a>` : ''}
    </div>
    ${b.heroNote ? `<div class="hero-note">${esc(b.heroNote)}</div>` : ''}
    ${b.highlights?.length ? `<div class="trust">${b.highlights.map((h) =>
      `<div><b>${esc(h.value)}</b><span>${esc(h.label)}</span></div>`).join('')}</div>` : ''}
  </div>
</div>

${b.services?.length ? `
<section id="services">
  <div class="wrap">
    <div class="eyebrow">Services</div>
    <h2>${esc(b.servicesHeading || 'What we do')}</h2>
    ${b.servicesLede ? `<p class="lede">${esc(b.servicesLede)}</p>` : ''}
    <div class="grid">
      ${b.services.map((s) => `<div class="card">
        <h3>${esc(s.name)}</h3>
        ${s.desc ? `<p>${esc(s.desc)}</p>` : ''}
        ${s.price ? `<span class="price">${esc(s.price)}</span>` : ''}
      </div>`).join('')}
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

${b.phone ? `<div class="callbar">
  <a class="btn btn-primary" href="tel:${esc(tel)}">Call ${esc(b.phone)}</a>
  ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Map</a>` : ''}
</div>` : ''}

</body>
</html>
`;
};
