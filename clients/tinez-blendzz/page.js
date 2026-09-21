// The page for Tinezz Blendzz, built by hand against DESIGN.md.
//
// Concept (rule zero): the price board on the barbershop wall. A barber's
// native objects are the board behind the chair, the clipper guards on the
// station, and the cuts themselves — so the menu is a gold-lettered board
// on dark green, the section breaks are a guard scale (the fade as a
// graphic: seven ticks from #0 to #4), and the work is his cuts hung on a
// black wall in gold hairline frames. Colour encodes: gold is a fade, green
// is a design, cream is a beard; on the menu, gold is a haircut and green
// is a trim.
//
// The brief, in his words: clean but gritty, black, gold and dark green,
// luxury street barbershop, sharp fades, clippers, trophies showing the
// journey, professional but true to the business. Gritty is the grain and
// the halftone; luxury is the Didot wordmark in foil; street is the black,
// the stickers and the tight mono labels. The "journey" wall carries only
// what is verified — his own bio and Instagram, and Booksy — and grows
// from business.json (`journey`) as he supplies trophies and certificates.
// Nothing about the business is invented here.
//
// Self-contained: system fonts, inline SVG grain, photos as data URIs.
// Works with JavaScript off. Judged at 390px.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const digits = (s) => String(s || '').replace(/\D/g, '');

// The same grain as tools/render.js, a touch heavier: on black it reads as
// specks of light. Felt, not seen, but felt a little more here — the brief
// said gritty.
const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .2"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

// A clipper guard scale: seven ticks that grow from a #0 to a #4, the way
// a fade steps up the head. A design element, not a claim.
const GUARDS = ['0', '½', '1', '1½', '2', '3', '4'];

