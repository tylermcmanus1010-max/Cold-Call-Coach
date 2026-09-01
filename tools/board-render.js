// Renders the call board to a single self-contained page.
//
// It is a dialling instrument, not a report: it gets read with a thumb, in the
// four seconds before a call connects. So the score is drawn as seven lamps
// rather than a percentage, because it *is* seven discrete provable checks —
// and a row shows the one sentence Tyler can say out loud, not a list of
// findings he has to triage himself while the phone rings.

const { HARD, SOFT, esc, digits } = require('./board');

const FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap';

function lamps(row) {
  // A parked domain's checks describe the placeholder, not the business. Two
  // of Alexander's lamps lit green beside a score of 0/7 — the checks had
  // passed on a registrar's holding page. Nothing about their site was
  // measured, so nothing is claimed.
  if (row.parked) {
    return HARD.map((c) =>
      `<i class="lamp na" title="${esc(c.label)}: not measured — the domain is parked"></i>`).join('');
  }
  return HARD.map((c) => {
    const ok = row.audit && row.audit[c.key] === true;
    return `<i class="lamp ${ok ? 'on' : 'off'}" title="${esc(c.label)}: ${ok ? 'passes' : 'fails'}"></i>`;
  }).join('');
}

function contact(row) {
  const bits = [];
  if (row.phone) {
    bits.push(`<a class="btn call" href="tel:+1${esc(digits(row.phone))}">${esc(row.phone)}</a>`);
  } else {
    bits.push('<span class="none">no number</span>');
  }
  // An address we do not hold is not an address we may invent. Six weeks of
  // this project has one hard bounce per guess to show for it.
  if (row.email) {
    bits.push(`<a class="btn mail" href="mailto:${esc(row.email)}">${esc(row.email)}</a>`);
  } else {
    bits.push('<span class="none">no email — ask on the call</span>');
  }
  return bits.join('');
}

function rowHtml(row, i) {
  const flaw = row.flaw;
  const where = [row.city, row.state + (row.stateDerived ? '*' : '')].filter(Boolean).join(', ');
  const site = row.site
    ? `<a class="site" href="${esc(row.site)}" target="_blank" rel="noopener noreferrer">${esc(row.site.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''))}</a>`
    : '<span class="none">no website found</span>';

  const tags = [];
  if (row.parked) tags.push('<span class="tag hot">no website — domain parked</span>');
  if (row.blocked) tags.push(`<span class="tag stop">${esc(row.blocked)}</span>`);
  if (row.checkUrl) tags.push('<span class="tag warn">open this first — the domain may not be theirs</span>');
  if (!row.rendered) tags.push('<span class="tag soft">not browser-measured</span>');
  if (row.status && row.status !== 'new') tags.push(`<span class="tag st-${esc(row.status)}">${esc(row.status)}</span>`);
  if (row.built) tags.push('<span class="tag ok">page built</span>');

  return `
<article class="row${row.blocked ? ' is-blocked' : ''}" data-state="${esc(row.state || '?')}" data-src="${esc(row.source)}" data-blocked="${row.blocked ? '1' : '0'}" data-score="${row.passed}" data-name="${esc((row.name + ' ' + row.category + ' ' + where).toLowerCase())}">
  <div class="idx">${i + 1}</div>
  <div class="who">
    <h3>${esc(row.name)}</h3>
    <p class="meta">${esc(row.category || 'business')}${where ? ' · ' + esc(where) : ''}${row.owner ? ' · ' + esc(row.owner) : ''}</p>
    <div class="tags">${tags.join('')}</div>
  </div>
  <div class="score">
    <div class="lampstrip">${lamps(row)}</div>
    <span class="num">${row.parked ? '<span class="of">no site</span>' : row.passed + `<span class="of">/${row.of}</span>`}</span>
  </div>
  <div class="flaw">
    ${flaw
      ? `<p class="flabel">${esc(flaw.label)}</p><p class="fwhy">${esc(flaw.why)}</p>`
      : '<p class="flabel none">Nothing provable to sell</p><p class="fwhy">All seven checks pass. Do not pitch a rebuild.</p>'}
  </div>
  <div class="reach">${contact(row)}${site}</div>
</article>`;
}

