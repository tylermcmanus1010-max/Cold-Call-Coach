// The page for BJB Custom Painting, built by hand against DESIGN.md — second
// pass, to the bar Angel & Arturo set (design/reference/angel-arturo/).
//
// Concept (rule zero): the painter's drawing. A landscaper works from a site
// plan; a painter works from an elevation and a room schedule — every surface
// in the house, named and numbered. So the hero is a cut-away house drawn in
// primer grey, with eight numbered markers, one per service. Tap a number and
// that surface gets painted in its colour; the matching chip lights up below.
// Tap a chip and the drawing answers. Keyboard reaches every marker.
//
// The colours are not decoration. Every one is lifted from a photograph of his
// own work on this page: the terracotta bedroom, the blue deck, the yellow
// siding, primed drywall. The services are still paint chips — the first
// pass's object — and the chips are now also the list. His photographs are
// prints held with painter's blue tape. Two grounds, drop cloth and canvas.
// The headline runs edge to edge and says what the work is for.
//
// Everything on it is his: services off his own site (decks from his gallery,
// garage epoxy from a customer's review), two Google reviews verbatim, "over a
// decade" and "painting and drywall" from his About page, the number on his
// yard signs, the email he prints, eight of his own photographs looked at one
// by one. Hours are not stated; his site never names a person, so none is.
// The map is geography — Delaware's three counties — with his two stated
// areas marked. Nothing here is invented.
//
// Self-contained: system fonts, inline SVG, photos as data URIs, no requests.
// Chips are checkboxes, so the estimate works with JavaScript off; the script
// adds the painting, the sync and the text body. Judged at 390px.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .17"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

// Delaware's three counties. Geography, restyled; his areas are marked on it.
const DE = {
  viewBox: '-10 -4 164 292',
  newCastle: 'M8 0 L58 0 Q118 2 140 36 L136 60 L112 70 L96 86 L88 96 L8 96 Z',
  kent: 'M8 96 L88 96 L104 108 L118 128 L122 150 L128 176 L112 190 L8 190 Z',
  sussex: 'M8 190 L112 190 L136 198 L146 226 L140 262 L124 284 L92 288 L8 288 Z',
};

