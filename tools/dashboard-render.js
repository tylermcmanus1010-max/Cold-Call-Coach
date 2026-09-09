// Renders the morning dashboard as one self-contained page: two tabs, a
// thumb-width card per business, nothing that needs a server.
//
// It is read on a phone between calls, so every card answers "who, what
// happened, what do I tap" in the first line, and the only live thing on the
// page — whether a business is answering the phone right now — is computed
// in the browser from the time windows brief.js already knows, because a
// page built at 6:30 is wrong about that by 7:00.

const { HARD, esc, digits } = require('./board');
const { fmt } = require('./dashboard');

const FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap';

const tel = (phone) => `tel:+1${esc(digits(phone).replace(/^1(?=\d{10}$)/, ''))}`;
const host = (url) => String(url || '').replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
const where = (r) => [r.city, r.state ? r.state + (r.stateDerived ? '*' : '') : ''].filter(Boolean).join(', ');

function lamps(row) {
  if (row.parked) return HARD.map((c) => `<i class="lamp na" title="${esc(c.label)}: not measured — the domain is parked"></i>`).join('');
  return HARD.map((c) => {
    const ok = row.audit && row.audit[c.key] === true;
    return `<i class="lamp ${ok ? 'on' : 'off'}" title="${esc(c.label)}: ${ok ? 'passes' : 'fails'}"></i>`;
  }).join('');
}

// "Our page" is only a link when it will open. Built-on-a-branch is a real
// state Tyler needs to see, not a 404 in front of an owner.
function pageLink(r) {
  if (!r.built) return '<span class="none">no page built yet</span>';
  if (!r.pageUrl) return '<span class="none">page built — no hosting domain set</span>';
  if (r.live === true) return `<a class="btn page" href="${esc(r.pageUrl)}" target="_blank" rel="noopener noreferrer">Our page <b>live</b></a>`;
  if (r.live === false) return `<span class="btn page off" title="${esc(r.pageUrl)}">Our page <b>built, not live yet</b></span>`;
  return `<a class="btn page" href="${esc(r.pageUrl)}" target="_blank" rel="noopener noreferrer">Our page <b>unchecked</b></a>`;
}

function siteLink(r) {
  return r.site
    ? `<a class="btn" href="${esc(r.site)}" target="_blank" rel="noopener noreferrer">Their site <span class="host">${esc(host(r.site))}</span></a>`
    : '<span class="none">no website found</span>';
}

function gapsHtml(gaps) {
  if (!gaps || !gaps.length) return '';
  return `<p class="gaps">Page still needs: ${gaps.map((g) => `<b>${esc(g)}</b>`).join(' ')}</p>`;
}

function contactedCard(c) {
  const o = c.outcome;
  const reach = [];
  if (c.phone) reach.push(`<a class="btn call" href="${tel(c.phone)}">${esc(c.phone)}</a>`);
  else reach.push('<span class="none">no number</span>');
  if (c.suppressed) reach.push(`<span class="btn stop" title="${esc(c.suppressed.reason)}">do not contact</span>`);
  else if (c.email) reach.push(`<a class="btn" href="mailto:${esc(c.email)}">${esc(c.email)}</a>`);
  else reach.push('<span class="none">no email on file</span>');
  const thread = c.sends.filter((s) => s.thread).slice(-1)[0];
  if (thread) reach.push(`<a class="btn" href="${esc(thread.thread)}" target="_blank" rel="noopener noreferrer">Gmail thread</a>`);

  const tags = [];
  if (c.warm) tags.push('<span class="tag hot">warm — hand-written pitch on file</span>');
  if (c.followUp) tags.push(`<span class="tag ${c.followUp.overdue ? 'stop' : 'warn'}">${esc(c.followUp.overdue ? 'overdue' : 'due')} · ${esc(c.followUp.why)}</span>`);

  return `
<article class="card" id="c-${esc(c.slug)}" data-k="${esc(o.key)}" data-name="${esc((c.name + ' ' + c.category + ' ' + where(c) + ' ' + c.email).toLowerCase())}">
  <div class="head">
    <div>
      <h3>${esc(c.name)}</h3>
      <p class="meta">${esc(c.category || 'business')}${where(c) ? ' · ' + esc(where(c)) : ''}</p>
    </div>
    <span class="chip ${esc(o.tone)}">${esc(o.label)}</span>
  </div>
  ${tags.length ? `<div class="tags">${tags.join('')}</div>` : ''}
  ${c.line ? `<p class="line">${esc(c.line)}</p>` : ''}
  <div class="reach">${reach.join('')}</div>
  <div class="reach pages">${pageLink(c)}${siteLink(c)}</div>
  ${gapsHtml(c.gaps)}
  ${c.lastNote ? `<details><summary>Last note</summary><p class="note">${esc(c.lastNote)}</p></details>` : ''}
</article>`;
}