module.exports = function render(rows, meta) {
  const callable = rows.filter((r) => !r.blocked);
  const states = [...new Set(rows.map((r) => r.state).filter(Boolean))].sort();
  const byState = states.map((s) => [s, rows.filter((r) => r.state === s).length]);

  const tally = (list) => ({
    total: list.length,
    callable: list.filter((r) => !r.blocked).length,
    phones: list.filter((r) => r.phone).length,
    emails: list.filter((r) => r.email).length,
  });
  const all = tally(rows);

  return `<title>Call Board</title>
<link rel="stylesheet" href="${FONTS}">
<style>
  :root{
    --ground:#F4F6F6; --surface:#FFFFFF; --sunk:#EAEEEE;
    --ink:#10181B; --ink-2:#3C4A4F; --muted:#68787D; --line:#D6DEDF;
    --accent:#0B5E6B; --accent-soft:#E2EFF1; --on-accent:#FFFFFF;
    --bad:#B3261E; --warn:#8A5A0B; --good:#1F6B3F;
    --lamp-off:#CFD8D9;
    --radius:8px;
    --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    --ui:"Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --ground:#0D1315; --surface:#151F22; --sunk:#101A1C;
      --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#86989C; --line:#27383C;
      --accent:#5FB9C9; --accent-soft:#122E34; --on-accent:#08191C;
      --bad:#F1867C; --warn:#E0B056; --good:#67C08C;
      --lamp-off:#2C3E42;
    }
  }
  :root[data-theme="dark"]{
    --ground:#0D1315; --surface:#151F22; --sunk:#101A1C;
    --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#86989C; --line:#27383C;
    --accent:#5FB9C9; --accent-soft:#122E34; --on-accent:#08191C;
    --bad:#F1867C; --warn:#E0B056; --good:#67C08C;
    --lamp-off:#2C3E42;
  }

  *{box-sizing:border-box}
  body{background:var(--ground);color:var(--ink);font-family:var(--ui);line-height:1.45;margin:0;-webkit-text-size-adjust:100%}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 18px 80px}

  header.top{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;justify-content:space-between;padding-bottom:18px;border-bottom:2px solid var(--ink)}
  h1{font-size:clamp(28px,5vw,40px);font-weight:700;letter-spacing:-.02em;margin:0;text-wrap:balance}
  .sub{color:var(--muted);font-size:14px;margin:4px 0 0;max-width:62ch}
  .sub code{font-family:var(--mono);font-size:12px}
  .stamp{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}

  .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:18px 0 22px}
  .tile{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px}
  .tile b{display:block;font-family:var(--mono);font-size:26px;font-weight:500;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .tile span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-top:2px}
  .tile.hero{background:var(--accent-soft);border-color:var(--accent)}
  .tiles.states{grid-template-columns:repeat(auto-fit,minmax(72px,1fr));margin:-12px 0 22px}
  .tiles.states .tile{padding:8px 10px;background:var(--sunk)}
  .tiles.states b{font-size:18px}
  .tile.hero b{color:var(--accent)}

  .controls{position:sticky;top:0;z-index:5;background:var(--ground);padding:10px 0 12px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
  input[type=search]{flex:1 1 220px;min-width:0;font:inherit;font-size:15px;padding:9px 12px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--ink)}
  .chip{font:inherit;font-size:13px;font-weight:500;padding:8px 12px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--ink-2);cursor:pointer;-webkit-appearance:none;appearance:none}
  .chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
  .chip:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  .count{font-family:var(--mono);font-size:12px;color:var(--muted);margin-left:auto}

  h2.sec{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:30px 0 10px;font-weight:600}

  .row{display:grid;grid-template-columns:34px minmax(180px,1.5fr) 118px minmax(190px,1.4fr) minmax(190px,1.2fr);gap:14px;align-items:start;
       background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:var(--radius);padding:12px 14px;margin-bottom:7px}
  .row.is-blocked{border-left-color:var(--lamp-off);opacity:.62}
  .idx{font-family:var(--mono);font-size:12px;color:var(--muted);padding-top:3px;font-variant-numeric:tabular-nums}
  .who h3{font-size:16px;font-weight:600;margin:0;letter-spacing:-.01em;text-wrap:balance}
  .meta{font-size:12.5px;color:var(--muted);margin:2px 0 0}
  .tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
  .tag{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;border-radius:4px;background:var(--sunk);color:var(--muted)}
  .tag.stop{background:var(--bad);color:var(--surface)}
  .tag.ok{background:var(--good);color:var(--surface)}
  .tag.hot{background:var(--accent);color:var(--on-accent)}
  .tag.warn{background:var(--warn);color:var(--surface)}
  .tag.st-sent,.tag.st-replied{background:var(--warn);color:var(--surface)}

  .lampstrip{display:flex;gap:3px}
  .lamp{width:11px;height:11px;border-radius:2px;background:var(--lamp-off);display:block}
  .lamp.on{background:var(--good)}
  .lamp.na{background:transparent;border:1px dashed var(--line)}
  .score .num{font-family:var(--mono);font-size:15px;font-weight:500;display:block;margin-top:5px;font-variant-numeric:tabular-nums}
  .score .of{color:var(--muted);font-size:12px}

  .flabel{font-size:14px;font-weight:600;margin:0;color:var(--bad)}
  .flabel.none{color:var(--good)}
  .fwhy{font-size:12.5px;color:var(--ink-2);margin:3px 0 0}

  .reach{display:flex;flex-direction:column;gap:5px;align-items:flex-start}
  .btn{font-family:var(--mono);font-size:13px;text-decoration:none;padding:5px 9px;border-radius:6px;border:1px solid var(--line);color:var(--ink);background:var(--sunk);display:inline-block}
  .btn.call{background:var(--accent);border-color:var(--accent);color:var(--on-accent);font-weight:500}
  .site{font-size:12px;color:var(--accent);word-break:break-all}
  .none{font-size:12px;color:var(--muted);font-style:italic}

  .advice{margin-top:44px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px}
  .advice h2{font-size:20px;margin:0 0 4px;letter-spacing:-.01em}
  .advice h3{font-size:14px;margin:20px 0 4px;color:var(--accent);letter-spacing:.01em}
  .advice p,.advice li{font-size:14px;color:var(--ink-2);max-width:68ch}
  .advice li{margin-bottom:6px}
  .advice strong{color:var(--ink)}

  @media (max-width:860px){
    .row{grid-template-columns:26px 1fr;gap:8px 10px}
    .idx{grid-row:1}
    .who{grid-column:2}
    .score,.flaw,.reach{grid-column:2}
    .score{display:flex;align-items:center;gap:10px}
    .score .num{margin:0}
    .reach{flex-direction:row;flex-wrap:wrap;align-items:center}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="wrap">
  <header class="top">
    <div>
      <h1>Call Board</h1>
      <p class="sub">Every business we have measured, ranked by how much there is to honestly say. Seven lamps = the seven checks that can be proved in a browser and repeated to an owner. A state marked <code>*</code> was read off the area code, not the listing.</p>
    </div>
    <div class="stamp">${esc(meta.builtAt)}<br>McManus Web Co.</div>
  </header>

  <div class="tiles">
    <div class="tile hero"><b>${all.callable}</b><span>worth calling</span></div>
    <div class="tile"><b>${all.total}</b><span>measured</span></div>
    <div class="tile"><b>${all.phones}</b><span>have a number</span></div>
    <div class="tile"><b>${all.emails}</b><span>have an email</span></div>
  </div>
  <div class="tiles states">
    ${byState.map(([s, n]) => `<div class="tile"><b>${n}</b><span>${esc(s)}</span></div>`).join('')}
  </div>

  <div class="controls">
    <input type="search" id="q" placeholder="Search name, trade or town…" aria-label="Search the board">
    <button class="chip" id="onlyCallable" aria-pressed="true">Callable only</button>
    ${states.map((s) => `<button class="chip st" data-st="${esc(s)}" aria-pressed="false">${esc(s)}</button>`).join('')}
    <span class="count" id="count"></span>
  </div>

  <h2 class="sec">Ranked — most broken first</h2>
  <div id="list">
${rows.map(rowHtml).join('')}
  </div>

  <section class="advice">
    <h2>What the numbers are actually telling you</h2>
    ${meta.advice}
  </section>
</div>

<script>
(function(){
  var rows = [].slice.call(document.querySelectorAll('.row'));
  var q = document.getElementById('q');
  var only = document.getElementById('onlyCallable');
  var count = document.getElementById('count');
  var stateBtns = [].slice.call(document.querySelectorAll('.chip.st'));
  var active = {};

  try {
    var saved = JSON.parse(localStorage.getItem('board.filters') || '{}');
    if (saved.only === false) only.setAttribute('aria-pressed','false');
    if (saved.q) q.value = saved.q;
    if (saved.states) { active = saved.states; stateBtns.forEach(function(b){
      if (active[b.dataset.st]) b.setAttribute('aria-pressed','true'); }); }
  } catch (e) {}

  function save(){
    try {
      localStorage.setItem('board.filters', JSON.stringify({
        only: only.getAttribute('aria-pressed') === 'true', q: q.value, states: active }));
    } catch (e) {}
  }

  function apply(){
    var term = q.value.trim().toLowerCase();
    var callableOnly = only.getAttribute('aria-pressed') === 'true';
    var picked = Object.keys(active).filter(function(k){ return active[k]; });
    var shown = 0;
    rows.forEach(function(r){
      var ok = true;
      if (callableOnly && r.dataset.blocked === '1') ok = false;
      if (ok && term && r.dataset.name.indexOf(term) === -1) ok = false;
      if (ok && picked.length && picked.indexOf(r.dataset.state) === -1) ok = false;
      r.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown + ' of ' + rows.length;
    save();
  }

  q.addEventListener('input', apply);
  only.addEventListener('click', function(){
    only.setAttribute('aria-pressed', only.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    apply();
  });
  stateBtns.forEach(function(b){
    b.addEventListener('click', function(){
      var on = b.getAttribute('aria-pressed') !== 'true';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      active[b.dataset.st] = on;
      apply();
    });
  });

  apply();
})();
</script>`;
};