function render(b) {
  const a = b.address || {};
  const tel = digits(b.phone);
  const booking = b.booking?.url || '';
  const instagram = b.social?.instagram || '';
  const handle = instagram ? '@' + instagram.replace(/\/+$/, '').split('/').pop() : '';
  const mapsQ = encodeURIComponent([a.street, a.city, a.state, a.zip].filter(Boolean).join(', '));
  const maps = a.street ? `https://www.google.com/maps/search/?api=1&query=${mapsQ}` : '';

  const photos = (b.photos || []).filter((p) => p && p.src);
  const work = photos.filter((p) => p.kind === 'work');
  const portrait = photos.find((p) => p.kind === 'team') || null;
  // Every photo is written into the page once, as a CSS variable; the hero
  // and the halftone break reuse two of them, and a data URI twice is a
  // quarter-megabyte for nothing.
  const vars = photos.map((p, i) => `--ph${i}:url("${p.src}")`).join(';');
  const img = (p, ratio) => !p ? '' :
    `<span class="ph" role="img" aria-label="${esc(p.alt)}" style="--src:var(--ph${photos.indexOf(p)});aspect-ratio:${ratio || '4/5'}"></span>`;

  // What a cut is, read off its own alt text. Gold = fade, green = design,
  // cream = beard. The label is the category, not a claim about quality.
  const kindOf = (p) => /design/i.test(p.alt) ? ['design', 'Design']
    : /fade|taper/i.test(p.alt) ? ['fade', 'Fade'] : ['beard', 'Beard'];
  // Short labels for the wall, each a plainer cut of its own alt text.
  const LABELS = [
    [/Curls on top/, 'Curls, low fade, beard'], [/freehand line/, 'Skin fade, line design'],
    [/High skin fade/, 'High skin fade, beard'], [/Taper fade/, 'Taper fade, full beard'],
    [/Textured fringe/, 'Fringe, temple design'], [/lightning/, 'Crop, lightning at the nape'],
    [/star design/, 'Crop, star at the nape'], [/clippers in hand/, 'Mid-cut, clippers in hand'],
  ];
  const label = (p) => (LABELS.find(([re]) => re.test(p.alt || '')) || [])[1] || p.alt;
  const pick = (re) => work.find((p) => re.test(p.alt || '')) || work[0] || null;
  const hero = pick(/Curls on top/);
  const kinds = [['fade', 'Fade'], ['design', 'Design'], ['beard', 'Beard']].filter(([c]) => work.some((p) => kindOf(p)[0] === c));
  const legendLede = { fade: 'Gold is a fade', design: 'green is a design', beard: 'cream is beard work' };
  const legendLedeText = kinds.map(([c], i) => (i ? legendLede[c] : legendLede[c])).join(', ') + '.';
  const clippers = pick(/clippers in hand/);
  const frame = (p, i) => !p ? '' : `
      <figure class="cut ${kindOf(p)[0]} rise" style="--i:${i}">
        <span class="bx" aria-hidden="true"></span>
        ${img(p, '4/5')}
        <figcaption><span class="tag">${kindOf(p)[1]}</span><span class="cap">${esc(label(p))}</span></figcaption>
      </figure>`;

  const services = (b.services || []).filter((s) => s && String(s.name || '').trim());
  const groups = [...new Set(services.map((s) => s.group || 'Services'))];
  const row = (s) => `
        <li class="row">
          <div class="line"><span class="name">${esc(s.name)}</span><span class="dots" aria-hidden="true"></span><span class="price">${esc(s.price)}</span></div>
          ${s.desc || s.duration ? `<div class="meta">${s.duration ? `<span class="dur">${esc(s.duration)}</span>` : ''}${s.desc ? `<span class="desc">${esc(s.desc)}</span>` : ''}</div>` : ''}
        </li>`;

  const hours = (b.hours || []).filter((h) => h && h.days);
  const reviews = (b.reviews || []).filter((r) => r && String(r.text || '').trim());
  const rating = b.rating || {};
  const years = (String(b.about || '').match(/(\d+)\s+years?/i) || [])[1];

  // The journey wall. Plaques for what is on record; anything Tinez sends
  // later (trophies, certificates, a date) goes in business.json `journey`
  // as {value,label,note?} and lands here without touching this file.
  const journey = (b.journey && b.journey.length) ? b.journey : [
    years ? { value: `${years} yrs`, label: 'behind the chair' } : null,
    rating.value ? { value: `${rating.value} ★`, label: `${rating.count} reviews on ${rating.source || 'Booksy'}` } : null,
    { value: 'Sensory Safe', label: 'certified barber' },
    { value: 'ABBC', label: 'Anti Broke Barbers Club ambassador' },
    { value: 'Colleywood Cuts', label: `in the chair at ${a.street || 'Colley Ave'}` },
  ].filter(Boolean);

  const ld = {
    '@context': 'https://schema.org',
    '@type': ['HairSalon', 'LocalBusiness'],
    name: b.name,
    description: b.subhead,
    url: b.liveUrl || undefined,
    telephone: tel ? '+1' + tel : undefined,
    priceRange: b.priceRange || undefined,
    address: a.street ? { '@type': 'PostalAddress', streetAddress: a.street, addressLocality: a.city, addressRegion: a.state, postalCode: a.zip, addressCountry: 'US' } : undefined,
    openingHours: hours.map((h) => h.schema).filter(Boolean),
    aggregateRating: rating.value ? { '@type': 'AggregateRating', ratingValue: rating.value, reviewCount: rating.count, bestRating: '5' } : undefined,
    sameAs: [instagram, booking].filter(Boolean),
    makesOffer: services.map((s) => {
      const low = Number((String(s.price).match(/\$([\d,]+)/) || [])[1]?.replace(/,/g, ''));
      return { '@type': 'Offer', name: s.name, category: s.group,
        priceSpecification: low ? { '@type': 'PriceSpecification', price: low, priceCurrency: 'USD' } : undefined };
    }),
  };
  const jsonld = JSON.stringify(ld, (k, v) => (v === undefined ? undefined : v), 2).replace(/</g, '\\u003c');

  const favicon = 'data:image/svg+xml,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#0b0b0b"/><text x="16" y="23" font-size="18" font-family="Didot,Georgia,serif" font-weight="700" fill="#c9a44c" text-anchor="middle">TB</text></svg>`);

  const guards = `<div class="guards" aria-hidden="true">${GUARDS.map((g, i) => `<span style="--h:${i + 1}"><i></i><b>${g}</b></span>`).join('')}</div>`;

  const title = `${b.name} — Barber in Ghent, Norfolk · Fades, beards, designs`;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(b.subhead)}">