function nextCard(n) {
  const flaw = n.flaw;
  const tags = [];
  if (n.checkUrl) tags.push('<span class="tag warn">open their site first — the domain may not be theirs</span>');
  if (!n.rendered && !n.parked) tags.push('<span class="tag soft">not browser-measured</span>');
  const w = n.window;

  return `
<article class="card next" id="n-${esc(n.slug)}" data-state="${esc(n.state || '?')}" data-built="${n.built ? '1' : '0'}" data-tz="${esc(w.tz || '')}" data-slots="${esc(JSON.stringify(w.slots))}" data-name="${esc((n.name + ' ' + n.category + ' ' + where(n)).toLowerCase())}">
  <div class="head">
    <div class="rank">${n.rank}</div>
    <div class="grow">
      <h3>${esc(n.name)}</h3>
      <p class="meta">${esc(n.category || 'business')}${where(n) ? ' · ' + esc(where(n)) : ''}</p>
    </div>
    <span class="chip now" data-now="unknown">checking…</span>
  </div>
  <div class="score">
    <span class="lampstrip">${lamps(n)}</span>
    <span class="num">${n.parked ? 'no site' : `${n.passed}<span class="of">/${n.of}</span>`}</span>
    ${flaw ? `<span class="flabel">${esc(flaw.label)}</span>` : '<span class="flabel ok">nothing provable to sell</span>'}
  </div>
  ${flaw ? `<p class="fwhy">${esc(flaw.why)}</p>` : ''}
  ${tags.length ? `<div class="tags">${tags.join('')}</div>` : ''}
  <div class="reach">
    ${n.phone ? `<a class="btn call" href="${tel(n.phone)}">${esc(n.phone)}</a>` : '<span class="none">no number</span>'}
    ${n.email ? `<a class="btn" href="mailto:${esc(n.email)}">${esc(n.email)}</a>` : '<span class="none">no email — ask on the call</span>'}
  </div>
  <div class="reach pages">${pageLink(n)}${siteLink(n)}</div>
  ${gapsHtml(n.gaps)}
  <p class="win"><b>${esc(w.name === 'business' ? 'Best time' : w.name[0].toUpperCase() + w.name.slice(1))}:</b> ${esc(w.text)} their time — ${esc(w.why)}.</p>
</article>`;
}

function dueItem(f) {
  const when = f.overdue ? `was due ${fmt(f.at)}` : f.today ? 'today' : fmt(f.at);
  return `<li class="${f.overdue ? 'overdue' : ''}">
  ${f.phone ? `<a class="btn call" href="${tel(f.phone)}">${esc(f.phone)}</a>` : '<span class="none">no number</span>'}
  <div>
    <a class="who" href="#c-${esc(f.slug)}">${esc(f.name)}</a>
    <span class="why">${esc(f.why)}${f.time ? ' · ' + esc(f.time) : ''} — <b>${esc(when)}</b></span>
  </div>
</li>`;
}

