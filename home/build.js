// Builds home/index.html, the McManus Web Co. landing page, by hand against
// DESIGN.md — rule zero applied to our own business.
//
// Concept: the ticket. Every page we ship is run through the same twelve
// checks (tools/checks.js) before the owner ever gets the link, so the
// object native to this trade is that check sheet: a paper ticket on the
// ink ground, twelve numbered rows, every one ticked in our green. The
// work is shown as it really is — full-page screenshots of pages we built,
// inside a phone, scrolling — because the pitch is "you look at it on your
// phone". The prices are the prices. Nothing on the page is a claim we
// cannot back: the checks are the real list, the screenshots are the real
// pages, the photo is Tyler.
//
// Self-contained: system fonts, inline SVG grain, every image a data URI.
// Works with JavaScript off (the phones show the top of each page; the
// scroll is a bonus). Reduced motion turns the scroll into a page step.
// Judged at 390px, survives 320px, no request leaves the page.
//
//   node home/build.js        → home/index.html

const fs = require('fs');
const path = require('path');
const CHECKS = require('../tools/checks.js');

const A = (f) => path.join(__dirname, 'assets', f);
const uri = (f) => {
  const ext = f.split('.').pop();
  const mime = { webp: 'image/webp', jpg: 'image/jpeg', png: 'image/png' }[ext];
  return `data:${mime};base64,${fs.readFileSync(A(f)).toString('base64')}`;
};
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const PHONE = '302-649-6600';
const SMS = 'sms:+13026496600';
const TEL = 'tel:+13026496600';
const MAIL = 'mailto:tylermcmanus1010@gmail.com?subject=Website%20for%20my%20business';

// Same grain as every page we ship: felt, not seen.
const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .16"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

// The work, as it really is. Each shot is a full-page capture of the page
// at phone width; the tall image scrolls inside the phone. Tags say
// exactly what each one is: a page built for a real business from their
// own material, a concept built before any conversation, or a demo.
const builds = [
  {
    file: 'shot-tinez-blendzz.webp', h: 7040, bg: '#0b0b0b',
    name: 'Barber', where: 'Norfolk, Virginia', tag: 'Built from his Booksy profile.',
    text: 'Black, gold and dark green, the way he asked. His whole menu on a board, and every cut books straight into his calendar.',
    alt: 'The barber website, a black page with gold lettering and a green price board',
  },
  {
    file: 'shot-gilman-visual-media.webp', h: 7040, bg: '#1b1816',
    name: 'Photographer', where: 'Portraits, weddings, real estate and aerial', tag: 'Built from their own site and photographs.',
    text: 'Their photographs laid out as prints on a table, their rates as index cards. Sixteen of their own pictures, none of ours.',
    alt: 'The photography website, prints on an ink table',
  },
  {
    file: 'shot-land.webp', h: 3926, bg: '#e9ede2',
    name: 'Landscaping and hardscaping crew', where: 'Delaware', tag: 'Concept build.',
    text: 'All fifteen of their services drawn onto one property plan. Tap a number and the plan shows you where that job happens.',
    alt: 'The landscaping website, a property plan with numbered services',
  },
  {
    file: 'shot-spa.webp', h: 4061, bg: '#f3f0e7',
    name: 'Hot tub and pool service', where: 'Omaha, Nebraska', tag: 'Concept build.',
    text: 'Customers tap the services they want, a bar adds them up, and the whole request goes to the owner as one text. No monthly booking fee.',
    alt: 'The pool service website, a tappable service menu',
  },
  {
    file: 'shot-plumb.webp', h: 4061, bg: '#f3f0e7',
    name: 'Plumber', where: 'San Diego', tag: 'Demo with sample details.',
    text: 'Built for the person with water on the floor. The call button is within reach of a thumb on every screen.',
    alt: 'The plumbing website, a call button within thumb reach',
  },
];
const vars = builds.map((b, i) => `--shot${i}:url("${uri(b.file)}")`).join(';');

const phone = (b, i, opts = {}) => `
      <div class="phone${opts.hero ? ' hero-phone' : ''}">
        <div class="screen" role="button" tabindex="0"${opts.auto ? ' data-auto' : ''} aria-label="${esc(b.alt)}. Press to scroll through it." style="background:${b.bg}">
          <span class="shot" style="--src:var(--shot${i});aspect-ratio:440/${b.h}"></span>
        </div>
      </div>
      <button class="play" type="button">Scroll the page<i></i></button>`;

