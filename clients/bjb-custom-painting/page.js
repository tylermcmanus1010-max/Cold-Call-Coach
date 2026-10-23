// The page for BJB Custom Painting, built by hand against DESIGN.md.
//
// Concept (rule zero): the fan deck. A painter's native object is the colour
// chip — a swatch with a name and a number, fanned out on the kitchen table
// while the homeowner decides. So his services are chips: each one a card
// with a code, a colour and a line of plain English, and the colours are not
// decoration — every one is lifted from a photograph of his own work on this
// page (the terracotta bedroom, the blue deck, the yellow siding, primed
// drywall). Tap chips to build an estimate request; it goes as a text.
//
// His photographs are prints held down with painter's blue tape, which is
// what a painter has instead of a polaroid's beige tape. Two grounds: a
// charcoal drop cloth and canvas. The headline wears the tape blue; his
// signage red appears once, on the sticker.
//
// Everything on it is his: the services off his own site (decks from his own
// gallery, garage epoxy from a customer's review), two Google reviews quoted
// verbatim, "over a decade" and "painting and drywall" from his About page,
// the number on his yard signs, the email he prints, eight of his own
// photographs — looked at one by one; the stock ones on his old site are
// kept on file and never shown. Hours are not stated because only a Friday
// close and a Saturday open were visible. Nothing here is invented.
//
// Self-contained: system fonts, an inline SVG grain, photos as data URIs.
// The estimate chips are checkboxes, so it works with JavaScript off; the
// script only writes the chosen services into the text. Judged at 390px.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// Same grain as tools/render.js: felt, not seen.
const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .17"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

function render(b) {
  const digits = String(b.phone || '').replace(/[^0-9]/g, '');
  const tel = `tel:+1${digits}`;
  const name = b.name || 'BJB Custom Painting';
  const area = (b.serviceArea || []).join(' · ');

  // Photographs, by what is in them. Only `work` may sit under a heading that
  // says so; `other` is on file and never shown.
  const photos = (b.photos || []).filter((p) => p && p.src);
  const work = photos.filter((p) => p.kind === 'work');
  // Only photographs the page shows are written into it. The four kept on
  // file and never shown were a hundred kilobytes of CSS variables nobody saw,
  // and the page failed its own speed check carrying them.
  const vars = work.map((p, i) => `--ph${i}:url("${p.src}")`).join(';');
  // The caption is the homeowner's description; the alt on the record is ours
  // and once leaked "the same deck on his Google listing" into a screen reader.
  const img = (p, ratio) => !p ? '' :
    `<span class="ph" role="img" aria-label="${esc(p.caption || '')}" style="--src:var(--ph${work.indexOf(p)});aspect-ratio:${ratio || '4/3'}"></span>`;
  const pick = (re) => work.find((p) => re.test(p.alt || '')) || null;
  const deck = pick(/deck/i);
  const fireplace = pick(/fireplace/i);
  const exterior = pick(/exterior/i);
  const hero = deck || exterior || work[0];
  const strip = work.filter((p) => p !== hero);

  const svc = b.services || [];
  const reviews = (b.reviews || []).filter((r) => r.text);
  const rating = b.rating || {};

  // The text a tap composes. The wording is a tradesman's: nobody "books"
  // a drywall repair, they ask when you can come out.
  const smsDefault = `Hi ${name}, could I get a free estimate? When could you come out?`;
  const sms = (body) => `sms:+1${digits}&body=${encodeURIComponent(body)}`;
  const mail = (body) => `mailto:${esc(b.email || '')}?subject=${encodeURIComponent('Free estimate')}&body=${encodeURIComponent(body)}`;

  const schema = {
    '@context': 'https://schema.org', '@type': 'HousePainter', name,
    telephone: `+1${digits}`, email: b.email || undefined,
    areaServed: (b.serviceArea || []).map((a) => ({ '@type': 'Place', name: a })),
    sameAs: b.social ? Object.values(b.social) : undefined,
    aggregateRating: rating.value ? { '@type': 'AggregateRating', ratingValue: rating.value, reviewCount: rating.count } : undefined,
  };

  const chip = (s) => `
    <label class="chip" style="--sw:${esc(s.swatch)}">
      <input type="checkbox" name="svc" value="${esc(s.name)}">
      <span class="sw" aria-hidden="true"></span>
      <span class="body">
        <span class="pair"><span class="n">BJB&#8209;${esc(s.code)}</span><span class="k">${esc(s.group)}</span></span>
        <span class="nm">${esc(s.name)}</span>
        <span class="ds">${esc(s.desc)}</span>
      </span>
      <span class="tape pick" aria-hidden="true"></span>
    </label>`;

  const print = (p, i) => `
    <figure class="print">
      <span class="tape" aria-hidden="true"></span>
      ${img(p, '4/3')}
      <figcaption class="pair"><span class="n">${String(i + 2).padStart(2, '0')}</span><span class="k">${esc(p.caption || '')}</span></figcaption>
    </figure>`;

  const review = (r, i) => `
    <li class="rev">
      <div class="pair"><span class="n">${String(i + 1).padStart(2, '0')}</span><span class="k">${esc(r.source)}${r.stars ? ' · ' + '★'.repeat(r.stars) : ''}</span></div>
      <blockquote>“${esc(r.text)}”</blockquote>
      <cite>— ${esc(r.name)}${/translated/i.test(r.note || '') ? ' <span class="k">(translated from Spanish)</span>' : ''}</cite>
    </li>`;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(name)} — Painting &amp; drywall, Sussex County, DE</title>