function render(d) {
  const s = d.stats;
  const states = [...new Set(d.next.map((n) => n.state).filter(Boolean))].sort();
  const built = d.next.filter((n) => n.built).length;

  const head = `<title>Cold Call Pipeline</title>
<link rel="stylesheet" href="${FONTS}">
<style>
  :root{
    --ground:#F4F6F6; --surface:#FFFFFF; --sunk:#EAEEEE;
    --ink:#10181B; --ink-2:#3C4A4F; --muted:#68787D; --line:#D6DEDF;
    --accent:#0B5E6B; --accent-soft:#E2EFF1; --on-accent:#FFFFFF;
    --bad:#B3261E; --bad-soft:#F7E3E1; --warn:#8A5A0B; --warn-soft:#F5EBD6; --good:#1F6B3F; --good-soft:#DFEFE5;
    --lamp-off:#CFD8D9; --radius:8px;
    --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    --ui:"Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --ground:#0D1315; --surface:#151F22; --sunk:#101A1C;
      --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#86989C; --line:#27383C;
      --accent:#5FB9C9; --accent-soft:#122E34; --on-accent:#08191C;
      --bad:#F1867C; --bad-soft:#3A1F1D; --warn:#E0B056; --warn-soft:#3A2E12; --good:#67C08C; --good-soft:#143224;
      --lamp-off:#2C3E42;
    }
  }
  :root[data-theme="dark"]{
    --ground:#0D1315; --surface:#151F22; --sunk:#101A1C;
    --ink:#E7EEEF; --ink-2:#B4C3C6; --muted:#86989C; --line:#27383C;
    --accent:#5FB9C9; --accent-soft:#122E34; --on-accent:#08191C;
    --bad:#F1867C; --bad-soft:#3A1F1D; --warn:#E0B056; --warn-soft:#3A2E12; --good:#67C08C; --good-soft:#143224;
    --lamp-off:#2C3E42;
  }

  *{box-sizing:border-box}
  body{background:var(--ground);color:var(--ink);font-family:var(--ui);line-height:1.45;margin:0;-webkit-text-size-adjust:100%}
  a{color:var(--accent)}
  .wrap{max-width:1100px;margin:0 auto;padding:22px 16px 90px}

  header.top{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:flex-end;justify-content:space-between;padding-bottom:14px;border-bottom:2px solid var(--ink)}
  h1{font-size:clamp(24px,5vw,34px);font-weight:700;letter-spacing:-.02em;margin:0;text-wrap:balance}
  .sub{color:var(--muted);font-size:13.5px;margin:4px 0 0;max-width:64ch}
  .stamp{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right;line-height:1.5}

  .tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:16px 0 18px}
  @media (min-width:700px){.tiles{grid-template-columns:repeat(6,1fr)}}
  .tile{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:10px 12px;min-width:0}
  .tile b{display:block;font-size:26px;font-weight:600;letter-spacing:-.02em;line-height:1.1}
  .tile b small{font-size:13px;font-weight:500;color:var(--muted);letter-spacing:0}
  .tile span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-top:4px;line-height:1.3}
  .tile.hero{background:var(--accent-soft);border-color:var(--accent)}
  .tile.hero b{color:var(--accent)}
  .tile.due b{color:var(--warn)}
  .tile.due.zero b{color:var(--muted)}

  .tabs{position:sticky;top:0;z-index:5;background:var(--ground);padding:8px 0 10px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
  [role=tab]{font:inherit;font-size:14px;font-weight:600;padding:9px 14px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--ink-2);cursor:pointer;-webkit-appearance:none;appearance:none}
  [role=tab] em{font-style:normal;font-family:var(--mono);font-weight:500;font-size:12px;margin-left:6px;opacity:.75}
  [role=tab][aria-selected="true"]{background:var(--ink);border-color:var(--ink);color:var(--ground)}
  input[type=search]{flex:1 1 180px;min-width:0;font:inherit;font-size:15px;padding:9px 12px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--ink)}
  .count{font-family:var(--mono);font-size:12px;color:var(--muted);margin-left:auto;white-space:nowrap}
  [role=tab]:focus-visible,input:focus-visible,a:focus-visible,.fchip:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

  .filters{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px}
  .fchip{font:inherit;font-size:12.5px;font-weight:500;padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink-2);cursor:pointer;-webkit-appearance:none;appearance:none}
  .fchip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}

  h2.sec{font-size:12.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:22px 0 8px;font-weight:600;display:flex;align-items:center;gap:8px}
  h2.sec::after{content:"";flex:1;height:1px;background:var(--line)}
  .lede{color:var(--muted);font-size:13px;margin:0 0 10px;max-width:70ch}

  .owed{background:var(--surface);border:1px solid var(--warn);border-left:4px solid var(--warn);border-radius:var(--radius);padding:12px 14px;margin:14px 0 6px}
  .owed h2{font-size:14px;margin:0 0 8px;letter-spacing:-.01em}
  .owed ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
  .owed li{display:flex;gap:10px;align-items:flex-start}
  .owed .who{font-weight:600;color:var(--ink);text-decoration:none;display:block}
  .owed .why{font-size:12.5px;color:var(--ink-2)}
  .owed li.overdue .why b{color:var(--bad)}

  .grid{display:grid;grid-template-columns:1fr;gap:8px}
  @media (min-width:720px){.grid{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}}
  .card{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:var(--radius);padding:12px 14px;display:flex;flex-direction:column;gap:8px;min-width:0}
  .card[data-k="bounced"],.card[data-k="stopped"]{border-left-color:var(--bad)}
  .card[data-k="closed"]{border-left-color:var(--lamp-off);opacity:.78}
  .card[data-k="replied"],.card[data-k="won"]{border-left-color:var(--good)}
  .card[data-k="waiting"]{border-left-color:var(--accent)}
  .card[data-k="noanswer"]{border-left-color:var(--warn)}
  .card.next[data-built="1"]{border-left-color:var(--good)}
  .head{display:flex;gap:10px;align-items:flex-start}
  .head .grow{flex:1;min-width:0}
  .head > div:first-child:not(.rank){flex:1;min-width:0}
  .rank{font-family:var(--mono);font-size:13px;color:var(--muted);padding-top:3px;min-width:22px;font-variant-numeric:tabular-nums}
  h3{font-size:16px;font-weight:600;margin:0;letter-spacing:-.01em;text-wrap:balance}
  .meta{font-size:12.5px;color:var(--muted);margin:2px 0 0}
  .chip{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:4px 8px;border-radius:999px;white-space:nowrap;background:var(--sunk);color:var(--ink-2);flex-shrink:0}
  .chip.good{background:var(--good-soft);color:var(--good)}
  .chip.warn{background:var(--warn-soft);color:var(--warn)}
  .chip.bad{background:var(--bad-soft);color:var(--bad)}
  .chip.accent{background:var(--accent-soft);color:var(--accent)}
  .chip.muted{background:var(--sunk);color:var(--muted)}
  .chip.now[data-now="open"]{background:var(--good-soft);color:var(--good)}
  .chip.now[data-now="soon"]{background:var(--warn-soft);color:var(--warn)}
  .chip.now[data-now="closed"],.chip.now[data-now="weekend"],.chip.now[data-now="unknown"]{background:var(--sunk);color:var(--muted)}

  .tags{display:flex;flex-wrap:wrap;gap:4px}
  .tag{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;border-radius:4px;background:var(--sunk);color:var(--muted)}
  .tag.stop{background:var(--bad);color:var(--surface)}
  .tag.warn{background:var(--warn);color:var(--surface)}
  .tag.hot{background:var(--accent);color:var(--on-accent)}
  .tag.soft{background:var(--sunk);color:var(--muted)}

  .line{font-size:13px;color:var(--ink-2);margin:0;overflow-wrap:anywhere}
  .reach{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .btn{font-family:var(--mono);font-size:12.5px;text-decoration:none;padding:6px 9px;border-radius:6px;border:1px solid var(--line);color:var(--ink);background:var(--sunk);display:inline-block;max-width:100%;overflow-wrap:anywhere}
  .btn.call{background:var(--accent);border-color:var(--accent);color:var(--on-accent);font-weight:500;font-size:14px}
  .btn.page{font-family:var(--ui);font-weight:500}
  .btn.page b{font-weight:500;color:var(--good);margin-left:4px}
  .btn.page.off{color:var(--muted)}
  .btn.page.off b{color:var(--warn)}
  .btn.stop{background:var(--bad-soft);border-color:var(--bad);color:var(--bad);font-family:var(--ui);font-weight:600}
  .btn .host{color:var(--muted);margin-left:4px}
  .none{font-size:12px;color:var(--muted);font-style:italic}

  .score{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
  .lampstrip{display:inline-flex;gap:3px}
  .lamp{width:11px;height:11px;border-radius:2px;background:var(--lamp-off);display:block}
  .lamp.on{background:var(--good)}
  .lamp.na{background:transparent;border:1px dashed var(--line)}
  .num{font-family:var(--mono);font-size:14px;font-weight:500;font-variant-numeric:tabular-nums}
  .num .of{color:var(--muted);font-size:12px}
  .flabel{font-size:13.5px;font-weight:600;color:var(--bad)}
  .flabel.ok{color:var(--good)}
  .fwhy{font-size:12.5px;color:var(--ink-2);margin:-4px 0 0}
  .win{font-size:12.5px;color:var(--muted);margin:0}
  .win b{color:var(--ink-2);font-weight:600}
  .gaps{font-size:12.5px;color:var(--warn);margin:0}
  .gaps b{font-weight:600;background:var(--warn-soft);padding:1px 6px;border-radius:4px;margin-right:2px;white-space:nowrap}
  details summary{cursor:pointer;font-size:12px;color:var(--muted)}
  .note{font-size:13px;color:var(--ink-2);margin:6px 0 0;white-space:pre-wrap;overflow-wrap:anywhere}

  .aside{margin-top:22px;font-size:12.5px;color:var(--muted);max-width:76ch}
  .aside b{color:var(--ink-2);font-weight:600}
  footer{margin-top:36px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:12px;max-width:76ch}
  footer code{font-family:var(--mono);font-size:11.5px}
  [hidden]{display:none!important}
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>`;

  const body = `
<div class="wrap">
  <header class="top">
    <div>
      <h1>Cold Call Pipeline</h1>
      <p class="sub">Everyone we have reached, and the ${s.next} worth reaching next. Rebuilt every morning from <code>clients/</code>, the send log and the lead files — a state marked <code>*</code> was read off the area code.</p>
    </div>
    <div class="stamp">${esc(d.builtAt)}<br>McManus Web Co.</div>
  </header>

  <div class="tiles">
    <div class="tile hero"><b>${s.waiting}</b><span>awaiting a reply</span></div>
    <div class="tile due${s.due ? '' : ' zero'}"><b>${s.due}</b><span>owed today</span></div>
    <div class="tile"><b>${s.replied}</b><span>replied${s.won ? ' · ' + s.won + ' won' : ''}</span></div>
    <div class="tile"><b>${s.bounced}</b><span>bounced or stopped</span></div>
    <div class="tile"><b>${s.live}<small>/${s.builtPages}</small></b><span>pages live</span></div>
    <div class="tile"><b>${s.next}<small>/${s.pool}</small></b><span>up next</span></div>
  </div>

  <div class="tabs" role="tablist" aria-label="Pipeline">
    <button role="tab" id="tab-contacted" aria-controls="panel-contacted" aria-selected="true">Contacted<em>${s.contacted}</em></button>
    <button role="tab" id="tab-next" aria-controls="panel-next" aria-selected="false">Up next<em>${s.next}</em></button>
    <input type="search" id="q" placeholder="Search name, trade, town…" aria-label="Search this tab">
    <span class="count" id="count"></span>
  </div>

  <section id="panel-contacted" role="tabpanel" aria-labelledby="tab-contacted">
    ${d.followUps.length ? `
    <div class="owed">
      <h2>Owed — ${d.followUps.length}</h2>
      <ul>${d.followUps.map(dueItem).join('')}</ul>
    </div>` : ''}
    <div class="filters" data-for="contacted">
      <button class="fchip" data-f="all" aria-pressed="true">All</button>
      <button class="fchip" data-f="waiting" aria-pressed="false">Awaiting reply · ${s.waiting}</button>
      <button class="fchip" data-f="noanswer" aria-pressed="false">No answer · ${s.noAnswer}</button>
      <button class="fchip" data-f="replied,won" aria-pressed="false">Replied · ${s.replied}</button>
      <button class="fchip" data-f="bounced,stopped" aria-pressed="false">Bounced · stopped · ${s.bounced}</button>
      <button class="fchip" data-f="closed" aria-pressed="false">Closed out</button>
    </div>
    <h2 class="sec">Most recent contact first</h2>
    <div class="grid">${d.contacted.map(contactedCard).join('')}</div>
    <p class="aside">Another <b>${s.closedUnreached}</b> were closed out without ever being contacted — sites that checked out fine in a browser, agencies, chains, wrong domains. They are not on this page because nobody spoke to them.</p>
  </section>

  <section id="panel-next" role="tabpanel" aria-labelledby="tab-next" hidden>
    <p class="lede">Nobody here has been contacted. Pages already built come first — the work is done, it only needs a call — then the board's order: worst site first. Seven lamps are the seven checks that can be proved in a browser and said out loud.</p>
    <div class="filters" data-for="next">
      <button class="fchip" data-f="all" aria-pressed="true">All</button>
      <button class="fchip" data-f="built" aria-pressed="false">Page built · ${built}</button>
      <button class="fchip" data-f="now" aria-pressed="false">Answering now</button>
      ${states.map((st) => `<button class="fchip" data-f="st:${esc(st)}" aria-pressed="false">${esc(st)}</button>`).join('')}
    </div>
    <h2 class="sec">Up next — ${s.next} of ${s.pool} callable</h2>
    <div class="grid">${d.next.map(nextCard).join('')}</div>
    ${d.setAside.length ? `<p class="aside">Set aside, not shown: ${d.setAside.map(([why, n]) => `<b>${n}</b> ${esc(why)}`).join(' · ')}.</p>` : ''}
  </section>

  <footer>Built by <code>./cc dashboard</code>. Statuses come from <code>clients/&lt;slug&gt;/business.json</code>; <code>./cc tried</code>, <code>./cc sent</code> and <code>./cc status</code> change them, and the next morning's build shows it. No email address on this page was guessed.</footer>
</div>

<script>
(function(){
  var tabs = [].slice.call(document.querySelectorAll('[role=tab]'));
  var panels = { contacted: document.getElementById('panel-contacted'), next: document.getElementById('panel-next') };
  var q = document.getElementById('q');
  var count = document.getElementById('count');
  var filter = { contacted: 'all', next: 'all' };
  var current = 'contacted';

  function store(k, v){ try { localStorage.setItem('pipeline.' + k, v); } catch (e) {} }
  function recall(k){ try { return localStorage.getItem('pipeline.' + k); } catch (e) { return null; } }

  function show(name){
    current = name;
    tabs.forEach(function(t){ t.setAttribute('aria-selected', t.id === 'tab-' + name ? 'true' : 'false'); });
    Object.keys(panels).forEach(function(k){ panels[k].hidden = (k !== name); });
    try { if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name); } catch (e) {}
    store('tab', name);
    apply();
  }

  function matches(card, f){
    if (f === 'all') return true;
    if (current === 'contacted') return f.split(',').indexOf(card.dataset.k) !== -1;
    if (f === 'built') return card.dataset.built === '1';
    if (f === 'now') { var c = card.querySelector('.chip.now'); return c && c.dataset.now === 'open'; }
    if (f.indexOf('st:') === 0) return card.dataset.state === f.slice(3);
    return true;
  }

  function apply(){
    var term = q.value.trim().toLowerCase();
    var cards = [].slice.call(panels[current].querySelectorAll('.card'));
    var shown = 0;
    cards.forEach(function(c){
      var ok = matches(c, filter[current]) && (!term || c.dataset.name.indexOf(term) !== -1);
      c.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown + ' of ' + cards.length;
  }

  tabs.forEach(function(t){ t.addEventListener('click', function(){ show(t.id.replace('tab-', '')); }); });
  q.addEventListener('input', apply);
  [].slice.call(document.querySelectorAll('.filters')).forEach(function(bar){
    var which = bar.dataset.for;
    bar.addEventListener('click', function(ev){
      var b = ev.target.closest('.fchip'); if (!b) return;
      filter[which] = b.dataset.f;
      [].slice.call(bar.querySelectorAll('.fchip')).forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });

  // Who is answering the phone right now, in their own time zone. The page
  // is built once a morning; this is the one thing on it that must not be.
  function clock(mins){ var h = Math.floor(mins / 60), m = mins % 60, ap = h >= 12 ? 'pm' : 'am'; h = h % 12 || 12; return h + (m ? ':' + (m < 10 ? '0' : '') + m : '') + ap; }
  function tick(){
    var now = new Date();
    [].slice.call(document.querySelectorAll('.card.next')).forEach(function(card){
      var chip = card.querySelector('.chip.now'); if (!chip) return;
      var tz = card.dataset.tz, slots;
      try { slots = JSON.parse(card.dataset.slots); } catch (e) { slots = []; }
      if (!tz) { chip.dataset.now = 'unknown'; chip.textContent = 'time zone unknown'; return; }
      var parts;
      try {
        parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', minute: 'numeric', weekday: 'short', hour12: false }).formatToParts(now);
      } catch (e) { chip.dataset.now = 'unknown'; chip.textContent = 'time zone unknown'; return; }
      var get = function(t){ var p = parts.filter(function(x){ return x.type === t; })[0]; return p ? p.value : ''; };
      var mins = (Number(get('hour')) % 24) * 60 + Number(get('minute'));
      var day = get('weekday');
      if (day === 'Sat' || day === 'Sun') { chip.dataset.now = 'weekend'; chip.textContent = day + ' there'; return; }
      var next = null;
      for (var i = 0; i < slots.length; i++) {
        var a = slots[i][0] * 60 + slots[i][1], b = slots[i][2] * 60 + slots[i][3];
        if (mins >= a && mins <= b) { chip.dataset.now = 'open'; chip.textContent = 'answering now · until ' + clock(b); return; }
        if (a > mins && (next === null || a < next)) next = a;
      }
      if (next !== null && next - mins <= 90) { chip.dataset.now = 'soon'; chip.textContent = 'opens in ' + (next - mins) + ' min'; return; }
      if (next !== null) { chip.dataset.now = 'closed'; chip.textContent = clock(mins) + ' there · next ' + clock(next); return; }
      chip.dataset.now = 'closed'; chip.textContent = clock(mins) + ' there · done for today';
    });
    if (filter.next === 'now' && current === 'next') apply();
  }

  var want = (location.hash || '').replace('#', '') || recall('tab') || 'contacted';
  if (!panels[want]) want = 'contacted';
  tick();
  show(want);
  setInterval(tick, 60000);
  window.addEventListener('hashchange', function(){ var h = location.hash.replace('#', ''); if (panels[h] && h !== current) show(h); });
})();
</script>`;

  const page = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="light dark">
${head}
</head>
<body>${body}
</body>
</html>
`;

  return { head, body, page };
}

module.exports = render;