const ticketRows = CHECKS.map((c, i) =>
  `<li><span class="n">${String(i + 1).padStart(2, '0')}</span><span class="what">${esc(c.label)}</span><span class="ok" aria-label="checked">✓</span></li>`).join('\n          ');

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://mcmanuswebco.com/">
<meta property="og:type" content="website">
<meta property="og:url" content="https://mcmanuswebco.com/">
<meta property="og:title" content="McManus Web Co. | Websites for local businesses, built before you pay">
<meta property="og:description" content="Tyler McManus builds one-page websites for local businesses in San Diego. He builds yours first, you look at it on your phone, then you decide. If you don't like it, you don't pay.">
<title>McManus Web Co. | Websites for local businesses, built before you pay</title>
<meta name="description" content="Tyler McManus builds one-page websites for local businesses. He builds yours first, you look at it on your phone, then you decide. If you don't like it, you don't pay.">
<meta name="theme-color" content="#15191A">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#15191A"/><text x="16" y="23" font-size="19" font-family="Georgia,serif" fill="#EDEEE9" text-anchor="middle">M</text><circle cx="26" cy="22" r="2.4" fill="#49B07A"/></svg>')}">
<script type="application/ld+json">
${JSON.stringify({
  '@context': 'https://schema.org', '@type': 'ProfessionalService', name: 'McManus Web Co.',
  url: 'https://mcmanuswebco.com/', telephone: '+13026496600', founder: 'Tyler McManus',
  areaServed: 'San Diego, CA', description: 'One-page websites for local businesses, built before you pay.',
  priceRange: '$750-$1500',
}, null, 1).replace(/</g, '\\u003c')}
</script>
<script>document.documentElement.className='js'</script>
<style>
  :root{
    --ink:#15191A; --ink-2:#1D2324; --bone:#EDEEE9; --bone-2:#E3E5DE; --paper:#F4F3EC;
    --green:#49B07A; --green-deep:#1F6B45; --mute:#93A09B; --rule:#2E3637;
    --line:rgba(21,25,26,.18); --line-ink:rgba(237,238,233,.16);
    --grain:url("${GRAIN}");
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --max:1120px; --gut:22px; --ease:cubic-bezier(.2,.7,.2,1);
    ${vars}
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
  body{margin:0;background:var(--ink);color:var(--bone);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit}
  p{margin:0}
  ul,ol{margin:0;padding:0;list-style:none}
  h1,h2,h3{margin:0;font-family:var(--serif);font-weight:400;letter-spacing:-.015em;line-height:1;text-wrap:balance;overflow-wrap:anywhere}
  .wrap{max-width:var(--max);margin-inline:auto;padding-inline:var(--gut)}

  /* grounds: grain and a faint grid on both, ink and bone */
  .ink,.bone{background-image:var(--grain),
    linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:220px 220px,44px 44px,44px 44px}
  .ink{background-color:var(--ink);color:var(--bone);--grid:rgba(255,255,255,.035)}
  .bone{background-color:var(--bone);color:var(--ink);--grid:rgba(21,25,26,.05)}
  section{padding-block:clamp(64px,11vw,132px)}

  /* labels: mono, tracked, small; the numbered pair */
  .k,.n{font:600 10px/1.5 var(--mono);letter-spacing:.16em;text-transform:uppercase}
  .n{color:var(--green)}
  .pair{display:flex;justify-content:space-between;gap:16px;align-items:baseline;color:var(--mute)}
  .bone .pair{color:#56625E}
  .sticker{display:inline-block;max-width:100%;background:var(--green);color:#0C1A12;font:700 10px/1.45 var(--mono);letter-spacing:.16em;
    text-transform:uppercase;padding:7px 11px 6px;box-shadow:3px 3px 0 var(--bone);transform:rotate(-1.6deg);transform-origin:left center}
  .bone .sticker{box-shadow:3px 3px 0 var(--ink)}
  .sticker.paper{background:var(--paper);color:var(--ink);border:1px solid var(--ink);transform:rotate(1.2deg);box-shadow:2px 2px 0 var(--green)}

  /* corner brackets, never a rounded card */
  .frame{position:relative;border:1px solid var(--line-ink);padding:22px 18px 20px}
  .bone .frame{border-color:var(--line)}
  .bx::before,.bx::after,.frame::before,.frame::after{content:"";position:absolute;width:14px;height:14px;border:1px solid var(--green);z-index:2}
  .frame::before{top:-1px;left:-1px;border-right:0;border-bottom:0}
  .frame::after{bottom:-1px;right:-1px;border-left:0;border-top:0}
  .bx::before{top:-1px;right:-1px;border-left:0;border-bottom:0}
  .bx::after{bottom:-1px;left:-1px;border-right:0;border-top:0}

  /* buttons: the one rounded thing, on purpose */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:.5em;min-height:52px;padding:.7em 1.4em;border-radius:999px;
    border:1.5px solid var(--green);background:var(--green);color:#0C1A12;font-weight:650;font-size:16px;text-decoration:none;white-space:nowrap}
  .btn:hover{background:#5CC58D;border-color:#5CC58D}
  .btn.ghost{background:transparent;color:inherit;border-color:currentColor;opacity:.9}
  .ink .btn.ghost:hover{background:var(--bone);color:var(--ink);border-color:var(--bone);opacity:1}
  .bone .btn.ghost:hover{background:var(--ink);color:var(--bone);border-color:var(--ink);opacity:1}
  .quiet{font-size:15.5px;color:var(--mute);text-underline-offset:4px}

  /* header */
  .top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding-block:18px}
  .mark{font-family:var(--serif);font-size:21px;line-height:1.05;text-decoration:none}
  .mark small{display:block;font-family:var(--sans);font-size:12.5px;color:var(--mute);margin-top:4px}
  .top .btn{min-height:42px;font-size:15px;padding:.45em 1.1em}

  /* hero: the headline, the ticket, the phone */
  .hero{padding-block:clamp(40px,7vw,96px) clamp(56px,9vw,112px)}
  .hero .eyebrow{display:flex;align-items:center;gap:10px;color:var(--mute)}
  .hero .eyebrow::before{content:"";width:28px;height:1px;background:var(--green)}
  .hero h1{font-size:clamp(44px,11.5vw,96px);margin-top:18px;display:flex;flex-direction:column}
  .hero h1 .then{color:var(--green);font-style:italic}
  .lede{margin-top:22px;font-size:18px;line-height:1.55;max-width:34em;color:#C9CEC8}
  .cta{display:flex;flex-wrap:wrap;gap:14px 22px;align-items:center;margin-top:28px}
  .hero-grid{display:grid;gap:clamp(40px,7vw,72px);align-items:start}

  /* the ticket: a paper check sheet on the ink */
  .ticket{position:relative;background:var(--paper);color:var(--ink);padding:20px 18px 18px;max-width:440px;
    box-shadow:0 30px 60px -24px rgba(0,0,0,.8),0 0 0 1px rgba(255,255,255,.06);transform:rotate(-.6deg)}
  .ticket .head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;border-bottom:1.5px solid var(--ink);padding-bottom:12px}
  .ticket .head b{font-family:var(--serif);font-weight:400;font-size:22px;letter-spacing:-.01em}
  .ticket .head .k{color:#56625E}
  .ticket ol{margin-top:6px}
  .ticket li{display:grid;grid-template-columns:28px 1fr 22px;align-items:baseline;gap:10px;padding:8px 0;border-bottom:1px dashed rgba(21,25,26,.28);font-size:15.5px}
  .ticket li:last-child{border-bottom:0}
  .ticket .n{color:var(--green-deep)}
  .ticket .ok{font:700 15px/1 var(--mono);color:var(--green-deep);text-align:right}
  .ticket .foot{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;padding-top:12px;border-top:1.5px solid var(--ink)}
  .ticket .foot .k{color:#56625E}
  .ticket .foot .n{white-space:nowrap;flex:0 0 auto;font-size:12px}
  .ticket .stamp{position:absolute;right:14px;top:-14px}
  .ticket .hole{position:absolute;left:50%;top:-7px;width:14px;height:14px;border-radius:50%;background:var(--ink);translate:-50% 0;box-shadow:inset 0 1px 2px rgba(0,0,0,.6)}

  /* the phone: a frame, and a screen that scrolls the real page */
  .phone{--w:min(264px,70vw);width:var(--w);margin-inline:auto;position:relative;border-radius:calc(var(--w)*.15);padding:calc(var(--w)*.035);
    background:#050606;box-shadow:0 0 0 1.5px #3A4344,0 30px 60px -20px rgba(0,0,0,.7)}
  .phone::before{content:"";position:absolute;z-index:2;top:calc(var(--w)*.06);left:50%;translate:-50% 0;width:28%;height:calc(var(--w)*.065);border-radius:99px;background:#050606}
  .screen{display:block;width:100%;aspect-ratio:9/19.3;border-radius:calc(var(--w)*.118);overflow:hidden;background:#fff;border:0;padding:calc(var(--w)*.125) 0 0;cursor:pointer;scrollbar-width:none}
  .screen::-webkit-scrollbar{display:none}
  .shot{display:block;width:100%;background:var(--src) top center/100% auto no-repeat;pointer-events:none}
  .play{display:flex;align-items:center;justify-content:center;gap:8px;margin:16px auto 0;background:none;border:0;padding:8px 12px;font-size:14.5px;color:var(--mute);cursor:pointer}
  .play i{width:26px;height:26px;border-radius:50%;border:1.5px solid currentColor;display:grid;place-items:center;font-style:normal}
  .play i::before{content:"";border-left:8px solid currentColor;border-block:5px solid transparent;margin-left:2px}
  .play.on i::before{border:0;width:8px;height:9px;margin:0;border-inline:3px solid currentColor}
  .play:hover{color:var(--bone)}
  html:not(.js) .play{display:none}

  /* how it works: the numbered steps */
  h2{font-size:clamp(38px,8vw,80px)}
  h2 em{font-style:italic;color:var(--green-deep)}
  .ink h2 em{color:var(--green)}
  .steps{margin-top:clamp(32px,5vw,64px);border-top:1.5px solid var(--ink);counter-reset:s}
  .steps li{display:grid;grid-template-columns:clamp(44px,8vw,96px) 1fr;gap:8px 16px;padding:clamp(20px,3vw,32px) 0;border-bottom:1px solid var(--line);counter-increment:s}
  .steps li::before{content:counter(s);font-family:var(--serif);font-size:clamp(40px,6vw,72px);line-height:.9;color:var(--green-deep)}
  .steps h3{font-size:clamp(24px,3vw,34px);line-height:1.15}
  .steps p{margin-top:6px;max-width:34em;color:#3B4543}
  .promise{margin-top:clamp(28px,4vw,48px);font-family:var(--serif);font-size:clamp(22px,3.2vw,30px);line-height:1.3;max-width:26em}
  .promise em{font-style:italic;color:var(--green-deep)}

  /* the work: phones on a rail */
  .work .lede{color:#C9CEC8}
  .rail{display:flex;gap:clamp(20px,4vw,48px);margin-top:clamp(32px,5vw,64px);padding:8px var(--gut) 24px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;max-width:var(--max);margin-inline:auto}
  .rail::-webkit-scrollbar{display:none}
  .build{flex:0 0 min(300px,80vw);scroll-snap-align:center}
  .build .pair{margin-bottom:14px}
  .build h3{font-size:26px;line-height:1.15;margin-top:20px}
  .build .tag{display:block;font-size:13.5px;color:var(--green);margin-top:6px}
  .build p{font-size:15.5px;line-height:1.5;color:#BFC6C0;margin-top:8px}

  /* the promise band */
  .band{padding-block:clamp(56px,9vw,104px)}
  .band .statement{font-family:var(--serif);font-size:clamp(34px,7.5vw,72px);line-height:1.05;max-width:16em}
  .band .statement em{font-style:italic;color:var(--green)}
  .band .k{display:block;margin-top:22px;color:var(--mute)}

  /* prices */
  .tiers{margin-top:clamp(28px,4vw,56px);display:grid;gap:18px}
  .tier{padding:22px 18px 20px}
  .tier header{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
  .tier h3{font-size:clamp(24px,3vw,30px);line-height:1.1}
  .tier .amt{font-family:var(--serif);font-size:clamp(30px,4.4vw,46px);line-height:1;white-space:nowrap;color:var(--green-deep)}
  .tier .amt small{font-family:var(--sans);font-size:14px;color:#56625E}
  .tier ul{margin-top:14px;color:#3B4543;font-size:15.5px}
  .tier li{padding:5px 0 5px 20px;position:relative}
  .tier li::before{content:"";position:absolute;left:2px;top:.85em;width:9px;height:1.5px;background:var(--green-deep)}

  /* about: the photo as a print, the note beside it */
  .about-grid{display:grid;gap:clamp(28px,5vw,56px);align-items:start}
  .print{position:relative;margin:0;background:var(--paper);padding:8px 8px 34px;width:min(100%,300px);transform:rotate(1.6deg);
    box-shadow:0 22px 40px -18px rgba(0,0,0,.8)}
  .print img{display:block;width:100%;height:auto;aspect-ratio:1;object-fit:cover}
  .print figcaption{position:absolute;left:0;right:0;bottom:10px;text-align:center;font:italic 15px/1.2 var(--serif);color:#3B4543}
  .note p{margin-top:16px;color:#C9CEC8;max-width:36em}
  .note p:first-child{margin-top:0}
  .sig{margin-top:22px;font:600 10px/1.8 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
  .sig b{display:block;font:italic 30px/1 var(--serif);color:var(--bone);letter-spacing:0;text-transform:none;margin-bottom:6px}

  /* contact */
  .contact h2{font-size:clamp(36px,7vw,72px)}
  .contact p{margin-top:16px;max-width:32em;color:#3B4543}
  .bar{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;gap:10px;padding:10px var(--gut) calc(10px + env(safe-area-inset-bottom));background:rgba(21,25,26,.94);border-top:1px solid var(--rule);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);transition:transform .35s var(--ease)}
  .bar .btn{flex:1;min-width:0;min-height:48px;white-space:normal;line-height:1.15;font-size:15px;text-align:center}
  .bar .btn.ghost{flex:0 0 auto;padding-inline:1.1em}
  .js .bar.off{transform:translateY(110%)}
  body{padding-bottom:78px}
  @media (min-width:860px){.bar{display:none}body{padding-bottom:0}}
  footer{padding:26px 0 calc(26px + env(safe-area-inset-bottom));font-size:13px;color:var(--mute);border-top:1px solid var(--rule)}
  footer .wrap{display:flex;flex-direction:column;gap:6px}

  /* motion: a settle, removed entirely when asked */
  .js .rise{opacity:0;transform:translateY(14px);animation:rise .9s var(--ease) forwards;animation-delay:calc(var(--i,0) * .08s)}
  @keyframes rise{to{opacity:1;transform:none}}
  @media (prefers-reduced-motion:reduce){.js .rise{animation:none;opacity:1;transform:none}html{scroll-behavior:auto}}

  @media (min-width:860px){
    .top{padding-block:26px}
    .hero-grid{grid-template-columns:1.15fr .85fr;align-items:center}
    .hero h1{font-size:clamp(60px,5.8vw,84px)}
    .ticket{margin-left:auto;transform:rotate(1deg)}
    .hero .side{display:grid;grid-template-columns:1fr auto;gap:28px;align-items:end}
    .rail{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));overflow:visible;padding-bottom:0}
    .build{flex-basis:auto}
    .tiers{grid-template-columns:repeat(3,1fr)}
    .about-grid{grid-template-columns:320px 1fr}
    footer .wrap{flex-direction:row;justify-content:space-between}
  }
  @media (max-width:340px){.hero h1{font-size:40px}.ticket li{font-size:14px}}
</style>
</head>
<body>

<header class="wrap top">
  <a class="mark" href="#top">McManus Web Co.<small>Websites for local businesses, San Diego</small></a>
  <a class="btn" href="${SMS}">Text me</a>
</header>

<main id="top">

<section class="hero ink">
  <div class="wrap hero-grid">
    <div>
      <span class="eyebrow k rise" style="--i:0">Web design · San Diego · Built before you pay</span>
      <h1 class="rise" style="--i:1"><span>I build your website first.</span><span class="then">Then you decide.</span></h1>
      <p class="lede rise" style="--i:2">I'm Tyler. I make one-page websites for local businesses. Yours gets built before we ever talk money, you open it on your phone, and if you don't like it, you don't pay.</p>
      <div class="cta rise" style="--i:3">
        <a class="btn" href="${SMS}">Text me your business name</a>
        <a class="quiet" href="#work">See what I've built</a>
      </div>
    </div>
    <div class="side">
      <div class="ticket rise" style="--i:2">
        <span class="hole" aria-hidden="true"></span>
        <span class="sticker stamp">Checked before you get the link</span>
        <div class="head"><b>The twelve checks</b><span class="k">Every page</span></div>
        <ol>
          ${ticketRows}
        </ol>
        <div class="foot"><span class="k">Run on your site before I build, and on mine before I send it</span><span class="n">12 / 12</span></div>
      </div>
    </div>
  </div>
</section>

<section class="how bone" id="how">
  <div class="wrap">
    <div class="pair"><span class="n">01</span><span class="k">How it works</span></div>
    <h2>Start to <em>finish.</em></h2>
    <ol class="steps">
      <li><div><h3>You text me your business name.</h3><p>That's all I need. If you already have a website, I'll look at what's hurting it, usually how it loads and reads on a phone.</p></div></li>
      <li><div><h3>I build your new site.</h3><p>The real thing, with your services, your area and your phone number on it. Not a mockup, not a template with your logo dropped in.</p></div></li>
      <li><div><h3>You open it on your phone.</h3><p>That's where your customers will see it, so that's where you should judge it. Tap around. Show your spouse. Take your time.</p></div></li>
      <li><div><h3>You decide.</h3><p>If you want it, I put it live on your own domain in 5 business days. If you don't, that's the end of it.</p></div></li>
    </ol>
    <p class="promise">If you don't like it, <em>you don't pay</em>, and you keep the page anyway.</p>
  </div>
</section>

<section class="work ink" id="work">
  <div class="wrap">
    <div class="pair"><span class="n">02</span><span class="k">The work</span></div>
    <h2>Every business gets <em>its own design.</em></h2>
    <p class="lede">These are the actual pages, scrolling inside a phone. A barber's price board, a photographer's prints on a table, a landscaper's property plan. Nothing here started from a template.</p>
  </div>
  <div class="rail">
    ${builds.map((b, i) => `<article class="build">
      ${phone(b, i, { auto: i === 0 })}
      <h3>${esc(b.name)}</h3><span class="tag">${esc(b.where)}. ${esc(b.tag)}</span>
      <p>${esc(b.text)}</p>
    </article>`).join('\n    ')}
  </div>
</section>

<section class="band ink" aria-label="The promise">
  <div class="wrap">
    <p class="statement">You never get a sales deck from me. <em style="white-space:nowrap">Just a link.</em></p>
    <span class="k">Then it's your call.</span>
  </div>
</section>

<section class="price bone" id="price">
  <div class="wrap">
    <div class="pair"><span class="n">03</span><span class="k">What it costs</span></div>
    <h2>The <em>prices.</em></h2>
    <div class="tiers">
      <div class="tier frame"><span class="bx" aria-hidden="true"></span>
        <header><h3>One-page website</h3><span class="amt">$750</span></header>
        <ul><li>The page you saw, live on your own domain</li><li>Phone, tablet and desktop</li><li>Google business markup, so your hours and rating show in search</li><li>Two rounds of changes</li><li>Live in 5 business days</li></ul>
      </div>
      <div class="tier frame"><span class="bx" aria-hidden="true"></span>
        <header><h3>Website plus booking</h3><span class="amt">$1,500</span></header>
        <ul><li>Everything in the one-page website</li><li>A separate page per service, for local search</li><li>Online booking or a quote form sent to your email</li><li>Photo gallery</li><li>Live in 10 business days</li></ul>
      </div>
      <div class="tier frame"><span class="bx" aria-hidden="true"></span>
        <header><h3>Hosting and updates, if you want them</h3><span class="amt">$60<small> /month</small></span></header>
        <ul><li>Hosting, SSL and backups</li><li>Unlimited small text and price changes</li><li>Cancel any time</li></ul>
      </div>
    </div>
  </div>
</section>

<section class="about ink" id="about">
  <div class="wrap about-grid">
    <figure class="print"><img src="${uri('tyler.jpg')}" alt="Tyler McManus" width="720" height="720"><figcaption>Tyler, San Diego</figcaption></figure>
    <div class="note">
      <div class="pair" style="margin-bottom:18px"><span class="n">04</span><span class="k">Who you're dealing with</span></div>
      <p>I'm Tyler McManus. I look at a lot of local business websites, and most of them have the same problems: slow on a phone, hard to read, a phone number you can't tap. Good businesses, bad first impression.</p>
      <p>So I flipped the usual order. I do the work first and let it make the case. You'll never get a sales deck from me, just a link.</p>
      <p>When you text the number below, I'm the one who answers.</p>
      <div class="sig"><b>Tyler</b>McManus Web Co.<br>${PHONE}</div>
    </div>
  </div>
</section>

<section class="contact bone" id="contact">
  <div class="wrap">
    <div class="pair"><span class="n">05</span><span class="k">Want to see yours?</span></div>
    <h2>Text me your <em>business name.</em></h2>
    <p>Or a link to your current site. No cost to look.</p>
    <div class="cta">
      <a class="btn" href="${SMS}">Text ${PHONE}</a>
      <a class="btn ghost" href="${TEL}">Call</a>
      <a class="btn ghost" href="${MAIL}">Email</a>
    </div>
  </div>
</section>

</main>

<div class="bar" id="bar"><a class="btn" href="${SMS}">Text me your business name</a><a class="btn ghost" href="${TEL}" aria-label="Call ${PHONE}">Call</a></div>

<footer class="ink"><div class="wrap"><span>McManus Web Co. Tyler McManus, San Diego.</span><span>No trackers on this page. It loads the way yours will.</span></div></footer>

<script>
(function(){
  var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  var running=null;
  function stop(){ if(!running)return; cancelAnimationFrame(running.raf); running.btn.classList.remove('on'); running.btn.firstChild.nodeValue='Scroll the page'; running=null; }
  function play(screen,btn){
    if(running&&running.screen===screen){stop();return;}
    stop();
    var max=screen.scrollHeight-screen.clientHeight; if(max<=0)return;
    if(screen.scrollTop>=max-2)screen.scrollTop=0;
    if(reduce){ screen.scrollTop=Math.min(max,screen.scrollTop+screen.clientHeight*.9); return; }
    btn.classList.add('on'); btn.firstChild.nodeValue='Pause';
    var last=null,speed=max/16000;
    running={screen:screen,btn:btn,raf:0};
    (function step(t){
      if(!running||running.screen!==screen)return;
      if(last!==null){screen.scrollTop+=Math.max(.5,(t-last)*speed);}
      last=t;
      if(screen.scrollTop>=max-1){stop();return;}
      running.raf=requestAnimationFrame(step);
    })(performance.now());
  }
  [].forEach.call(document.querySelectorAll('.phone'),function(ph){
    var screen=ph.querySelector('.screen'),btn=ph.parentNode.querySelector('.play');
    screen.style.overflowY='auto';
    if(reduce&&btn)btn.firstChild.nodeValue='Next screen';
    screen.addEventListener('click',function(){play(screen,btn);});
    screen.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();play(screen,btn);}});
    if(btn)btn.addEventListener('click',function(){play(screen,btn);});
  });
  var bar=document.getElementById('bar'),cta=document.querySelector('.hero .cta');
  if(bar&&cta&&'IntersectionObserver' in window){ bar.classList.add('off'); new IntersectionObserver(function(es){ bar.classList.toggle('off',es[0].isIntersecting||es[0].boundingClientRect.top>0); }).observe(cta); }
  var auto=document.querySelector('.screen[data-auto]');
  if(auto&&!reduce){
    var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting&&!running){ play(auto,auto.parentNode.parentNode.querySelector('.play')); io.disconnect(); } }); },{threshold:.6});
    io.observe(auto);
  }
})();
</script>
</body>
</html>
`;

fs.writeFileSync(path.join(__dirname, 'index.html'), html);
console.log(`home/index.html written, ${Math.round(html.length / 1024)}KB, ${builds.length} pages in the phones`);