<meta name="description" content="${esc(name)}: interior and exterior painting, cabinets, decks, drywall and garage floor epoxy across Sussex County and Middletown, Delaware. Free estimates. Call or text ${esc(b.phone)}.">
<meta property="og:title" content="${esc(name)}">
<meta property="og:description" content="Painting and drywall across Sussex County, DE. Free estimates — call or text ${esc(b.phone)}.">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#17191c"/><rect x="6" y="9" width="20" height="8" fill="#2d74c4"/><rect x="6" y="19" width="20" height="4" fill="#efe8da"/></svg>')}">
<script type="application/ld+json">${JSON.stringify(schema)}</script>
<style>
  :root{
    --ink:#17191c; --ink-2:#1e2125;
    --paper:#efe8da; --paper-2:#e5dcc9; --white:#faf7f1;
    --tape:#2d74c4; --tape-2:#5b9be0; --red:#b8322a;
    --brown:#5e5449;
    --line:rgba(23,25,28,.16); --muted:#6b6358; --grid:rgba(30,24,16,.05);
    --grain:url("${GRAIN}");
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --wrap:1080px;
  }
  :root{${vars}}
  .ph{display:block;width:100%;background:var(--src) center/cover no-repeat}
  *{box-sizing:border-box}
  html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
  body{margin:0;color:var(--ink);background:var(--paper);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit}
  p{margin:0 0 16px}
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}

  /* ── grounds: drop cloth and canvas, grain and a faint grid on both ── */
  .ink,.paper,.paper-2{background-image:var(--grain),
    linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:220px 220px,36px 36px,36px 36px}
  .paper{background-color:var(--paper)}
  .paper-2{background-color:var(--paper-2)}
  .ink{background-color:var(--ink);color:var(--paper);--grid:rgba(255,255,255,.045);--line:rgba(255,255,255,.16);--muted:rgba(239,232,218,.6)}
  section{padding:clamp(72px,14vw,150px) 0;scroll-margin-top:12px}

  /* ── three scales of type, far apart ── */
  .k,.n{font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .n{color:var(--tape)}
  .ink .n{color:var(--tape-2)}
  .pair{display:flex;justify-content:space-between;gap:16px;align-items:baseline;color:var(--muted)}
  h2{font:400 clamp(44px,13vw,112px)/.92 var(--serif);letter-spacing:-.025em;margin:0 0 .35em;text-wrap:balance}
  h2 em{font-style:italic;color:var(--tape)}
  .ink h2 em{color:var(--tape-2)}
  .lede{font-size:18px;line-height:1.55;max-width:56ch;color:var(--brown)}
  .ink .lede{color:var(--muted)}
  .prose{font-family:var(--serif);font-size:18.5px;line-height:1.6;max-width:62ch}

  /* stickers: his signage red, hard offset shadow, stuck on at an angle */
  .sticker{display:inline-block;max-width:100%;background:var(--red);color:var(--white);font:700 10px/1.45 var(--mono);
    letter-spacing:.14em;text-transform:uppercase;text-wrap:balance;padding:7px 11px 6px;box-shadow:3px 3px 0 var(--ink);
    transform:rotate(-1.6deg);transform-origin:left center}
  .ink .sticker{box-shadow:3px 3px 0 var(--paper)}

  /* corner brackets, never rounded cards */
  .card{position:relative;padding:22px 18px 20px}
  .card::before,.card::after,.bx::before,.bx::after{content:"";position:absolute;width:14px;height:14px;border:1px solid currentColor;opacity:.7}
  .card::before{top:0;left:0;border-right:0;border-bottom:0}
  .card::after{bottom:0;right:0;border-left:0;border-top:0}
  .bx::before{top:0;right:0;border-left:0;border-bottom:0}
  .bx::after{bottom:0;left:0;border-right:0;border-top:0}

  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:46px;padding:0 18px;
    border:1px solid currentColor;text-decoration:none;font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:inherit;background:transparent}
  .btn-solid{background:var(--tape);border-color:var(--tape);color:var(--white)}
  .btns{display:flex;flex-wrap:wrap;gap:10px}
  a:focus-visible,button:focus-visible,input:focus-visible+.sw{outline:2px solid var(--tape-2);outline-offset:3px}

  /* painter's tape: the one object that is on every print */
  .tape{position:absolute;z-index:2;top:-11px;left:50%;width:92px;height:24px;transform:translateX(-50%) rotate(-2deg);
    background:rgba(45,116,196,.82);box-shadow:0 1px 2px rgba(0,0,0,.25)}
  .tape::after{content:"";position:absolute;inset:0;background:var(--grain);opacity:.5}

  /* ── nav ── */
  .nav{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 22px;
    background:rgba(23,25,28,.92);color:var(--paper);backdrop-filter:blur(8px);border-bottom:1px solid rgba(255,255,255,.08)}
  .brand{text-decoration:none;color:var(--paper);display:flex;align-items:baseline;gap:8px}
  .brand b{font:700 18px/1 var(--serif);letter-spacing:.06em}
  .brand span{font:400 italic 14px/1 var(--serif);color:var(--muted)}
  .nav .btn{min-height:40px;padding:0 14px;font-size:10px}

  /* ── hero: drop cloth, the headline in tape blue, the deck as a taped print ── */
  .hero{position:relative;padding:clamp(56px,10vw,110px) 0 clamp(40px,8vw,80px);overflow:hidden}
  .hero .wrap{display:grid;gap:34px}
  .hero h1{font:400 clamp(50px,15.5vw,108px)/.9 var(--serif);letter-spacing:-.03em;margin:22px 0 0;color:var(--tape-2);display:flex;flex-direction:column;text-wrap:balance}
  .hero h1 em{font-style:italic;color:var(--paper);padding-left:.4em}
  .hero .sub{margin-top:22px;max-width:46ch}
  .hero .btns{margin-top:26px}
  .hero .print{position:relative;margin:30px 0 0;background:var(--white);padding:9px 9px 12px;
    transform:rotate(-1.4deg);box-shadow:10px 10px 0 var(--tape),0 20px 40px -18px rgba(0,0,0,.6)}
  .hero .print figcaption{margin-top:10px;color:var(--ink)}
  .hero .print .n{color:var(--tape)}

  /* highlights: three numbers on a hairline */
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:10px;padding-top:18px;border-top:1px solid var(--line)}
  .stats b{display:block;font:400 clamp(24px,7vw,34px)/1 var(--serif);color:var(--tape-2);letter-spacing:-.02em}
  .stats .k{display:block;margin-top:6px;white-space:normal}

  /* ── the work: prints taped to canvas, numbered ── */
  .work .strip{display:flex;gap:26px;overflow-x:auto;scroll-snap-type:x mandatory;padding:34px 22px 28px;margin:0 -22px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .work .strip::-webkit-scrollbar{display:none}
  .print{position:relative;flex:0 0 min(78vw,330px);margin:0;background:var(--white);padding:9px 9px 12px;scroll-snap-align:start;
    box-shadow:0 12px 26px -8px rgba(0,0,0,.35),0 1px 0 rgba(0,0,0,.06)}
  .print figcaption{margin-top:10px}
  .work .print:nth-child(odd){transform:rotate(-1.3deg)}
  .work .print:nth-child(even){transform:rotate(1.2deg)}

  /* ── the deck: services as paint chips ── */
  .deck .chips{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin-top:30px}
  .chip{position:relative;display:flex;flex-direction:column;background:var(--white);cursor:pointer;min-height:100%;
    box-shadow:0 10px 22px -10px rgba(0,0,0,.35),0 1px 0 rgba(0,0,0,.06);transform:rotate(-.6deg);transition:transform .15s ease,box-shadow .15s ease}
  .chip:nth-child(even){transform:rotate(.7deg)}
  .chip:nth-child(3n){transform:rotate(-1.1deg)}
  .chip input{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
  .chip .sw{display:block;height:88px;background:var(--sw);border-bottom:1px solid rgba(0,0,0,.08)}
  .chip .body{display:flex;flex-direction:column;gap:6px;padding:12px 12px 14px}
  .chip .nm{font:400 20px/1.15 var(--serif);letter-spacing:-.01em;color:var(--ink)}
  .chip .ds{font-size:13px;line-height:1.45;color:var(--brown)}
  .chip .tape.pick{display:none;top:-10px;left:auto;right:10px;transform:rotate(6deg);width:70px}
  .chip:has(input:checked){transform:rotate(0) translateY(-3px);box-shadow:0 0 0 2px var(--tape),0 14px 26px -10px rgba(0,0,0,.4)}
  .chip:has(input:checked) .tape.pick{display:block}
  .chip:has(input:checked) .nm{color:var(--tape)}
  .deck .how{margin-top:16px;color:var(--muted)}

  /* ── the estimate: what you picked, and the three ways to send it ── */
  .ask-bar{margin-top:34px;display:grid;gap:14px}
  .picked{min-height:24px;font:italic 17px/1.5 var(--serif);color:var(--muted)}
  .picked b{font-style:normal;color:var(--paper);font-family:var(--sans);font-weight:600}

  /* ── reviews: numbered rows on the drop cloth ── */
  .revs{list-style:none;margin:30px 0 0;padding:0}
  .rev{padding:22px 0;border-top:1px solid var(--line)}
  .rev blockquote{margin:12px 0 10px;font:400 clamp(21px,5.4vw,30px)/1.3 var(--serif);letter-spacing:-.01em;text-wrap:pretty}
  .rev cite{font-style:normal;color:var(--muted);font-size:14px}
  .ink .rev .k{color:var(--muted)}

  /* ── about: one taped print, and four true things ── */
  .about .wrap{display:grid;gap:34px}
  .about .print{width:min(100%,340px);flex:none;transform:rotate(1.6deg)}
  .about .print figcaption{font:italic 15px/1.3 var(--serif);color:var(--brown);text-align:center}
  .facts{list-style:none;margin:20px 0 0;padding:0;display:grid;gap:0}
  .facts li{display:flex;gap:16px;align-items:baseline;padding:12px 0;border-top:1px solid var(--line);font-size:16px}
  .facts li:last-child{border-bottom:1px solid var(--line)}

  /* ── the ask: a paper card on the drop cloth, the most confident moment ── */
  .ask .card{background:var(--white);color:var(--ink);padding:28px 22px 24px;max-width:560px;
    box-shadow:0 22px 40px -16px rgba(0,0,0,.6);transform:rotate(-.8deg)}
  .ask .card h3{font:400 clamp(34px,9vw,54px)/1 var(--serif);letter-spacing:-.025em;margin:8px 0 12px}
  .ask .card .btns{margin-top:18px}
  .ask .card .btn-solid{color:var(--white)}
  .spec{margin:22px 0 0;padding:0;list-style:none}
  .spec li{display:flex;justify-content:space-between;gap:16px;padding:9px 0;border-top:1px solid var(--line);font:600 10px/1.5 var(--mono);letter-spacing:.12em;text-transform:uppercase}
  .spec li span:last-child{color:var(--tape);text-align:right}

  footer{padding:30px 22px 110px;color:var(--muted);font-size:13px}
  footer a{color:var(--paper)}

  /* sticky bar: the two things a phone is for */
  .bar{position:fixed;left:0;right:0;bottom:0;z-index:30;display:flex;gap:8px;padding:10px 12px;
    padding-bottom:max(10px,env(safe-area-inset-bottom));background:rgba(23,25,28,.94);backdrop-filter:blur(8px);border-top:1px solid rgba(255,255,255,.1)}
  .bar .btn{flex:1;color:var(--paper)}
  .bar .btn-solid{color:var(--white)}

  @media (min-width:880px){
    .hero .wrap{grid-template-columns:1.1fr .9fr;align-items:center}
    .hero .print{margin-top:0;transform:rotate(1.2deg);grid-column:2;grid-row:1/3}
    .hero .stats{grid-column:1;margin-top:10px}
    .work .strip{flex-wrap:wrap;overflow:visible;margin:0;padding:34px 0 0}
    .print{flex:0 0 calc(33.333% - 18px)}
    .deck .chips{grid-template-columns:repeat(4,1fr);gap:18px}
    .about .wrap{grid-template-columns:1fr 1fr;align-items:start}
    .bar{display:none}
    footer{padding-bottom:40px}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}}
</style>
</head>
<body>

<nav class="nav">
  <a class="brand" href="#top"><b>BJB</b><span>Custom Painting</span></a>
  <a class="btn" href="${tel}">Call ${esc(b.phone)}</a>
</nav>

<header class="hero ink" id="top">
  <div class="wrap">
    <div>
      <span class="sticker">Painting &amp; drywall · ${esc(area)}</span>
      <h1><span>Walls, trim, decks</span><em>&amp; drywall.</em></h1>
      <p class="lede sub">${esc(b.about)} Free estimates — call or text, and we come out.</p>
      <div class="btns">
        <a class="btn btn-solid" href="${tel}">Call now</a>
        <a class="btn" href="#deck">Build an estimate ↓</a>
      </div>
    </div>
    ${hero ? `<figure class="print"><span class="tape" aria-hidden="true"></span>${img(hero, '4/3')}<figcaption class="pair"><span class="n">01</span><span class="k">${esc(hero.caption || '')}</span></figcaption></figure>` : ''}
    <div class="stats">
      ${(b.highlights || []).map((h) => `<div><b>${esc(h.value)}</b><span class="k">${esc(h.label)}</span></div>`).join('')}
    </div>
  </div>
</header>

${strip.length ? `
<section class="work paper" id="work">
  <div class="wrap">
    <span class="k">Recent work · his own photographs</span>
    <h2>The <em>work.</em></h2>
    <p class="lede">Rooms, exteriors and decks across Sussex County. Every picture here is a job he did.</p>
  </div>
  <div class="wrap"><div class="strip">${strip.map(print).join('')}</div></div>
</section>` : ''}

<section class="deck paper-2" id="deck">
  <div class="wrap">
    <span class="k">Services · tap to add to your estimate</span>
    <h2>Pick your <em>chips.</em></h2>
    <p class="lede">Every colour on these chips is from a job on this page. Pick what you need and send it as a text — no forms, no account.</p>
    <form id="est" class="chips" onsubmit="return false">${svc.map(chip).join('')}</form>
    <p class="how k">Prices depend on the room, the surface and the prep. That is what the free visit is for.</p>
  </div>
</section>

<section class="ink" id="estimate">
  <div class="wrap">
    <span class="k">Your estimate</span>
    <h2>Send it <em>over.</em></h2>
    <div class="ask-bar">
      <p class="picked" id="picked">Nothing picked yet — a plain “when could you come out?” is fine too.</p>
      <div class="btns">
        <a class="btn btn-solid" id="sms" href="${sms(smsDefault)}">Text the request</a>
        <a class="btn" href="${tel}">Call ${esc(b.phone)}</a>
        ${b.email ? `<a class="btn" id="mail" href="${mail(smsDefault)}">Email instead</a>` : ''}
      </div>
    </div>
  </div>
</section>

${reviews.length ? `
<section class="ink" id="reviews" style="padding-top:0">
  <div class="wrap">
    <div class="pair"><span class="k">${esc(rating.value || '')} on ${esc(rating.source || 'Google')} · ${esc(rating.count || '')} reviews</span><span class="k">quoted as written</span></div>
    <h2 style="margin-top:14px">In their <em>words.</em></h2>
    <ol class="revs">${reviews.map(review).join('')}</ol>
  </div>
</section>` : ''}

<section class="about paper" id="about">
  <div class="wrap">
    <div>
      <span class="k">About</span>
      <h2>Over a <em>decade.</em></h2>
      <p class="prose">${esc(b.about)}</p>
      <ul class="facts">
        <li><span class="n">01</span><span>Painting and drywall, inside and out</span></li>
        <li><span class="n">02</span><span>Homes and businesses</span></li>
        <li><span class="n">03</span><span>${esc(area)}</span></li>
        <li><span class="n">04</span><span>Free estimates — we come to you</span></li>
      </ul>
    </div>
    ${fireplace ? `<figure class="print"><span class="tape" aria-hidden="true"></span>${img(fireplace, '4/3')}<figcaption>${esc(fireplace.caption || '')}</figcaption></figure>` : ''}
  </div>
</section>

<section class="ask ink" id="contact">
  <div class="wrap">
    <span class="k">Get in touch</span>
    <div class="card bx">
      <span class="k">Free estimate</span>
      <h3>Tell us what needs painting.</h3>
      <p>Call or text ${esc(b.phone)} and say roughly what the job is. We come out, look at it properly, and put a number on it. No charge for the visit.</p>
      <div class="btns">
        <a class="btn btn-solid" href="${tel}">Call</a>
        <a class="btn" href="${sms(smsDefault)}">Text</a>
        ${b.email ? `<a class="btn" href="mailto:${esc(b.email)}">Email</a>` : ''}
      </div>
      <ul class="spec">
        <li><span>Estimates</span><span>Free</span></li>
        <li><span>Area</span><span>${esc(area)}</span></li>
        <li><span>Reach us</span><span>Call or text</span></li>
      </ul>
    </div>
  </div>
</section>

<footer class="ink">
  <div class="wrap">
    <div class="pair"><span>${esc(name)} · ${esc(area)}</span>${b.social && b.social.facebook ? `<a href="${esc(b.social.facebook)}" rel="noopener">Facebook ↗</a>` : ''}</div>
  </div>
</footer>

<div class="bar">
  <a class="btn btn-solid" href="${tel}">Call</a>
  <a class="btn" href="#deck">Estimate</a>
</div>

<script>
(function () {
  var form = document.getElementById('est');
  var picked = document.getElementById('picked');
  var sms = document.getElementById('sms');
  var mail = document.getElementById('mail');
  if (!form || !picked || !sms) return;
  var NAME = ${JSON.stringify(name)};
  var TO = ${JSON.stringify('+1' + digits)};
  var EMAIL = ${JSON.stringify(b.email || '')};
  function update() {
    var names = [].slice.call(form.querySelectorAll('input:checked')).map(function (i) { return i.value; });
    var body = names.length
      ? 'Hi ' + NAME + ', could I get a free estimate for: ' + names.join(', ') + '. When could you come out?'
      : 'Hi ' + NAME + ', could I get a free estimate? When could you come out?';
    sms.href = 'sms:' + TO + '&body=' + encodeURIComponent(body);
    if (mail && EMAIL) mail.href = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent('Free estimate') + '&body=' + encodeURIComponent(body);
    picked.innerHTML = names.length
      ? '<b>' + names.length + ' picked:</b> ' + names.map(function (n) { var d = document.createElement('span'); d.textContent = n; return d.innerHTML; }).join(', ')
      : 'Nothing picked yet \\u2014 a plain \\u201cwhen could you come out?\\u201d is fine too.';
  }
  form.addEventListener('change', update);
  update();
})();
</script>
</body>
</html>`;
}

module.exports = { render };