function render(b) {
  const digits = String(b.phone || '').replace(/[^0-9]/g, '');
  const tel = `tel:+1${digits}`;
  const name = b.name || 'BJB Custom Painting';
  const area = (b.serviceArea || []).join(' · ');

  const photos = (b.photos || []).filter((p) => p && p.src);
  const work = photos.filter((p) => p.kind === 'work');
  const vars = work.map((p, i) => `--ph${i}:url("${p.src}")`).join(';');
  const img = (p, ratio) => !p ? '' :
    `<span class="ph" role="img" aria-label="${esc(p.caption || '')}" style="--src:var(--ph${work.indexOf(p)});aspect-ratio:${ratio || '4/3'}"></span>`;
  const pick = (re) => work.find((p) => re.test(p.alt || '')) || null;
  const deck = pick(/deck/i), fireplace = pick(/fireplace/i);
  const strip = work.filter((p) => p !== fireplace);

  const svc = b.services || [];
  const reviews = (b.reviews || []).filter((r) => r.text);
  const rating = b.rating || {};
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

  // Swatch colours by service code, so the drawing and the chips share them.
  const sw = Object.fromEntries(svc.map((s) => [s.code, s.swatch]));
  const swVars = svc.map((s) => `--sw${s.code}:${s.swatch}`).join(';');

  // ── the drawing ───────────────────────────────────────────────────────────
  // A cut-away house in primer grey. Each surface is a zone (.z + code) that
  // takes its service's colour when active. Markers carry the number.
  const mk = (code, x, y, label) =>
    `<g class="mk" data-s="${code}" tabindex="0" role="button" aria-label="${code}, ${esc(label)}" transform="translate(${x} ${y})" style="--c:var(--sw${code})">
      <circle class="halo" r="17"/><circle class="dot" r="12"/><text y="4">${Number(code)}</text></g>`;
  const label = (code) => (svc.find((s) => s.code === code) || {}).name || '';

  const house = `
<svg class="house" viewBox="0 0 600 400" role="img" aria-label="A cut-away drawing of a house with every painted surface numbered one to eight" style="${swVars}">
  <defs>
    <pattern id="siding" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0 7.5H8" stroke="currentColor" stroke-width="1" opacity=".55"/></pattern>
    <pattern id="boards" width="12" height="10" patternUnits="userSpaceOnUse"><path d="M0 9.5H12" stroke="currentColor" stroke-width="1.2" opacity=".5"/></pattern>
    <pattern id="speckle" width="10" height="10" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".9" fill="currentColor" opacity=".55"/><circle cx="7" cy="7" r=".8" fill="currentColor" opacity=".45"/><circle cx="5" cy="1" r=".6" fill="currentColor" opacity=".4"/></pattern>
    <pattern id="tapeseam" width="60" height="100" patternUnits="userSpaceOnUse"><path d="M30 0V100" stroke="currentColor" stroke-width="5" opacity=".28"/></pattern>
    <pattern id="grass" width="10" height="6" patternUnits="userSpaceOnUse"><path d="M2 6V2M5 6V1M8 6V3" stroke="currentColor" stroke-width="1" opacity=".5"/></pattern>
  </defs>

  <!-- ground -->
  <rect class="ground" x="0" y="330" width="600" height="70"/>
  <rect class="lawn" x="0" y="330" width="600" height="70" fill="url(#grass)"/>

  <!-- 02 exterior: the gable wall, siding -->
  <g class="lay l1">
    <path class="z z02 surf" d="M40 330 V150 L135 70 L230 150 V330 Z"/>
    <path class="hatch" d="M40 330 V150 L135 70 L230 150 V330 Z" fill="url(#siding)"/>
    <path class="roof" d="M28 158 L135 62 L242 158" fill="none" stroke-width="7" stroke-linejoin="round"/>
    <rect class="win" x="78" y="190" width="40" height="52"/><path class="mull" d="M98 190V242M78 216H118"/>
    <rect class="win" x="152" y="190" width="40" height="52"/><path class="mull" d="M172 190V242M152 216H192"/>
    <rect class="door" x="118" y="262" width="34" height="68"/>
  </g>

  <!-- the cut-away: one storey, sectioned -->
  <g class="lay l2">
    <!-- 01 interior wall, with trim -->
    <rect class="z z01 surf" x="236" y="150" width="190" height="180"/>
    <rect class="base" x="236" y="318" width="190" height="12"/>
    <rect class="crown" x="236" y="150" width="190" height="7"/>
    <!-- a window on the interior wall, the only thing on it -->
    <rect class="win" x="270" y="188" width="52" height="60"/><path class="mull" d="M296 188V248M270 218H322"/>
    <!-- 05 the repair: a patch, feathered -->
    <g class="z z05 surf patch"><ellipse cx="380" cy="215" rx="26" ry="20"/><ellipse cx="380" cy="215" rx="15" ry="11" class="patch-in"/></g>
    <!-- 03 kitchen cabinets, upper and lower -->
    <g class="z z03 surf">
      <rect x="436" y="156" width="124" height="54"/><path class="cab" d="M467 156V210M498 156V210M529 156V210"/>
      <rect x="436" y="268" width="124" height="62"/><path class="cab" d="M467 268V330M498 268V330M529 268V330"/>
      <path class="pull" d="M457 183h6M488 183h6M519 183h6M550 183h6M457 300h6M488 300h6M519 300h6M550 300h6"/>
    </g>
    <rect class="counter" x="432" y="262" width="132" height="7"/>
    <!-- ceiling line -->
    <path class="ceil" d="M236 150H560" stroke-width="6"/>
    <!-- 04 new drywall: bare board, taped seams -->
    <rect class="z z04 surf" x="236" y="46" width="324" height="98"/>
    <rect class="seams" x="236" y="46" width="324" height="98" fill="url(#tapeseam)"/>
    <path class="screws" d="M250 60h2M250 90h2M250 120h2M320 60h2M320 120h2M400 60h2M400 120h2M480 60h2M480 90h2M480 120h2M548 70h2M548 110h2" stroke-width="3" stroke-linecap="round"/>
  </g>

  <!-- outside right: 07 the deck, 08 the garage floor -->
  <g class="lay l3">
    <rect class="z z07 surf" x="430" y="340" width="150" height="26"/>
    <rect class="hatch" x="430" y="340" width="150" height="26" fill="url(#boards)"/>
    <path class="rail" d="M434 340V318M470 340V318M506 340V318M542 340V318M578 340V318M430 322H582" stroke-width="3"/>
    <path class="rail" d="M430 332H582" stroke-width="2"/>
    <rect class="z z08 surf" x="236" y="340" width="186" height="26"/>
    <rect class="hatch" x="236" y="340" width="186" height="26" fill="url(#speckle)"/>
    <path class="slab" d="M236 340H422" stroke-width="3"/>
  </g>

  <!-- 06 the colour consultation: a fan deck held to the wall -->
  <g class="lay l4 fan" transform="translate(372 266) rotate(-14)">
    <rect class="z z06 surf" x="0" y="0" width="22" height="46" rx="2"/>
    <rect class="card c2" x="9" y="-6" width="22" height="46" rx="2"/>
    <rect class="card c3" x="18" y="-12" width="22" height="46" rx="2"/>
    <circle cx="11" cy="42" r="2.4" class="rivet"/>
  </g>

  <!-- markers, numbered in the order of the chips -->
  <g class="lay l5 marks">
    ${mk('01', 262, 296, label('01'))}
    ${mk('02', 60, 300, label('02'))}
    ${mk('03', 498, 236, label('03'))}
    ${mk('04', 400, 95, label('04'))}
    ${mk('05', 412, 196, label('05'))}
    ${mk('06', 360, 254, label('06'))}
    ${mk('07', 508, 379, label('07'))}
    ${mk('08', 330, 379, label('08'))}
  </g>
</svg>`;

  // ── the chips: service as paint chip, and the list the drawing answers to ─
  const chip = (s) => `
    <li><label class="chip" data-s="${esc(s.code)}" style="--sw:${esc(s.swatch)}">
      <input type="checkbox" name="svc" value="${esc(s.name)}">
      <span class="sw" aria-hidden="true"><b class="num">${Number(s.code)}</b></span>
      <span class="body">
        <span class="pair"><span class="n">BJB&#8209;${esc(s.code)}</span><span class="k">${esc(s.group)}</span></span>
        <span class="nm">${esc(s.name)}</span>
        <span class="ds">${esc(s.desc)}</span>
        <span class="add k">tap to add to your estimate</span>
      </span>
      <span class="tape pick" aria-hidden="true"></span>
    </label></li>`;

  const print = (p, i) => `
    <figure class="print">
      <span class="tape" aria-hidden="true"></span>
      ${img(p, '4/3')}
      <figcaption class="pair"><span class="n">${String(i + 1).padStart(2, '0')}</span><span class="k">${esc(p.caption || '')}</span></figcaption>
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
<meta property="og:title" content="${esc(name)} — every surface in the house">
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
    --primer:#d9d4c9; --primer-2:#c7c1b4; --pencil:#4a4640;
    --brown:#5e5449; --line:rgba(23,25,28,.16); --muted:#6b6358; --grid:rgba(30,24,16,.05);
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
  body{margin:0;color:var(--ink);background:var(--paper);font:17px/1.55 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit} p{margin:0 0 16px} ul,ol{margin:0;padding:0;list-style:none}
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}

  .ink,.paper,.paper-2{background-image:var(--grain),
    linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:220px 220px,36px 36px,36px 36px}
  .paper{background-color:var(--paper)} .paper-2{background-color:var(--paper-2)}
  .ink{background-color:var(--ink);color:var(--paper);--grid:rgba(255,255,255,.045);--line:rgba(255,255,255,.16);--muted:rgba(239,232,218,.6)}
  section{padding:clamp(64px,12vw,130px) 0;scroll-margin-top:12px}

  /* three scales of type, far apart. The voice is a heavy sans in capitals. */
  .k,.n{font:600 9.5px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .n{color:var(--tape)} .ink .n{color:var(--tape-2)}
  .pair{display:flex;justify-content:space-between;gap:16px;align-items:baseline;color:var(--muted)}
  h2{font:800 clamp(38px,10.5vw,86px)/.92 var(--sans);letter-spacing:-.035em;text-transform:uppercase;margin:0 0 .35em;text-wrap:balance}
  h2 em{font:400 italic .92em/1 var(--serif);text-transform:none;letter-spacing:-.01em;color:var(--tape)}
  .ink h2 em{color:var(--tape-2)}
  .lede{font-size:18px;line-height:1.5;max-width:54ch;color:var(--brown)} .ink .lede{color:var(--muted)}
  .prose{font-family:var(--serif);font-size:18.5px;line-height:1.6;max-width:62ch}

  .sticker{display:inline-block;max-width:100%;background:var(--red);color:var(--white);font:700 10px/1.45 var(--mono);letter-spacing:.14em;text-transform:uppercase;text-wrap:balance;padding:7px 11px 6px;box-shadow:3px 3px 0 var(--ink);transform:rotate(-1.6deg);transform-origin:left center}
  .ink .sticker{box-shadow:3px 3px 0 var(--paper)}
  .card{position:relative;padding:22px 18px 20px}
  .card::before,.card::after,.bx::before,.bx::after{content:"";position:absolute;width:14px;height:14px;border:1px solid currentColor;opacity:.7}
  .card::before{top:0;left:0;border-right:0;border-bottom:0} .card::after{bottom:0;right:0;border-left:0;border-top:0}
  .bx::before{top:0;right:0;border-left:0;border-bottom:0} .bx::after{bottom:0;left:0;border-right:0;border-top:0}

  /* one loud accent: every call button is tape blue, and nothing else is */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:50px;padding:0 20px;border:1px solid currentColor;text-decoration:none;font:700 15px/1 var(--sans);letter-spacing:-.01em;color:inherit;background:transparent;cursor:pointer}
  .btn-solid{background:var(--tape);border-color:var(--tape);color:var(--white)}
  .btn svg{width:16px;height:16px;flex:none}
  .btns{display:flex;flex-wrap:wrap;gap:10px}
  a:focus-visible,button:focus-visible,.mk:focus-visible,input:focus-visible+.sw{outline:2px solid var(--tape-2);outline-offset:3px}

  .tape{position:absolute;z-index:2;top:-11px;left:50%;width:92px;height:24px;transform:translateX(-50%) rotate(-2deg);background:rgba(45,116,196,.82);box-shadow:0 1px 2px rgba(0,0,0,.25)}
  .tape::after{content:"";position:absolute;inset:0;background:var(--grain);opacity:.5}

  /* nav */
  .nav{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 22px;background:rgba(23,25,28,.92);color:var(--paper);backdrop-filter:blur(8px);border-bottom:1px solid rgba(255,255,255,.08)}
  .brand{text-decoration:none;color:var(--paper);display:flex;align-items:baseline;gap:8px}
  .brand b{font:800 18px/1 var(--sans);letter-spacing:-.02em} .brand span{font:400 italic 14px/1 var(--serif);color:var(--muted)}
  .nav .btn{min-height:40px;padding:0 14px;font-size:13px}

  /* hero: the headline edge to edge, then the drawing */
  .hero{padding:clamp(40px,8vw,90px) 0 0;overflow:hidden}
  .hero h1{font:800 72px/.86 var(--sans);letter-spacing:-.04em;text-transform:uppercase;margin:18px 0 0;color:var(--tape-2);display:flex;flex-direction:column}
  .hero h1 span{display:block;white-space:nowrap}
  .hero h1 .ph{display:inline}
  .hero h1 span:last-child{color:var(--paper)}
  .hero .rule{height:3px;background:var(--paper);margin:26px 0 22px;opacity:.9}
  .hero .lede{max-width:46ch}
  .hero .btns{margin-top:22px}
  .hero .btn{min-height:54px;font-size:17px;flex:1 1 150px}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:30px;padding-top:16px;border-top:1px solid var(--line)}
  .stats b{display:block;font:800 clamp(22px,6.4vw,32px)/1 var(--sans);letter-spacing:-.03em;color:var(--tape-2)}
  .stats .k{display:block;margin-top:6px;white-space:normal}

  /* the drawing sits on a sheet of paper in a frame */
  .sheet{margin:34px -6px 0;background:var(--white);border:2px solid var(--ink);position:relative;padding:12px 10px 6px;color:var(--ink);--muted:#6b6358;--line:rgba(23,25,28,.16)}
  .sheet::after{content:"";position:absolute;inset:6px;border:1px solid var(--line);pointer-events:none}
  .ink .sheet{border-color:var(--paper)}
  .house{display:block;width:100%;height:auto;color:var(--pencil)}
  .house .ground{fill:var(--primer-2)} .house .lawn{color:#5f7d49}
  .house .surf{fill:var(--primer);stroke:var(--pencil);stroke-width:1.5;transition:fill .25s ease,opacity .2s ease}
  .house .hatch{pointer-events:none;color:var(--pencil)}
  .house .roof,.house .ceil,.house .slab,.house .rail,.house .screws,.house .mull,.house .cab,.house .pull{stroke:var(--pencil);fill:none}
  .house .mull,.house .cab{stroke-width:1.2} .house .pull{stroke-width:2;stroke-linecap:round}
  .house .win{fill:#dfe7ee;stroke:var(--pencil);stroke-width:1.5} .house .door{fill:var(--primer-2);stroke:var(--pencil);stroke-width:1.5}
  .house .base,.house .crown,.house .counter{fill:var(--white);stroke:var(--pencil);stroke-width:1.2}
  .house .patch{stroke-dasharray:4 3} .house .patch-in{fill:var(--white);stroke:none}
  .house .seams{color:var(--white)}
  .house .card{fill:var(--white);stroke:var(--pencil);stroke-width:1.2} .house .c2{fill:#e8ddd0} .house .c3{fill:#d6dde8} .house .rivet{fill:var(--pencil)}
  /* paint it: an active surface takes its colour */
  .house.has-active .surf{opacity:.55}
  .house.has-active .surf.is-active{opacity:1}
  .house .z01.is-active{fill:var(--sw01)} .house .z02.is-active{fill:var(--sw02)} .house .z03.is-active rect{fill:var(--sw03)} .house .z03.is-active{fill:var(--sw03)}
  .house .z04.is-active{fill:var(--sw04)} .house .z05.is-active ellipse:first-child{fill:var(--sw05)} .house .z06.is-active{fill:var(--sw06)}
  .house .z07.is-active{fill:var(--sw07)} .house .z08.is-active{fill:var(--sw08)}
  .house .mk{cursor:pointer;transition:opacity .2s ease}
  .house .mk .halo{fill:var(--c);opacity:0;transition:opacity .2s ease}
  .house .mk .dot{fill:var(--pencil);stroke:var(--c);stroke-width:3}
  .house .mk text{font:800 12.5px var(--sans);fill:#fff;text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:rgba(0,0,0,.25);stroke-width:2}
  .house.has-active .mk{opacity:.35} .house.has-active .mk.is-active{opacity:1}
  .house .mk.is-active .halo{opacity:.3} .house .mk.is-active .dot{fill:var(--c);stroke:var(--white);stroke-width:3.5}
  .house .mk.is-active text{fill:#fff;stroke:rgba(0,0,0,.45)}
  .readout{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:center;padding:12px 10px 8px;border-top:1px solid var(--line);margin-top:8px;font-size:14px}
  .readout .chipn{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font:800 13px var(--sans);color:#fff;background:var(--tape)}
  .readout .chipn[hidden]{display:none}
  .readout .ro-name{font-weight:700} .readout .ro-cat{display:block;color:var(--muted);font-size:12.5px}
  .readout .ro-add{display:none;margin-left:auto;font:700 12px var(--sans);color:var(--tape);background:none;border:1px solid var(--tape);padding:7px 10px;cursor:pointer}
  .readout.live .ro-add{display:inline-block}
  @media (prefers-reduced-motion:no-preference){
    .js .house .lay{animation:lay .5s ease backwards}
    .js .house .lay.l1{animation-delay:.05s} .js .house .lay.l2{animation-delay:.3s} .js .house .lay.l3{animation-delay:.55s} .js .house .lay.l4{animation-delay:.8s} .js .house .lay.l5{animation-delay:1.05s}
    @keyframes lay{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  }

  /* the work */
  .work .strip{display:flex;gap:26px;overflow-x:auto;scroll-snap-type:x mandatory;padding:34px 22px 28px;margin:0 -22px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .work .strip::-webkit-scrollbar{display:none}
  .print{position:relative;flex:0 0 min(78vw,330px);margin:0;background:var(--white);padding:9px 9px 12px;scroll-snap-align:start;box-shadow:0 12px 26px -8px rgba(0,0,0,.35),0 1px 0 rgba(0,0,0,.06)}
  .print figcaption{margin-top:10px}
  .work .print:nth-child(odd){transform:rotate(-1.3deg)} .work .print:nth-child(even){transform:rotate(1.2deg)}

  /* the chips: the list the drawing answers to */
  .deck .chips{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-top:30px}
  .chip{position:relative;display:flex;flex-direction:column;background:var(--white);cursor:pointer;height:100%;box-shadow:0 10px 22px -10px rgba(0,0,0,.35),0 1px 0 rgba(0,0,0,.06);transform:rotate(-.6deg);transition:transform .15s ease,box-shadow .15s ease}
  .chips li:nth-child(even) .chip{transform:rotate(.7deg)} .chips li:nth-child(3n) .chip{transform:rotate(-1.1deg)}
  .chip input{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
  .chip .sw{display:flex;align-items:flex-end;padding:8px;height:84px;background:var(--sw);border-bottom:1px solid rgba(0,0,0,.08)}
  .chip .num{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--white);color:var(--ink);font:800 13px var(--sans);box-shadow:0 1px 3px rgba(0,0,0,.3)}
  .chip .body{display:flex;flex-direction:column;gap:5px;padding:12px 12px 14px}
  .chip .nm{font:700 18px/1.15 var(--sans);letter-spacing:-.02em;color:var(--ink)}
  .chip .ds{font-size:13px;line-height:1.45;color:var(--brown)}
  .chip .add{margin-top:4px;color:var(--muted);font-size:9px}
  .chip .tape.pick{display:none;top:-10px;left:auto;right:10px;transform:rotate(6deg);width:70px}
  .chip:has(input:checked){box-shadow:0 0 0 2px var(--tape),0 14px 26px -10px rgba(0,0,0,.4)}
  .chip:has(input:checked) .tape.pick{display:block}
  .chip:has(input:checked) .add{color:var(--tape)}
  .chip.is-active{transform:rotate(0) translateY(-4px)!important;box-shadow:0 0 0 3px var(--tape),0 18px 30px -10px rgba(0,0,0,.45)}
  .chip.is-active .nm{color:var(--tape)}
  .deck .how{margin-top:16px;color:var(--muted)}

  .ask-bar{margin-top:34px;display:grid;gap:14px}
  .picked{min-height:24px;font:italic 17px/1.5 var(--serif);color:var(--muted)} .picked b{font-style:normal;color:var(--paper);font-family:var(--sans);font-weight:700}

  .revs{margin-top:30px} .rev{padding:22px 0;border-top:1px solid var(--line)}
  .rev blockquote{margin:12px 0 10px;font:400 clamp(21px,5.4vw,30px)/1.3 var(--serif);letter-spacing:-.01em;text-wrap:pretty}
  .rev cite{font-style:normal;color:var(--muted);font-size:14px}

  .about .wrap{display:grid;gap:34px}
  .about .print{width:min(100%,340px);flex:none;transform:rotate(1.6deg)}
  .about .print figcaption{font:italic 15px/1.3 var(--serif);color:var(--brown);text-align:center}
  .facts{margin:20px 0 0} .facts li{display:flex;gap:16px;align-items:baseline;padding:12px 0;border-top:1px solid var(--line);font-size:16px} .facts li:last-child{border-bottom:1px solid var(--line)}

  /* the place: Delaware, his two areas marked */
  .area .wrap{display:grid;gap:30px}
  .demap{display:block;width:min(100%,260px);height:auto;margin:0 auto}
  .demap path{fill:var(--primer);stroke:var(--pencil);stroke-width:1.5;stroke-linejoin:round}
  .demap path.mine{fill:var(--tape)}
  .demap text{font:600 10px var(--sans);fill:var(--pencil);letter-spacing:.04em}
  .demap text.on{fill:var(--white);font-weight:800}
  .demap .pin{fill:var(--tape);stroke:var(--white);stroke-width:2.5}
  .areas{margin-top:8px} .areas li{display:flex;gap:14px;align-items:baseline;padding:12px 0;border-top:1px solid var(--line);font-size:17px;font-weight:600} .areas li:last-child{border-bottom:1px solid var(--line)}
  .areas .k{color:var(--muted)}

  .ask .card{background:var(--white);color:var(--ink);padding:28px 22px 24px;max-width:560px;box-shadow:0 22px 40px -16px rgba(0,0,0,.6);transform:rotate(-.8deg)}
  .ask .card h3{font:800 clamp(30px,8vw,48px)/.95 var(--sans);letter-spacing:-.035em;text-transform:uppercase;margin:8px 0 12px}
  .ask .card .btns{margin-top:18px} .ask .card .btn{flex:1 1 120px}
  .ask .tel{display:block;font:800 clamp(26px,7vw,40px)/1 var(--sans);letter-spacing:-.03em;color:var(--tape);text-decoration:none;margin:4px 0 14px;font-variant-numeric:tabular-nums}
  .spec{margin:22px 0 0} .spec li{display:flex;justify-content:space-between;gap:16px;padding:9px 0;border-top:1px solid var(--line);font:600 10px/1.5 var(--mono);letter-spacing:.12em;text-transform:uppercase} .spec li span:last-child{color:var(--tape);text-align:right}

  footer{padding:30px 22px 110px;color:var(--muted);font-size:13px} footer a{color:var(--paper)}

  /* the call bar shows only when no other call button is on screen */
  .bar{position:fixed;left:0;right:0;bottom:0;z-index:30;display:flex;gap:8px;padding:10px 12px;padding-bottom:max(10px,env(safe-area-inset-bottom));background:rgba(23,25,28,.94);backdrop-filter:blur(8px);border-top:2px solid var(--tape)}
  .bar .btn{flex:1;color:var(--paper);font-size:16px} .bar .btn-solid{color:var(--white)}
  .js .bar{transform:translateY(110%);transition:transform .25s ease} .js .bar.show{transform:none}

  @media (min-width:700px){ .hero h1 .ph{display:none} }
  @media (min-width:880px){
    .hero .top{display:grid;grid-template-columns:1.15fr .85fr;gap:40px;align-items:end}
    .hero .sheet{margin:46px 0 0}
    .work .strip{flex-wrap:wrap;overflow:visible;margin:0;padding:34px 0 0} .print{flex:0 0 calc(33.333% - 18px)}
    .deck .chips{grid-template-columns:repeat(4,1fr);gap:18px}
    .about .wrap,.area .wrap{grid-template-columns:1fr 1fr;align-items:start}
    .demap{margin:0}
    .bar{display:none} footer{padding-bottom:40px}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}.js .bar{transition:none}}
</style>
</head>
<body>
<script>document.documentElement.classList.add('js')</script>

<nav class="nav">
  <a class="brand" href="#top"><b>BJB</b><span>Custom Painting</span></a>
  <a class="btn btn-solid" href="${tel}">Call ${esc(b.phone)}</a>
</nav>

<header class="hero ink" id="top">
  <div class="wrap">
    <span class="sticker">Painting &amp; drywall · ${esc(area)}</span>
    <h1><span>Every <br class="ph">surface</span><span>in the <br class="ph">house.</span></h1>
    <div class="rule"></div>
    <div class="top">
      <div>
        <p class="lede">${esc(b.about)} Free estimates — call or text, and we come out.</p>
        <div class="btns cta-row">
          <a class="btn btn-solid" href="${tel}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.2 1.8l2 .4 1 3-1.6 1.2a8 8 0 0 0 4 4l1.2-1.6 3 1 .4 2c0 .7-.6 1.4-1.4 1.4A12 12 0 0 1 1 3.2c0-.8.6-1.4 1.4-1.4z" fill="currentColor"/></svg>Call now</a>
          <a class="btn btn-solid" href="${sms(smsDefault)}">Text us</a>
        </div>
      </div>
      <div class="stats">
        ${(b.highlights || []).map((h) => `<div><b>${esc(h.value)}</b><span class="k">${esc(h.label)}</span></div>`).join('')}
      </div>
    </div>

    <div class="sheet" id="sheet">
      ${house}
      <div class="readout" id="readout">
        <span class="chipn" id="ro-chip" hidden></span>
        <span><span class="ro-name" id="ro-name">Tap any number</span><span class="ro-cat" id="ro-cat">Each one is a surface we paint. It matches a chip below.</span></span>
        <button class="ro-add" id="ro-add" type="button">Add to estimate</button>
      </div>
    </div>
  </div>
</header>

<section class="deck paper" id="deck">
  <div class="wrap">
    <span class="k">Services · the same eight numbers</span>
    <h2>What we <em>paint.</em></h2>
    <p class="lede">Every colour on these chips is from a job on this page. Tap a chip to see it on the house above, and tap again to add it to your estimate.</p>
    <form id="est" onsubmit="return false"><ol class="chips">${svc.map(chip).join('')}</ol></form>
    <p class="how k">Prices depend on the room, the surface and the prep — that is what the free visit is for.</p>
  </div>
</section>

<section class="ink" id="estimate">
  <div class="wrap">
    <span class="k">Your estimate</span>
    <h2>Send it <em>over.</em></h2>
    <div class="ask-bar">
      <p class="picked" id="picked">Nothing picked yet — a plain “when could you come out?” is fine too.</p>
      <div class="btns people">
        <a class="btn btn-solid" id="sms" href="${sms(smsDefault)}">Text the request</a>
        <a class="btn btn-solid" href="${tel}">Call ${esc(b.phone)}</a>
        ${b.email ? `<a class="btn" id="mail" href="${mail(smsDefault)}">Email instead</a>` : ''}
      </div>
    </div>
  </div>
</section>

${strip.length ? `
<section class="work paper-2" id="work">
  <div class="wrap">
    <span class="k">Recent work · his own photographs</span>
    <h2>The <em>work.</em></h2>
    <p class="lede">Rooms, exteriors and decks across Sussex County. Every picture here is a job he did.</p>
  </div>
  <div class="wrap"><div class="strip">${strip.map(print).join('')}</div></div>
</section>` : ''}

${reviews.length ? `
<section class="ink" id="reviews">
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
        <li><span class="n">03</span><span>Free estimates — we come to you</span></li>
      </ul>
    </div>
    ${fireplace ? `<figure class="print"><span class="tape" aria-hidden="true"></span>${img(fireplace, '4/3')}<figcaption>${esc(fireplace.caption || '')}</figcaption></figure>` : ''}
  </div>
</section>

<section class="area paper-2" id="area">
  <div class="wrap">
    <div>
      <span class="k">Where we work</span>
      <h2>Sussex County <em>&amp; Middletown.</em></h2>
      <p class="lede">The southern county, and Middletown up in New Castle. If you are between the two, ask.</p>
      <ul class="areas">
        <li><span class="n">01</span><span>Sussex County, DE</span><span class="k">all of it</span></li>
        <li><span class="n">02</span><span>Middletown, DE</span><span class="k">New Castle County</span></li>
      </ul>
    </div>
    <svg class="demap" viewBox="${DE.viewBox}" role="img" aria-label="Delaware's three counties: Sussex County marked, and a pin on Middletown">
      <path d="${DE.newCastle}"/><path d="${DE.kent}"/><path class="mine" d="${DE.sussex}"/>
      <text x="22" y="40">New Castle</text><text x="22" y="150">Kent</text><text class="on" x="22" y="246">Sussex</text>
      <circle class="pin" cx="54" cy="84" r="5.5"/><text x="62" y="80">Middletown</text>
      <text x="96" y="144" style="font-size:8.5px;opacity:.7">Dover</text><text x="70" y="258" style="font-size:8.5px;opacity:.85;fill:#fff">Georgetown</text>
    </svg>
  </div>
</section>

<section class="ask ink" id="contact">
  <div class="wrap">
    <span class="k">Get in touch</span>
    <div class="card bx">
      <span class="k">Free estimate</span>
      <h3>Tell us what needs painting.</h3>
      <a class="tel" href="${tel}">${esc(b.phone)}</a>
      <p>Call or text and say roughly what the job is. We come out, look at it properly, and put a number on it. No charge for the visit.</p>
      <div class="btns people">
        <a class="btn btn-solid" href="${tel}">Call</a>
        <a class="btn btn-solid" href="${sms(smsDefault)}">Text</a>
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
  <div class="wrap"><div class="pair"><span>${esc(name)} · ${esc(area)}</span>${b.social && b.social.facebook ? `<a href="${esc(b.social.facebook)}" rel="noopener">Facebook ↗</a>` : ''}</div></div>
</footer>

<div class="bar">
  <a class="btn btn-solid" href="${tel}">Call</a>
  <a class="btn" href="${sms(smsDefault)}">Text</a>
</div>

<script>
(function () {
  /* The headline runs the full width of its column, whatever face the device has. */
  var h1 = document.querySelector('.hero h1');
  function fit() {
    if (!h1) return;
    h1.style.fontSize = '100px';
    var w = 0;
    /* The lines are blocks, so measured as blocks they are the column's width,
       not the text's — and the headline came out 98px at every screen size.
       Measure each line inline, then put it back. */
    /* …and they are flex items, which are blockified, so inline-block is
       ignored too. Let them shrink to their text for the measurement. */
    h1.style.alignItems = 'flex-start';
    [].forEach.call(h1.children, function (s) { w = Math.max(w, s.getBoundingClientRect().width); });
    h1.style.alignItems = '';
    /* The wrapper's rect is its padding box; the text has to fit the content box. */
    var cs = getComputedStyle(h1.parentNode);
    var box = h1.parentNode.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    if (w > 0 && box > 0) h1.style.fontSize = Math.min(210, Math.floor(100 * box / w * 0.985)) + 'px';
  }
  fit(); addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);

  /* The call bar, only when no other call button is on screen. */
  var bar = document.querySelector('.bar');
  if (bar && 'IntersectionObserver' in window) {
    var seen = new Set();
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { e.isIntersecting ? seen.add(e.target) : seen.delete(e.target); });
      bar.classList.toggle('show', seen.size === 0);
    });
    [].forEach.call(document.querySelectorAll('.cta-row, .people'), function (el) { io.observe(el); });
  } else if (bar) { bar.classList.add('show'); }
})();

