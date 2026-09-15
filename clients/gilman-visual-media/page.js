// The page for Gilman Visual Media, built by hand against DESIGN.md.
//
// Everything on it is theirs: the about text, the price list, the four
// reasons to choose them, the Proust line, the get-in-touch paragraph, and
// sixteen of their own photographs — all read off gilmanvisualmedia.com
// (browse.json) and kept in business.json beside this file. This file
// decides only how it looks. Their site prints no phone, email, city or
// reviews, so none appear here; the ask goes to their Instagram and to the
// contact form on their current site.
//
// Self-contained: system fonts, an inline SVG grain, photos as data URIs.
// Works with JavaScript off. Judged at 390px.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// Same grain as tools/render.js: felt, not seen.
const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .16"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

const INSTAGRAM = 'https://www.instagram.com/gilmanvisualmedia';
const MESSAGE = 'https://ig.me/m/gilmanvisualmedia';
const SITE = 'https://www.gilmanvisualmedia.com/';
const FORM = SITE + 'contact/';
const PORTFOLIO = SITE + 'portfolio/';

function render(b) {
  const photos = b.photos || [];
  const pick = (re) => photos.find((p) => re.test(p.alt || '')) || null;
  // Each photograph is written into the page once, as a CSS variable; every
  // place it appears (the hero table, a strip, the screened break) points at
  // that one copy. Six of them sit in two places, and a data URI twice is a
  // megabyte for nothing.
  const vars = photos.map((p, i) => `--ph${i}:url("${p.src}")`).join(';');
  const img = (p, ratio) => !p ? '' :
    `<span class="ph" role="img" aria-label="${esc(p.alt)}" style="--src:var(--ph${photos.indexOf(p)});aspect-ratio:${ratio || '3/2'}"></span>`;
  const polaroid = (p, ratio, cap) => !p ? '' :
    `<figure class="polaroid"><span class="tape" aria-hidden="true"></span>${img(p, ratio)}<figcaption>${esc(cap || p.caption || '')}</figcaption></figure>`;
  const print = (p, cls, ratio) => !p ? '' :
    `<figure class="print ${cls}" aria-hidden="true">${img(p, ratio)}</figure>`;

  // The photographs, by what is in them.
  const rushmore = pick(/Rushmore/);
  const lift = pick(/groom lifting/);
  const sunflowerWoman = pick(/sunflower field/);
  const headshot = pick(/white shirt and tie/);
  const close = pick(/close together/);
  const yellowLab = pick(/yellow Labrador/);
  const badlands = pick(/Badlands/);
  const tieDye = pick(/tie-dye/);
  const archKiss = pick(/kissing under/);
  const cat = pick(/orange cat/);
  const needles = pick(/Needles/);
  const lakeside = pick(/lakeside/);
  const bwDog = pick(/black and white dog/);
  const sunflowers = pick(/^Sunflowers/);
  const bison = pick(/bison/);
  const blackLab = pick(/black Labrador/);

  const services = b.services || [];
  const groups = [...new Set(services.map((s) => s.group))];
  let n = 0;
  const card = (s) => {
    n++;
    return `<article class="card"><span class="bx" aria-hidden="true"></span>
      <div class="pair"><span class="n">${String(n).padStart(2, '0')}</span><span class="k">${esc(s.group)} / ${esc(s.name)}</span></div>
      <h3>${esc(s.name)}</h3>
      <p>${esc(s.desc)}</p>
      <div class="spec"><span class="price">${esc(s.price)}</span>${s.duration ? `<span class="dur">${esc(s.duration)}</span>` : ''}</div>
    </article>`;
  };

  // Their "Why choose us", as a spec table. Every value is their wording.
  const why = [
    ['Hidden fees', 'None — clear, upfront rates'],
    ['Delivery', 'A personal, password-protected online gallery'],
    ['Editing', 'Intentional and minimal — true to life'],
    ['Ownership', 'Full personal print releases'],
    ['Drone', 'FAA-certified · fully insured · 4K & RAW'],
  ];
  // Their stated delivery times, from the price list.
  const when = [
    ['Real estate & aerial', '24–48 hours'],
    ['Portraits', '5–7 business days'],
    ['Weddings', 'Full gallery in 3–5 weeks'],
  ];

  const ld = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    name: b.name,
    url: SITE,
    sameAs: [INSTAGRAM],
    description: b.subhead,
    makesOffer: services.map((s) => {
      const low = Number((String(s.price).match(/\$([\d,]+)/) || [])[1]?.replace(/,/g, ''));
      return { '@type': 'Offer', name: s.name, category: s.group,
        priceSpecification: low ? { '@type': 'PriceSpecification', minPrice: low, priceCurrency: 'USD' } : undefined };
    }),
  };
  const jsonld = JSON.stringify(ld, (k, v) => (v === undefined ? undefined : v), 2).replace(/</g, '\\u003c');

  const favicon = 'data:image/svg+xml,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#1b1816"/><text x="16" y="23" font-size="19" font-family="Georgia,serif" font-weight="700" fill="#c9702b" text-anchor="middle">G</text></svg>`);

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gilman Visual Media — Photography, real estate and aerial</title>
<meta name="description" content="${esc(b.subhead)}">
<meta property="og:title" content="Gilman Visual Media">
<meta property="og:description" content="${esc(b.tagline)}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#1b1816">
<link rel="icon" href="${favicon}">
<script type="application/ld+json">
${jsonld}
</script>
<script>document.documentElement.className+=' js';</script>
<style>
  :root{
    --ink:#1b1816;
    --paper:#f5f0e6;
    --paper-2:#ede3d0;
    --cream:#f2dfbf;
    --brown:#6b5d4f;
    --accent:#c9702b;
    --white:#fbf9f5;
    --line:rgba(27,24,22,.16);
    --muted:#6f6659;
    --grid:rgba(30,24,16,.05);
    --grain:url("${GRAIN}");
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --wrap:1080px;
    --ease:cubic-bezier(.2,.7,.2,1);
  }
  :root{${vars}}
  .ph{display:block;width:100%;background:var(--src) center/cover no-repeat}
  *{box-sizing:border-box}
  html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
  body{margin:0;color:var(--ink);background:var(--paper);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit}
  img{display:block;max-width:100%}
  p{margin:0 0 16px}
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}

  /* ── grounds: grain and a faint grid on both, ink and paper ─────────── */
  .ink,.paper,.paper-2{background-image:var(--grain),
    linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:220px 220px,36px 36px,36px 36px}
  .paper{background-color:var(--paper)}
  .paper-2{background-color:var(--paper-2)}
  .ink{background-color:var(--ink);color:var(--paper);--grid:rgba(255,255,255,.045);--line:rgba(255,255,255,.16);--muted:rgba(245,240,230,.58)}
  section{padding:clamp(72px,14vw,150px) 0;scroll-margin-top:12px}

  /* ── three scales of type, far apart ────────────────────────────────── */
  .k,.n{font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .n{color:var(--accent)}
  .pair{display:flex;justify-content:space-between;gap:16px;align-items:baseline;color:var(--muted)}
  .pair .k{text-align:right}
  .pair .n{color:var(--accent)}
  h1,h2,h3{margin:0;font-family:var(--serif);font-weight:700;line-height:.96;letter-spacing:-.025em;text-wrap:balance;overflow-wrap:anywhere}
  h2{font-size:clamp(46px,13vw,112px);margin:22px 0 26px}
  h2 em{font-style:normal;color:var(--accent)}
  h3{font-size:clamp(30px,8vw,64px);margin:10px 0 0}
  .prose{font-family:var(--serif);font-size:18.5px;line-height:1.6;max-width:62ch}
  .lede{font-size:18px;line-height:1.55;max-width:56ch;color:var(--brown)}

  /* stickers: solid fill, hard offset shadow, tilted a couple of degrees */
  .sticker{display:inline-block;max-width:100%;background:var(--accent);color:var(--paper);font:700 10px/1.45 var(--mono);
    letter-spacing:.14em;text-transform:uppercase;text-wrap:balance;padding:7px 11px 6px;box-shadow:3px 3px 0 var(--ink);
    transform:rotate(-1.6deg);transform-origin:left center}
  .ink .sticker{box-shadow:3px 3px 0 var(--paper)}
  .sticker.paper-label{background:var(--white);color:var(--ink);border:1px solid var(--ink);transform:rotate(1.4deg);box-shadow:2px 2px 0 var(--ink)}

  /* corner brackets, never rounded cards */
  .card,.frame{position:relative;padding:22px 18px 20px}
  .card::before,.card::after,.bx::before,.bx::after,.frame::before,.frame::after,.frame .bx::before,.frame .bx::after{
    content:"";position:absolute;width:14px;height:14px;border:1px solid currentColor;opacity:.7}
  .card::before,.frame::before{top:0;left:0;border-right:0;border-bottom:0}
  .card::after,.frame::after{bottom:0;right:0;border-left:0;border-top:0}
  .bx::before{top:0;right:0;border-left:0;border-bottom:0}
  .bx::after{bottom:0;left:0;border-right:0;border-top:0}

  /* buttons: the only rounded corners on the page, besides nothing */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 18px;
    font:600 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;text-decoration:none;border:1px solid currentColor;border-radius:3px}
  .btn-solid{background:var(--accent);border-color:var(--accent);color:var(--paper)}
  .arrow{font-family:var(--sans);font-weight:700}

  /* ── header, laid over the hero ────────────────────────────────────── */
  header.top{position:absolute;top:0;left:0;right:0;z-index:6;display:flex;justify-content:space-between;align-items:flex-start;padding:18px 22px;gap:12px}
  .brand{font:700 16px/1.05 var(--serif);letter-spacing:-.01em;text-decoration:none;color:var(--paper)}
  header nav{display:none;gap:22px}
  header nav a{font:600 9.5px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;text-decoration:none;color:var(--muted)}
  header nav a:hover{color:var(--paper)}
  header .btn{display:none;color:var(--paper);border-color:rgba(245,240,230,.4);min-height:38px;padding:0 14px;font-size:10px}

  /* ── hero: an ink table with their prints on it ─────────────────────── */
  .hero{position:relative;min-height:100vh;min-height:100svh;padding:0;overflow:hidden;display:grid;place-items:center}
  .hero .thread{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:.5}
  .hero-mid{position:relative;z-index:3;padding:0 22px;width:100%;max-width:var(--wrap)}
  .hero h1{font-size:clamp(58px,17.5vw,156px);color:var(--accent);line-height:.9;display:flex;flex-direction:column;position:relative;
    padding-left:.14em;border-left:.075em solid var(--accent)}
  .hero h1 span:last-child{padding-left:.5em}
  .hero .pin{position:absolute;z-index:4;right:6%;top:-.35em;background:var(--white);color:var(--ink);font:600 8px/1 var(--mono);letter-spacing:.16em;
    text-transform:uppercase;padding:6px 8px;transform:rotate(-2deg);box-shadow:2px 2px 0 var(--accent)}
  .hero .sub{margin:26px 0 0 .35em;display:flex;flex-direction:column;align-items:flex-start;gap:14px}
  .hero .sub .k{color:var(--muted);letter-spacing:.18em}
  .hero .see{margin-top:10px;text-decoration:none;color:var(--paper);font:600 8.5px/1 var(--mono);letter-spacing:.2em;text-transform:uppercase}
  .hero .see b{color:var(--accent);font-weight:400}

  /* a print: paper edge, a hairline of accent, real depth on the table */
  .print{position:absolute;z-index:2;margin:0;background:var(--white);padding:6px;
    box-shadow:0 0 0 1px rgba(201,112,43,.55),0 26px 40px -12px rgba(0,0,0,.75)}
  .p1{top:7%;right:-7%;width:clamp(180px,52vw,400px);transform:rotate(5deg)}
  .p2{bottom:9%;left:-6%;width:clamp(150px,42vw,320px);transform:rotate(-6deg)}
  .p3{bottom:12%;right:-3%;width:clamp(104px,29vw,230px);transform:rotate(8deg)}
  .p4,.p5{display:none}
  .print.taped::before{content:"";position:absolute;z-index:2;top:-9px;left:50%;width:78px;height:22px;transform:translateX(-50%) rotate(-3deg);
    background:rgba(242,223,191,.72);box-shadow:0 1px 2px rgba(0,0,0,.25)}

  /* ── about, on paper ────────────────────────────────────────────────── */
  .about .quote{margin:34px 0 44px;font:italic 21px/1.45 var(--serif);max-width:32ch}
  .about .quote p{display:inline;background:linear-gradient(transparent 78%,rgba(201,112,43,.45) 78%,rgba(201,112,43,.45) 92%,transparent 92%);
    background-size:100% 100%}
  .about .quote cite{display:block;margin-top:12px;font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase;font-style:normal;color:var(--muted)}
  .about .polaroid{transform:rotate(1.6deg);margin:0 auto 0 0}

  /* polaroids: white frame, tape, a written caption; the only rounded corner is the print itself */
  .polaroid{position:relative;margin:0;background:var(--white);padding:10px 10px 14px;width:min(100%,340px);
    box-shadow:0 12px 26px -8px rgba(0,0,0,.35),0 1px 0 rgba(0,0,0,.06)}
  .polaroid .ph{border-radius:1px}
  .polaroid figcaption{margin-top:12px;text-align:center;font:italic 15px/1.3 var(--serif);color:var(--brown)}
  .tape{position:absolute;z-index:2;top:-11px;left:50%;width:84px;height:24px;transform:translateX(-50%) rotate(-2deg);
    background:rgba(242,223,191,.78);box-shadow:0 1px 2px rgba(0,0,0,.2)}

  /* ── the work: numbered rows, strips of prints ──────────────────────── */
  .work{padding-bottom:clamp(40px,8vw,80px)}
  .work .huge{font-size:clamp(70px,24vw,220px);margin:18px 0 0;letter-spacing:-.035em}
  .work .lede{margin:14px 0 0}
  .row{margin-top:clamp(56px,10vw,96px)}
  .row .pair{padding-top:14px;border-top:1px solid var(--line)}
  .strip{display:flex;align-items:flex-start;gap:22px;overflow-x:auto;scroll-snap-type:x mandatory;padding:26px 22px 34px;scrollbar-width:none;-webkit-overflow-scrolling:touch}
  .strip::-webkit-scrollbar{display:none}
  /* every print in a strip is the same height, like prints from one lab:
     a portrait comes out narrow, a landscape wide, and no card is ever
     stretched to its neighbour's height */
  .strip .polaroid{flex:0 0 auto;width:auto;scroll-snap-align:start}
  .strip .ph{height:clamp(170px,50vw,220px);width:auto}
  .strip .polaroid:nth-child(odd){transform:rotate(-1.5deg)}
  .strip .polaroid:nth-child(even){transform:rotate(1.4deg)}
  .strip .polaroid:nth-child(3n){transform:rotate(-.6deg)}

  /* ── section break: a full-bleed print, screened, behind a statement ── */
  .break{position:relative;min-height:88vh;min-height:88svh;display:grid;align-items:end;overflow:hidden;padding:clamp(72px,14vw,150px) 0 28px}
  /* a real halftone: the print, inverted and softened, multiplied by a soft
     dot per cell, then pushed to black-or-white and inverted back. The dot
     that survives is large where the print was bright and gone where it
     was dark — tone as dot size, the way a screened newspaper photo works. */
  .break .screen{position:absolute;inset:0;background:#fff;filter:contrast(28) invert(1);opacity:.6;overflow:hidden;isolation:isolate}
  .break .half{position:absolute;inset:0;width:100%;height:100%;filter:grayscale(1) contrast(.75) brightness(.7) invert(1) blur(1.2px)}
  .break .dots{position:absolute;inset:0;mix-blend-mode:multiply;
    background:radial-gradient(circle at center,#000 0,#000 .4px,#fff 2.3px) 0 0/4px 4px}
  .break .fade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(27,24,22,.5),rgba(27,24,22,.12) 38%,rgba(27,24,22,.95) 100%)}
  .break .wrap{position:relative;z-index:2;width:100%}
  .statement{margin:0;font:800 clamp(42px,12.5vw,110px)/.95 var(--sans);letter-spacing:-.04em;color:var(--paper)}
  .statement em{font-style:normal;color:var(--accent)}
  .break-foot{display:flex;justify-content:space-between;align-items:center;margin-top:clamp(40px,8vw,72px);gap:16px}
  .break-foot .brand{font-size:15px}
  .break-foot .btn{color:var(--paper);border-color:rgba(245,240,230,.45)}

  /* ── rates ──────────────────────────────────────────────────────────── */
  .rates .cards{display:grid;gap:18px;margin-top:22px}
  .rates .group{margin-top:clamp(40px,7vw,64px)}
  .card{color:var(--ink)}
  .card h3{font-size:clamp(26px,6.4vw,38px);margin:10px 0 10px}
  .card p{font-size:15.5px;line-height:1.55;color:#3b352f;margin-bottom:16px}
  .card .spec{display:flex;justify-content:space-between;align-items:baseline;gap:12px;border-top:1px solid var(--line);padding-top:12px}
  .price{font:700 15px/1.2 var(--mono);letter-spacing:.04em;color:var(--accent)}
  .dur{font:600 9.5px/1.5 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-align:right}

  /* spec tables, like a label on the back of a print */
  .table{margin:0;padding:0;list-style:none;border-top:1px solid var(--line)}
  .table li{display:flex;flex-direction:column;gap:3px;padding:13px 0;border-bottom:1px solid var(--line)}
  .table .k{color:var(--muted)}
  .table .v{font:600 12px/1.45 var(--mono);letter-spacing:.06em;text-transform:uppercase}
  .why{margin-top:clamp(56px,10vw,96px)}
  .why .frame{margin-top:22px}

  /* ── contact: the paper card on the ink ground ──────────────────────── */
  .contact .frame{padding:24px 18px 18px}
  .contact .card-ask{display:block;margin:16px 0 18px;background:var(--paper);color:var(--ink);text-decoration:none;padding:22px 20px 24px;position:relative}
  .contact .card-ask .k{display:flex;justify-content:space-between;color:var(--brown)}
  .contact .card-ask .big{display:block;margin-top:44px;font:700 clamp(19px,5.6vw,26px)/1.1 var(--mono);letter-spacing:-.01em;overflow-wrap:anywhere}
  .contact .cta-lede{margin:clamp(40px,8vw,64px) 0 26px;font-family:var(--serif);font-size:19px;line-height:1.55;max-width:56ch;color:var(--paper)}
  .links{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
  .links a{display:flex;align-items:center;gap:18px;padding:22px 0;border-bottom:1px solid var(--line);text-decoration:none;
    font:600 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .links a .arrow{margin-left:auto;font-size:16px}
  footer{margin-top:clamp(56px,10vw,96px);display:flex;flex-direction:column;gap:8px;font:600 9px/1.6 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  footer a{text-decoration:none}

  /* ── the phone bar: one action, always in reach ─────────────────────── */
  .bar{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;gap:10px;padding:10px 14px calc(10px + env(safe-area-inset-bottom));
    background:rgba(27,24,22,.94);backdrop-filter:blur(8px);color:var(--paper)}
  .bar .btn{flex:1}
  .bar .btn-ghost{border-color:rgba(245,240,230,.4);color:var(--paper)}
  body{padding-bottom:70px}

  /* motion: a settle, removed entirely when asked */
  .js .rise{opacity:0;transform:translateY(16px);animation:rise 1s var(--ease) forwards;animation-delay:calc(var(--i,0) * .09s)}
  @keyframes rise{to{opacity:1;transform:none}}
  .js .print{animation:settle 1.2s var(--ease) both;animation-delay:calc(var(--i,0) * .12s)}
  @keyframes settle{from{opacity:0;translate:0 18px}to{opacity:1;translate:0 0}}
  @media (prefers-reduced-motion:reduce){.js .rise,.js .print{animation:none;opacity:1;transform:none}html{scroll-behavior:auto}}

  /* ── wider: the prints spread out; the headline stays the size of a hand */
  @media (min-width:860px){
    header.top{padding:24px 32px;align-items:center}
    header nav{display:flex}
    header .btn{display:inline-flex}
    .hero{min-height:100vh}
    .hero h1{font-size:clamp(96px,10.5vw,156px)}
    .hero .pin{right:auto;left:62%;top:38%}
    .hero-mid{text-align:left;max-width:760px}
    .p1{top:7%;right:5%;width:380px;transform:rotate(4deg)}
    .p2{bottom:10%;left:7%;width:300px;transform:rotate(-4deg)}
    .p3{bottom:-3%;right:auto;left:46%;width:200px;transform:rotate(-10deg)}
    .p4{display:block;top:9%;left:6%;width:280px;transform:rotate(-7deg)}
    .p5{display:block;bottom:7%;right:9%;width:340px;transform:rotate(6deg)}
    .about .wrap{display:grid;grid-template-columns:1.2fr .8fr;gap:56px;align-items:start}
    .about .text{grid-column:1}
    .about .polaroid{grid-column:2;grid-row:1;margin-top:120px;transform:rotate(2.2deg)}
    .strip{flex-wrap:wrap;overflow:visible;max-width:var(--wrap);margin:0 auto;padding:30px 22px 20px;scroll-snap-type:none}
    .strip .ph{height:190px}
    .rates .cards{grid-template-columns:1fr 1fr;gap:22px}
    .rates .lede{font-size:19px}
    .why .frame{display:grid}
    .table li{flex-direction:row;justify-content:space-between;gap:24px;align-items:baseline}
    .table .v{text-align:right;max-width:60%}
    .contact .wrap{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start}
    .contact .cta-lede{margin-top:0}
    footer{grid-column:1 / -1;flex-direction:row;justify-content:space-between}
    .bar{display:none}
    body{padding-bottom:0}
  }
  @media (max-width:340px){.hero h1{font-size:56px}}
</style>
</head>
<body>

<header class="top">
  <a class="brand" href="#top">Gilman<br>Visual Media</a>
  <nav aria-label="Sections"><a href="#work">Work</a><a href="#rates">Rates</a><a href="#about">About</a><a href="#contact">Contact</a></nav>
  <a class="btn" href="#contact">Let’s connect</a>
</header>

<main>
<section class="hero ink" id="top">
  <svg class="thread" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <path d="M-40 780 C 300 760, 420 520, 700 470 S 1000 300, 1140 420 S 1180 700, 900 720 S 560 620, 640 470 S 900 330, 1120 360 S 1420 300, 1500 120" fill="none" stroke="rgba(245,240,230,.42)" stroke-width="1.2"/>
  </svg>
  ${print(rushmore, 'p1 taped', '3/2')}
  ${print(lift, 'p2', '1/1')}
  ${print(yellowLab, 'p3 taped', '1/1')}
  ${print(sunflowerWoman, 'p4', '3/2')}
  ${print(blackLab, 'p5 taped', '3/2')}
  <div class="hero-mid">
    <h1 class="rise" style="--i:1"><span>Real life,</span><span>preserved.</span><span class="pin">${esc(b.name)}</span></h1>
    <div class="sub">
      <span class="sticker paper-label rise" style="--i:3">Natural light · True colors · Honest emotion</span>
      <span class="k rise" style="--i:4">Photography / Real estate / Aerial</span>
      <a class="see rise" style="--i:6" href="#work">See the work <b>↓</b></a>
    </div>
  </div>
</section>

<section class="about paper" id="about">
  <div class="wrap">
    <div class="text">
      <span class="sticker">01 / About</span>
      <h2>Looking with <em>new eyes.</em></h2>
      <span class="sticker paper-label">Real moments, as they actually happen</span>
      <div class="prose" style="margin-top:30px">
        ${(b.about || '').split(/\n\n+/).map((p) => `<p>${esc(p)}</p>`).join('\n        ')}
      </div>
      <blockquote class="quote"><p>“${esc(b.quote?.text || '')}”</p><cite>— ${esc(b.quote?.by || '')}</cite></blockquote>
    </div>
    ${polaroid(sunflowerWoman, '3/2', 'in the sunflowers')}
  </div>
</section>

<section class="work paper-2" id="work">
  <div class="wrap">
    <span class="sticker">02 / The work</span>
    <h2 class="huge">The work</h2>
    <p class="lede">Portraits, weddings, pets and the open country — as it was in front of the lens.</p>
  </div>

  <div class="row">
    <div class="wrap"><div class="pair"><span class="n">01</span><span class="k">Portraits / Headshots</span></div><h3>Portraits</h3></div>
    <div class="strip">
      ${polaroid(tieDye, '3/2', 'among the sunflowers')}
      ${polaroid(lakeside, '3/4', 'at the lake')}
      ${polaroid(headshot, '3/2', 'an outdoor headshot')}
    </div>
  </div>

  <div class="row">
    <div class="wrap"><div class="pair"><span class="n">02</span><span class="k">Weddings / Milestones</span></div><h3>Weddings</h3></div>
    <div class="strip">
      ${polaroid(lift, '1/1', 'under the arch')}
      ${polaroid(close, '3/2', 'the two of them')}
      ${polaroid(archKiss, '1/1', 'the kiss')}
    </div>
  </div>

  <div class="row">
    <div class="wrap"><div class="pair"><span class="n">03</span><span class="k">Pets / Lifestyle</span></div><h3>Pets</h3></div>
    <div class="strip">
      ${polaroid(blackLab, '3/2', 'on the orange leash')}
      ${polaroid(yellowLab, '1/1', 'straight down the lens')}
      ${polaroid(cat, '3/2', 'on the cat tree')}
      ${polaroid(bwDog, '3/2', 'looking up')}
    </div>
  </div>

  <div class="row">
    <div class="wrap"><div class="pair"><span class="n">04</span><span class="k">Landscape / Open country</span></div><h3>Landscapes</h3></div>
    <div class="strip">
      ${polaroid(rushmore, '3/2', 'Mount Rushmore')}
      ${polaroid(badlands, '3/2', 'the Badlands')}
      ${polaroid(needles, '3/2', 'the Needles')}
      ${polaroid(bison, '3/2', 'a bison on the prairie')}
      ${polaroid(sunflowers, '3/2', 'sunflowers')}
    </div>
  </div>
</section>

<section class="break ink" aria-label="Natural light, true colors, honest emotion">
  ${badlands ? `<div class="screen" aria-hidden="true"><div class="half ph" style="--src:var(--ph${photos.indexOf(badlands)})"></div><div class="dots"></div></div>` : ''}
  <div class="fade" aria-hidden="true"></div>
  <div class="wrap">
    <p class="statement">Natural light.<br>True colors.<br><em>Honest emotion.</em></p>
    <div class="break-foot"><span class="brand">Gilman<br>Visual Media</span><a class="btn" href="#rates">Rates <span class="arrow">↓</span></a></div>
  </div>
</section>

<section class="rates paper" id="rates">
  <div class="wrap">
    <span class="sticker">03 / Rates</span>
    <h2>What we <em>shoot.</em></h2>
    <p class="lede">${esc(b.servicesLede)}</p>
    ${groups.map((g) => `
    <div class="group">
      <span class="sticker paper-label">${esc(g)}</span>
      <div class="cards">
        ${services.filter((s) => s.group === g).map(card).join('\n        ')}
      </div>
    </div>`).join('')}

    <div class="why">
      <div class="pair"><span class="n">04</span><span class="k">Why choose us</span></div>
      <div class="frame"><span class="bx" aria-hidden="true"></span>
        <ul class="table">
          ${why.map(([k, v]) => `<li><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></li>`).join('\n          ')}
        </ul>
      </div>
    </div>
  </div>
</section>

<section class="contact ink" id="contact">
  <div class="wrap">
    <div class="frame"><span class="bx" aria-hidden="true"></span>
      <div class="pair"><span class="k">Contact us</span><span class="k">Let’s connect</span></div>
      <a class="card-ask" href="${MESSAGE}" rel="noopener">
        <span class="k">Send a message <span class="arrow">↗</span></span>
        <span class="big">@gilmanvisualmedia</span>
      </a>
      <ul class="table">
        ${when.map(([k, v]) => `<li><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></li>`).join('\n        ')}
      </ul>
    </div>
    <div>
      <p class="cta-lede">${esc(b.ctaHeading)} ${esc(b.ctaLede)}</p>
      <ol class="links">
        <li><a href="${INSTAGRAM}" rel="noopener"><span class="n">01</span>Instagram<span class="arrow">↗</span></a></li>
        <li><a href="${FORM}" rel="noopener"><span class="n">02</span>Contact form<span class="arrow">↗</span></a></li>
        <li><a href="${PORTFOLIO}" rel="noopener"><span class="n">03</span>Full portfolio<span class="arrow">↗</span></a></li>
      </ol>
    </div>
    <footer>
      <span>Photography / Real estate / Aerial</span>
      <span>${esc(b.name)} © ${new Date().getFullYear()}</span>
      <span>Site by McManus Web Co.</span>
    </footer>
  </div>
</section>
</main>

<div class="bar">
  <a class="btn btn-solid" href="${MESSAGE}" rel="noopener">Send a message</a>
  <a class="btn btn-ghost" href="#rates">Rates</a>
</div>

</body>
</html>
`;
}

module.exports = { render };