<meta property="og:title" content="${esc(b.name)}">
<meta property="og:description" content="${esc(b.headline)} ${esc(b.tagline)}">
<meta property="og:type" content="website">
${b.liveUrl ? `<meta property="og:url" content="${esc(b.liveUrl)}">` : ''}
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#0b0b0b">
<link rel="icon" href="${favicon}">
<script type="application/ld+json">
${jsonld}
</script>
<script>document.documentElement.className+=' js';</script>
<style>
  :root{
    --black:#0b0b0b;
    --black-2:#121212;
    --green:#0f2e22;
    --green-2:#143a2a;
    --green-line:#2c6a4a;
    --gold:#c9a44c;
    --gold-2:#e6c56d;
    --gold-3:#8a6a22;
    --cream:#f1e9d6;
    --muted:rgba(241,233,214,.6);
    --line:rgba(201,164,76,.32);
    --grain:url("${GRAIN}");
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --display:Didot,"Bodoni 72","Bodoni MT","Libre Bodoni","Playfair Display",Georgia,"Times New Roman",serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --wrap:1080px;
    --ease:cubic-bezier(.2,.7,.2,1);
  }
  :root{${vars}}
  .ph{display:block;width:100%;background:var(--src) center/cover no-repeat}
  *{box-sizing:border-box}
  html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
  body{margin:0;color:var(--cream);background:var(--black);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit}
  p{margin:0 0 16px}
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}

  /* ── grounds: black wall, black-2 wall, green board; grain on all ─────── */
  .black,.black-2,.green{background-image:var(--grain),
    linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
    background-size:220px 220px,44px 44px,44px 44px}
  .black{background-color:var(--black)}
  .black-2{background-color:var(--black-2)}
  .green{background-color:var(--green);--line:rgba(201,164,76,.4)}
  section{padding:clamp(64px,13vw,132px) 0;scroll-margin-top:12px;position:relative}

  /* ── type: foil display, mono labels, plain sans body ────────────────── */
  .k,.n{font:600 9.5px/1.5 var(--mono);letter-spacing:.16em;text-transform:uppercase}
  .n{color:var(--gold)}
  .pair{display:flex;justify-content:space-between;gap:16px;align-items:baseline;color:var(--muted)}
  .pair .k{text-align:right}
  h1,h2,h3{margin:0;font-family:var(--display);font-weight:700;line-height:.95;letter-spacing:-.01em;text-wrap:balance;overflow-wrap:anywhere}
  h2{font-size:clamp(44px,12.5vw,104px);margin:18px 0 22px}
  /* gold foil: a gradient clipped to the letters; a solid gold under it for any browser that cannot clip */
  .foil{color:var(--gold);background:linear-gradient(168deg,var(--gold-2) 0%,var(--gold) 38%,var(--gold-3) 58%,var(--gold-2) 100%);
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  @supports not (-webkit-background-clip:text){.foil{background:none;-webkit-text-fill-color:currentColor}}
  h3{font-size:clamp(26px,7vw,48px);margin:8px 0 0}
  .lede{font-size:17.5px;line-height:1.55;max-width:56ch;color:var(--muted)}
  .prose{font-size:18px;line-height:1.6;max-width:60ch}

  /* stickers: solid gold, hard shadow, a degree of tilt */
  .sticker{display:inline-block;max-width:100%;background:var(--gold);color:var(--black);font:700 10px/1.45 var(--mono);
    letter-spacing:.16em;text-transform:uppercase;text-wrap:balance;padding:7px 11px 6px;box-shadow:3px 3px 0 var(--cream);
    transform:rotate(-1.6deg);transform-origin:left center}
  .sticker.green-label{background:var(--green-line);color:var(--cream);box-shadow:3px 3px 0 var(--gold);transform:rotate(1.2deg)}

  /* corner brackets in gold, never a rounded card */
  .bx::before,.bx::after,.frame::before,.frame::after,.cut::before,.cut::after,.plaque::before,.plaque::after{
    content:"";position:absolute;width:14px;height:14px;border:1px solid var(--gold);opacity:.85;z-index:2}
  .frame::before,.cut::before,.plaque::before{top:-1px;left:-1px;border-right:0;border-bottom:0}
  .frame::after,.cut::after,.plaque::after{bottom:-1px;right:-1px;border-left:0;border-top:0}
  .bx::before{top:-1px;right:-1px;border-left:0;border-bottom:0}
  .bx::after{bottom:-1px;left:-1px;border-right:0;border-top:0}
  .frame{position:relative;border:1px solid var(--line);padding:22px 18px 20px}

  /* buttons: gold solid is the one action; ghost is gold hairline */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:46px;padding:0 20px;
    font:700 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;text-decoration:none;border:1px solid var(--gold);border-radius:2px;color:var(--cream)}
  .btn-solid{background:var(--gold);color:var(--black)}
  .arrow{font-family:var(--sans);font-weight:700}

  /* ── the guard scale: seven ticks, #0 up to #4 ──────────────────────── */
  .guards{display:flex;align-items:flex-end;gap:clamp(10px,4vw,26px);padding:0 22px;max-width:var(--wrap);margin:0 auto;height:64px}
  .guards span{display:flex;flex-direction:column;align-items:center;gap:6px}
  .guards i{display:block;width:2px;height:calc(var(--h) * 6px);background:var(--gold);opacity:.9}
  .guards b{font:600 9px/1 var(--mono);color:var(--muted);letter-spacing:.06em}
  .guards::after{content:"";flex:1;height:1px;background:var(--line);margin-bottom:14px}

  /* ── header, over the hero ─────────────────────────────────────────── */
  header.top{position:absolute;top:0;left:0;right:0;z-index:6;display:flex;justify-content:space-between;align-items:center;padding:16px 22px;gap:12px}
  .brand{font:700 15px/1.05 var(--display);letter-spacing:.02em;text-decoration:none;color:var(--gold);text-transform:uppercase}
  header nav{display:none;gap:22px}
  header nav a{font:600 9.5px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;text-decoration:none;color:var(--muted)}
  header nav a:hover{color:var(--gold)}
  header .btn{min-height:36px;padding:0 14px;font-size:10px}

  /* ── hero: the wordmark, then the cut in a gold frame on a green mount ── */
  .hero{position:relative;min-height:100svh;padding:88px 0 56px;overflow:hidden;display:grid;align-content:center}
  .hero::before{content:"";position:absolute;inset:0;background:radial-gradient(120% 70% at 50% 0%,rgba(201,164,76,.14),transparent 60%),
    radial-gradient(80% 50% at 50% 100%,rgba(15,46,34,.9),transparent 70%);pointer-events:none}
  .hero .wrap{position:relative;z-index:2}
  .hero .eyebrow{display:flex;gap:10px;align-items:center;color:var(--muted)}
  .hero .eyebrow::before{content:"";width:28px;height:1px;background:var(--gold)}
  .hero h1{font-size:clamp(52px,15.5vw,150px);line-height:.92;margin:16px 0 0;display:flex;flex-direction:column}
  .hero h1 .foil{padding-right:.06em}
  .hero h1 .cream{color:var(--cream);font-size:.62em;font-style:italic;font-weight:400;letter-spacing:0;margin-top:.12em}
  .hero .sub{margin-top:22px;display:flex;flex-direction:column;align-items:flex-start;gap:14px}
  .hero .sub .k{color:var(--muted);letter-spacing:.2em}
  .hero .actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
  .mount{position:relative;margin:40px 0 0;width:min(100%,420px)}
  .mount::before{content:"";position:absolute;inset:14px -14px -14px 14px;background:var(--green-2);border:1px solid var(--green-line)}
  .mount .cut{margin:0}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:36px;border-top:1px solid var(--line);padding-top:18px}
  .stats b{display:block;font:700 clamp(22px,6.4vw,34px)/1 var(--display);color:var(--gold);letter-spacing:-.01em}
  .stats span{display:block;margin-top:6px;font:600 9px/1.45 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}

  /* ── a cut on the wall: black mat, gold hairline, category tag ─────── */
  .cut{position:relative;margin:0;background:#000;border:1px solid var(--line);padding:6px;
    box-shadow:0 24px 40px -18px rgba(0,0,0,.9)}
  .cut .ph{filter:saturate(.92) contrast(1.04)}
  .cut figcaption{display:flex;flex-direction:column;gap:6px;padding:10px 4px 4px}
  .tag{align-self:flex-start;font:700 8.5px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;padding:5px 7px 4px;border:1px solid currentColor}
  .fade .tag{color:var(--black);background:var(--gold);border-color:var(--gold)}
  .design .tag{color:var(--cream);background:var(--green-line);border-color:var(--green-line)}
  .beard .tag{color:var(--cream)}
  .cap{font:600 9.5px/1.45 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}

  /* ── the work: two across, a wall of frames ────────────────────────── */
  .work .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:34px}
  .work .grid .cut:nth-child(4n+1){transform:rotate(-.5deg)}
  .work .grid .cut:nth-child(4n+3){transform:rotate(.5deg)}
  .legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:20px}
  .legend .tag{align-self:auto}

  /* ── the board: gold letters on green, dotted leaders to the price ─── */
  .menu .group{margin-top:clamp(34px,6vw,56px)}
  .menu .group .sticker{margin-bottom:6px}
  .board{list-style:none;margin:14px 0 0;padding:0;border-top:1px solid var(--line)}
  .row{padding:15px 0 14px;border-bottom:1px solid var(--line)}
  .line{display:flex;align-items:baseline;gap:10px}
  .name{font:700 17px/1.25 var(--sans);letter-spacing:-.01em;color:var(--cream)}
  .dots{flex:1;min-width:16px;border-bottom:1px dotted rgba(201,164,76,.55);transform:translateY(-5px)}
  .price{font:700 16px/1 var(--mono);letter-spacing:.02em;color:var(--gold);white-space:nowrap}
  .trims .price{color:var(--gold-2)}
  .meta{display:flex;gap:12px;flex-wrap:wrap;margin-top:6px;align-items:baseline}
  .dur{font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--gold);opacity:.85}
  .desc{font-size:14.5px;line-height:1.5;color:var(--muted)}
  .menu .book{margin-top:32px;display:flex;flex-direction:column;gap:12px;align-items:flex-start}
  .menu .book .k{color:var(--muted)}

  /* ── the break: the clipper shot, screened to a halftone, a review on it ── */
  .break{position:relative;min-height:84svh;display:grid;align-items:end;overflow:hidden;padding:clamp(64px,13vw,132px) 0 28px;background:var(--black)}
  .break .screen{position:absolute;inset:0;background:#fff;filter:contrast(28) invert(1);opacity:.55;overflow:hidden;isolation:isolate}
  .break .half{position:absolute;inset:0;width:100%;height:100%;filter:grayscale(1) contrast(.75) brightness(.7) invert(1) blur(1.2px)}
  .break .dots2{position:absolute;inset:0;mix-blend-mode:multiply;
    background:radial-gradient(circle at center,#000 0,#000 .4px,#fff 2.3px) 0 0/4px 4px}
  .break .tint{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,11,.55),rgba(15,46,34,.35) 45%,rgba(11,11,11,.96) 100%)}
  .break .wrap{position:relative;z-index:2;width:100%}
  .statement{margin:0;font:700 clamp(40px,12vw,104px)/.95 var(--display);letter-spacing:-.01em;color:var(--cream)}
  .statement em{font-style:italic;font-weight:400}
  .break cite{display:block;margin-top:18px;font:600 10px/1.5 var(--mono);letter-spacing:.16em;text-transform:uppercase;font-style:normal;color:var(--gold)}
  .break-foot{display:flex;justify-content:space-between;align-items:center;margin-top:clamp(36px,7vw,64px);gap:16px}

  /* ── the wall: plaques, gold plate on black ─────────────────────────── */
  .wall .plaques{display:grid;gap:14px;margin-top:30px}
  .plaque{position:relative;border:1px solid var(--line);padding:18px 16px 16px;background:linear-gradient(180deg,rgba(201,164,76,.08),rgba(201,164,76,.02))}
  .plaque b{display:block;font:700 clamp(24px,7vw,36px)/1 var(--display);color:var(--gold);letter-spacing:-.01em;overflow-wrap:anywhere}
  .plaque span{display:block;margin-top:8px;font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--cream)}
  .plaque small{display:block;margin-top:8px;font-size:13px;line-height:1.5;color:var(--muted)}
  .wall .note{margin-top:22px;font-size:14px;color:var(--muted);max-width:52ch}

  /* ── who's cutting: the portrait in a frame, the bio beside it ──────── */
  .about .portrait{width:min(100%,360px);margin:30px 0 0}
  .about .prose{margin-top:26px}
  .points{list-style:none;margin:18px 0 0;padding:0;border-top:1px solid var(--line)}
  .points li{display:flex;gap:14px;align-items:baseline;padding:13px 0;border-bottom:1px solid var(--line);font:600 12px/1.5 var(--mono);letter-spacing:.06em;text-transform:uppercase}
  .points li::before{content:"";flex:0 0 8px;height:8px;background:var(--gold);transform:rotate(45deg) translateY(-1px)}

  /* ── hours & the chair ─────────────────────────────────────────────── */
  .table{margin:0;padding:0;list-style:none;border-top:1px solid var(--line)}
  .table li{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--line);align-items:baseline}
  .table .k{color:var(--muted)}
  .table .v{font:600 12px/1.45 var(--mono);letter-spacing:.06em;text-transform:uppercase;text-align:right}
  .table .closed .v{color:var(--muted)}
  .where{margin-top:36px}
  .where .frame{margin-top:14px}
  .where .big{display:block;font:700 clamp(22px,6.4vw,32px)/1.1 var(--display);color:var(--gold);margin:8px 0 6px}
  .where p{color:var(--muted);font-size:15px;margin-bottom:14px}

  /* ── reviews: gold stars, the words as they were left ──────────────── */
  .reviews .score{display:flex;align-items:baseline;gap:14px;margin-top:18px}
  .reviews .score b{font:700 clamp(56px,16vw,120px)/1 var(--display);color:var(--gold);letter-spacing:-.02em}
  .reviews .score .k{color:var(--muted)}
  .stars{color:var(--gold);letter-spacing:.08em;font-size:14px}
  .quotes{display:grid;gap:12px;margin-top:26px}
  .quote{position:relative;border:1px solid var(--line);padding:18px 16px 16px;margin:0}
  .quote p{font:italic 19px/1.4 var(--display);margin:8px 0 12px;color:var(--cream)}
  .quote cite{font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase;font-style:normal;color:var(--muted)}

  /* ── the ask: one gold card, then the links ─────────────────────────── */
  .book .card-ask{display:block;margin:18px 0 0;background:var(--gold);color:var(--black);text-decoration:none;padding:22px 20px 24px;position:relative;
    box-shadow:6px 6px 0 var(--green-line)}
  .book .card-ask .k{display:flex;justify-content:space-between;color:rgba(11,11,11,.7)}
  .book .card-ask .big{display:block;margin-top:40px;font:700 clamp(24px,7vw,34px)/1.05 var(--display);letter-spacing:-.01em}
  .book .cta-lede{margin:clamp(34px,7vw,56px) 0 22px;font-size:18px;line-height:1.55;max-width:56ch}
  .links{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
  .links a{display:flex;align-items:center;gap:18px;padding:20px 0;border-bottom:1px solid var(--line);text-decoration:none;
    font:600 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .links a .arrow{margin-left:auto;font-size:16px;color:var(--gold)}
  footer{margin-top:clamp(48px,9vw,88px);display:flex;flex-direction:column;gap:8px;font:600 9px/1.6 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  footer a{text-decoration:none}

  /* ── the phone bar: book, always in reach ──────────────────────────── */
  .bar{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;gap:10px;padding:10px 14px calc(10px + env(safe-area-inset-bottom));
    background:rgba(11,11,11,.94);backdrop-filter:blur(8px);border-top:1px solid var(--line)}
  .bar .btn{flex:1}
  body{padding-bottom:72px}

  /* motion: a settle, removed entirely when asked */
  .js .rise{opacity:0;transform:translateY(14px);animation:rise .9s var(--ease) forwards;animation-delay:calc(var(--i,0) * .08s)}
  @keyframes rise{to{opacity:1;transform:none}}
  @media (prefers-reduced-motion:reduce){.js .rise{animation:none;opacity:1;transform:none}html{scroll-behavior:auto}}

  /* ── wider: the hero splits, the wall goes four across ─────────────── */
  @media (min-width:860px){
    header.top{padding:24px 32px}
    header nav{display:flex}
    header .btn{min-height:40px;font-size:11px;padding:0 18px}
    .hero{padding:120px 0 80px}
    .hero .wrap{display:grid;grid-template-columns:1.15fr .85fr;gap:56px;align-items:center}
    .hero h1{font-size:clamp(84px,9.5vw,150px)}
    .mount{margin:0;justify-self:end;width:min(100%,440px)}
    .stats{grid-column:1 / -1;grid-template-columns:repeat(3,max-content);gap:64px}
    .work .grid{grid-template-columns:repeat(4,1fr);gap:20px}
    .menu .wrap{display:grid;grid-template-columns:1fr 1fr;gap:0 64px}
    .menu .head{grid-column:1 / -1}
    .menu .book{grid-column:1 / -1}
    .wall .plaques{grid-template-columns:repeat(3,1fr);gap:18px}
    .about .wrap{display:grid;grid-template-columns:.8fr 1.2fr;gap:56px;align-items:start}
    .about .portrait{margin-top:0}
    .hours .wrap{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start}
    .where{margin-top:0}
    .quotes{grid-template-columns:1fr 1fr}
    .book .wrap{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start}
    .book .cta-lede{margin-top:0}
    footer{grid-column:1 / -1;flex-direction:row;justify-content:space-between}
    .bar{display:none}
    body{padding-bottom:0}
  }
  @media (max-width:340px){.hero h1{font-size:46px}.work .grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>

<header class="top">
  <a class="brand" href="#top">${esc(b.name)}</a>
  <nav aria-label="Sections"><a href="#work">The work</a><a href="#menu">Menu</a><a href="#wall">Journey</a><a href="#about">Tinez</a><a href="#hours">Hours</a></nav>
  ${booking ? `<a class="btn btn-solid" href="${esc(booking)}" target="_blank" rel="noopener">Book</a>` : ''}
</header>

<main>
<section class="hero black" id="top">
  <div class="wrap">
    <div>
      <span class="eyebrow k rise" style="--i:0">${esc(b.tagline)}</span>
      <h1 class="rise" style="--i:1"><span class="foil">Quality cuts.</span><span class="cream">Attention to detail.</span></h1>
      <div class="sub">
        <span class="sticker rise" style="--i:3">Fades · Beards · Designs · Kids</span>
        <p class="lede rise" style="--i:4">${esc(b.subhead)}</p>
        <div class="actions rise" style="--i:5">
          ${booking ? `<a class="btn btn-solid" href="${esc(booking)}" target="_blank" rel="noopener">${esc(b.cta?.primary || 'Book online')}</a>` : ''}
          <a class="btn" href="#menu">The menu <span class="arrow">↓</span></a>
        </div>
      </div>
    </div>
    <div class="mount rise" style="--i:2">
      <figure class="cut ${hero ? kindOf(hero)[0] : 'fade'}">
        <span class="bx" aria-hidden="true"></span>
        ${img(hero, '4/5')}
        <figcaption><span class="tag">${hero ? kindOf(hero)[1] : ''}</span><span class="cap">${esc(hero ? label(hero) : '')}</span></figcaption>
      </figure>
    </div>
    <div class="stats rise" style="--i:6">
      ${(b.highlights || []).filter((h) => h && (h.value || h.label)).slice(0, 3).map((h) => `<div><b>${esc(h.value)}</b><span>${esc(h.label)}</span></div>`).join('\n      ')}
    </div>
  </div>
</section>

${guards}

<section class="work black-2" id="work">
  <div class="wrap">
    <span class="sticker">01 / The work</span>
    <h2 class="foil">Sharp fades. Clean lines.</h2>
    <p class="lede">Cuts from the chair at Colleywood Cuts, as he posted them. ${legendLedeText}</p>
    <div class="legend" aria-hidden="true">${kinds.map(([c, t]) => `<span class="${c}"><span class="tag">${t}</span></span>`).join('')}</div>
    <div class="grid">
      ${work.map((p, i) => frame(p, i)).join('')}
    </div>
  </div>
</section>

${guards}

<section class="menu green" id="menu">
  <div class="wrap">
    <div class="head">
      <span class="sticker">02 / ${esc(b.servicesHeading || 'The menu')}</span>
      <h2 class="foil">The board.</h2>
      <p class="lede">${esc(b.servicesLede)}</p>
    </div>
    ${groups.map((g) => `
    <div class="group ${/trim/i.test(g) ? 'trims' : 'cuts'}">
      <span class="sticker ${/trim/i.test(g) ? 'green-label' : ''}">${esc(g)}</span>
      <ol class="board">${services.filter((s) => (s.group || 'Services') === g).map(row).join('')}
      </ol>
    </div>`).join('')}
    <div class="book">
      ${booking ? `<a class="btn btn-solid" href="${esc(booking)}" target="_blank" rel="noopener">${esc(b.cta?.primary || 'Book online')} <span class="arrow">↗</span></a>` : ''}
      <span class="k">Prices and times as listed on Booksy · ${esc(b.priceRange)}</span>
    </div>
  </div>
</section>

<section class="break" aria-label="A review, over a photo of Tinez mid-cut">
  ${clippers ? `<div class="screen" aria-hidden="true"><div class="half ph" style="--src:var(--ph${photos.indexOf(clippers)})"></div><div class="dots2"></div></div>` : ''}
  <div class="tint" aria-hidden="true"></div>
  <div class="wrap">
    ${reviews[2] ? `<blockquote style="margin:0"><p class="statement">“${esc(reviews[2].text)}”</p><cite>— ${esc(reviews[2].author)}, on ${esc(reviews[2].source || 'Booksy')}</cite></blockquote>` : ''}
    <div class="break-foot"><span class="brand">${esc(b.name)}</span><a class="btn" href="#wall">The journey <span class="arrow">↓</span></a></div>
  </div>
</section>

<section class="wall black" id="wall">
  <div class="wrap">
    <span class="sticker">03 / The journey</span>
    <h2 class="foil">On the wall.</h2>
    <p class="lede">What's on record so far. The wall grows as the trophies go up.</p>
    <div class="plaques">
      ${journey.map((j, i) => `<div class="plaque rise" style="--i:${i}"><span class="bx" aria-hidden="true"></span><b>${esc(j.value)}</b><span>${esc(j.label)}</span>${j.note ? `<small>${esc(j.note)}</small>` : ''}</div>`).join('\n      ')}
    </div>
  </div>
</section>

${guards}

<section class="about black-2" id="about">
  <div class="wrap">
    ${portrait ? `<figure class="cut portrait"><span class="bx" aria-hidden="true"></span>${img(portrait, '4/5')}<figcaption><span class="tag" style="color:var(--gold);border-color:var(--gold)">The barber</span><span class="cap">${esc(portrait.caption || '')}</span></figcaption></figure>` : ''}
    <div>
      <span class="sticker">04 / ${esc(b.aboutHeading || "Who's cutting")}</span>
      <h2 class="foil">Tinez.</h2>
      <span class="sticker green-label">Say it TEE-NEZ</span>
      <div class="prose">
        ${(b.about || '').split(/\n\n+/).map((p) => `<p>${esc(p)}</p>`).join('\n        ')}
      </div>
      <ul class="points">
        ${(b.points || []).map((p) => `<li>${esc(p)}</li>`).join('\n        ')}
      </ul>
    </div>
  </div>
</section>

<section class="hours green" id="hours">
  <div class="wrap">
    <div>
      <span class="sticker">05 / Hours</span>
      <h2 class="foil">The chair.</h2>
      <ul class="table">
        ${hours.map((h) => `<li class="${/closed/i.test(h.time) ? 'closed' : ''}"><span class="k">${esc(h.days)}</span><span class="v">${esc(h.time)}</span></li>`).join('\n        ')}
      </ul>
    </div>
    <div class="where">
      <div class="pair"><span class="n">Where</span><span class="k">Ghent, Norfolk</span></div>
      <div class="frame"><span class="bx" aria-hidden="true"></span>
        <span class="k">Colleywood Cuts</span>
        <span class="big">${esc(a.street)}</span>
        <p>${esc([a.city, a.state].filter(Boolean).join(', '))} ${esc(a.zip)}</p>
        ${maps ? `<a class="btn" href="${maps}" target="_blank" rel="noopener">Directions <span class="arrow">↗</span></a>` : ''}
      </div>
    </div>
  </div>
</section>

<section class="reviews black" id="reviews">
  <div class="wrap">
    <span class="sticker">06 / Reviews</span>
    ${rating.value ? `<div class="score"><b>${esc(rating.value)}</b><div><span class="stars" aria-label="${esc(rating.value)} out of 5">★★★★★</span><br><span class="k">${esc(rating.count)} reviews on ${esc(rating.source || 'Booksy')}</span></div></div>` : ''}
    <div class="quotes">
      ${reviews.map((r) => `<blockquote class="quote"><span class="bx" aria-hidden="true"></span><span class="stars" aria-hidden="true">★★★★★</span><p>${esc(r.text)}</p><cite>${esc(r.author)} · ${esc(r.source || 'Booksy')}</cite></blockquote>`).join('\n      ')}
    </div>
  </div>
</section>

<section class="book black-2" id="book">
  <div class="wrap">
    <div>
      <div class="pair"><span class="n">07 / Book</span><span class="k">${esc(b.ctaHeading || 'Book the chair')}</span></div>
      ${booking ? `<a class="card-ask" href="${esc(booking)}" target="_blank" rel="noopener">
        <span class="k">Open the calendar <span class="arrow">↗</span></span>
        <span class="big">Book an appointment</span>
      </a>` : ''}
    </div>
    <div>
      <p class="cta-lede">${esc(b.ctaLede)}</p>
      <ol class="links">
        ${booking ? `<li><a href="${esc(booking)}" target="_blank" rel="noopener"><span class="n">01</span>Booksy<span class="arrow">↗</span></a></li>` : ''}
        ${instagram ? `<li><a href="${esc(instagram)}" target="_blank" rel="noopener"><span class="n">02</span>${esc(handle)}<span class="arrow">↗</span></a></li>` : ''}
        ${tel ? `<li><a href="sms:${esc(tel)}"><span class="n">03</span>Text for after hours<span class="arrow">↗</span></a></li>` : ''}
        ${maps ? `<li><a href="${maps}" target="_blank" rel="noopener"><span class="n">${tel ? '04' : '03'}</span>${esc(a.street)}, ${esc(a.city)}<span class="arrow">↗</span></a></li>` : ''}
      </ol>
    </div>
    <footer>
      <span>${esc(b.tagline)}</span>
      <span>${esc(b.name)} © ${new Date().getFullYear()}</span>
      <span>Site by McManus Web Co.</span>
    </footer>
  </div>
</section>
</main>

<div class="bar">
  ${booking ? `<a class="btn btn-solid" href="${esc(booking)}" target="_blank" rel="noopener">Book now</a>` : ''}
  <a class="btn" href="#menu">Menu</a>
</div>

</body>
</html>
`;
}

module.exports = { render };