(function () {
  /* The drawing and the chips are one list in two views. */
  var house = document.querySelector('.house'), sheet = document.getElementById('sheet');
  var chipN = document.getElementById('ro-chip'), nm = document.getElementById('ro-name'), cat = document.getElementById('ro-cat');
  var add = document.getElementById('ro-add'), readout = document.getElementById('readout');
  if (!house) return;
  var idleName = nm.textContent, idleCat = cat.textContent, active = null;
  function all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function chipFor(n) { return document.querySelector('.chip[data-s="' + n + '"]'); }
  function set(n, fromList) {
    all('.is-active').forEach(function (el) { el.classList.remove('is-active'); });
    if (n === null || n === active) {
      active = null; house.classList.remove('has-active'); readout.classList.remove('live');
      chipN.hidden = true; nm.textContent = idleName; cat.textContent = idleCat; return;
    }
    active = n; house.classList.add('has-active'); readout.classList.add('live');
    all('.house .z' + n + ', .house .mk[data-s="' + n + '"], .chip[data-s="' + n + '"]').forEach(function (el) { el.classList.add('is-active'); });
    var c = chipFor(n);
    chipN.hidden = false; chipN.textContent = Number(n); chipN.style.background = getComputedStyle(c).getPropertyValue('--sw');
    nm.textContent = c.querySelector('.nm').textContent;
    cat.textContent = c.querySelector('.ds').textContent;
    add.textContent = c.querySelector('input').checked ? 'Remove from estimate' : 'Add to estimate';
    if (fromList) { var r = sheet.getBoundingClientRect(); if (r.bottom < 120 || r.top > innerHeight - 120) sheet.scrollIntoView({ block: 'start' }); }
  }
  all('.house .mk').forEach(function (m) {
    m.addEventListener('click', function (e) { e.stopPropagation(); set(m.dataset.s, false); });
    m.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); set(m.dataset.s, false); } });
  });
  house.addEventListener('click', function (e) { if (!e.target.closest('.mk')) set(null); });
  /* A chip tap shows it on the house; the checkbox itself still toggles natively. */
  all('.chip').forEach(function (c) {
    c.addEventListener('click', function () {
      var n = c.dataset.s;
      if (active !== n) { set(n, true); }
      setTimeout(function () { if (active === n) add.textContent = c.querySelector('input').checked ? 'Remove from estimate' : 'Add to estimate'; }, 0);
    });
  });
  add.addEventListener('click', function () {
    if (!active) return; var i = chipFor(active).querySelector('input'); i.checked = !i.checked;
    i.dispatchEvent(new Event('change', { bubbles: true }));
    add.textContent = i.checked ? 'Remove from estimate' : 'Add to estimate';
  });
})();

(function () {
  /* The estimate, composed as a text in a tradesman's words. */
  var form = document.getElementById('est'), picked = document.getElementById('picked');
  var sms = document.getElementById('sms'), mail = document.getElementById('mail');
  if (!form || !picked || !sms) return;
  var NAME = ${JSON.stringify(name)}, TO = ${JSON.stringify('+1' + digits)}, EMAIL = ${JSON.stringify(b.email || '')};
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
  form.addEventListener('change', update); update();
})();
</script>
</body>
</html>`;
}

module.exports = { render };
