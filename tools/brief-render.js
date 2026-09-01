// The morning plan, as one page you can hold in one hand.
//
// Sorted by whose phone can be answered rather than whose site is worst,
// because the best lead in the country is worthless at 5am if they are asleep.

const { esc, digits } = require('./board');
const { brief } = require('./brief');

const FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap';

const pacific = (d, opts) => new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', ...opts }).format(d);

function slot(when, seen) {
  const b = brief(when, { limit: 60 });
  const fresh = b.open.filter((r) => !seen.has(r.phone));
  fresh.forEach((r) => seen.add(r.phone));
  return { label: pacific(when, { hour: 'numeric', hour12: true }), total: b.open.length, rows: fresh };
}

function row(r) {
  const score = r.parked
    ? '<span class="hot">no website at all</span>'
    : `<span class="sc">${r.passed}/7</span>`;
  return `<li>
  <a class="tel" href="tel:+1${esc(digits(r.phone))}">${esc(r.phone)}</a>
  <div class="b">
    <strong>${esc(r.name)}</strong>
    <span class="m">${esc(r.category || 'business')} · ${esc([r.city, r.state].filter(Boolean).join(', '))} · <b>${esc(r.when.local)} their time</b></span>
    <span class="f">${score} — ${esc(r.flaw ? r.flaw.label : 'nothing provable to sell')}</span>
  </div>
</li>`;
}

module.exports = function render(start, hours) {
  const seen = new Set();
  const slots = [];
  for (let i = 0; i < hours; i++) {
    slots.push(slot(new Date(start.getTime() + i * 3600e3), seen));
  }
  const total = slots.reduce((n, s) => n + s.rows.length, 0);

  return `<title>Morning Call Plan</title>
<link rel="stylesheet" href="${FONTS}">
<style>
  :root{--ground:#F4F6F6;--surface:#fff;--sunk:#EAEEEE;--ink:#10181B;--ink2:#3C4A4F;--muted:#68787D;
        --line:#D6DEDF;--accent:#0B5E6B;--accent-soft:#E2EFF1;--on-accent:#fff;--bad:#B3261E;
        --mono:"IBM Plex Mono",ui-monospace,monospace;--ui:"Archivo",system-ui,sans-serif}
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
    --ground:#0D1315;--surface:#151F22;--sunk:#101A1C;--ink:#E7EEEF;--ink2:#B4C3C6;--muted:#86989C;
    --line:#27383C;--accent:#5FB9C9;--accent-soft:#122E34;--on-accent:#08191C;--bad:#F1867C}}
  :root[data-theme="dark"]{
    --ground:#0D1315;--surface:#151F22;--sunk:#101A1C;--ink:#E7EEEF;--ink2:#B4C3C6;--muted:#86989C;
    --line:#27383C;--accent:#5FB9C9;--accent-soft:#122E34;--on-accent:#08191C;--bad:#F1867C}
  *{box-sizing:border-box}
  body{background:var(--ground);color:var(--ink);font-family:var(--ui);margin:0;line-height:1.45}
  .w{max-width:760px;margin:0 auto;padding:26px 16px 70px}
  h1{font-size:clamp(26px,6vw,36px);margin:0;letter-spacing:-.02em;text-wrap:balance}
  .lede{color:var(--muted);font-size:14.5px;margin:6px 0 0;max-width:60ch}
  .hour{margin:30px 0 0;display:flex;align-items:baseline;gap:10px;border-bottom:2px solid var(--ink);padding-bottom:6px}
  .hour h2{font-size:22px;margin:0;font-family:var(--mono);font-weight:500;letter-spacing:-.02em}
  .hour span{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
  ul{list-style:none;padding:0;margin:10px 0 0}
  li{display:flex;gap:12px;align-items:flex-start;background:var(--surface);border:1px solid var(--line);
     border-left:3px solid var(--accent);border-radius:8px;padding:11px 13px;margin-bottom:6px}
  .tel{font-family:var(--mono);font-size:14px;font-weight:500;text-decoration:none;background:var(--accent);
       color:var(--on-accent);padding:7px 10px;border-radius:6px;white-space:nowrap}
  .b{display:flex;flex-direction:column;gap:2px;min-width:0}
  .b strong{font-size:15px;font-weight:600}
  .m{font-size:12.5px;color:var(--muted)}
  .m b{color:var(--ink2);font-family:var(--mono);font-weight:500}
  .f{font-size:13px;color:var(--bad);font-weight:500}
  .sc{font-family:var(--mono);color:var(--muted);font-weight:500}
  .hot{color:var(--accent);font-weight:700}
  .none{color:var(--muted);font-style:italic;font-size:14px;padding:10px 2px}
  .note{background:var(--accent-soft);border:1px solid var(--accent);border-radius:8px;padding:14px 16px;margin:22px 0 0}
  .note p{margin:0 0 8px;font-size:14px;color:var(--ink2)}
  .note p:last-child{margin:0}
  .note strong{color:var(--ink)}
  a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  @media (max-width:420px){ li{flex-direction:column;gap:8px} .tel{align-self:flex-start} }
</style>
<div class="w">
  <h1>Morning Call Plan</h1>
  <p class="lede">${pacific(start, { weekday: 'long', month: 'long', day: 'numeric' })}, from ${pacific(start, { hour: 'numeric', hour12: true })} Pacific.
  Ordered by whose phone can be answered, not by whose website is worst — ${total} businesses, each shown in <em>their</em> local time.</p>

  <div class="note">
    <p><strong>Why 5am is worth setting an alarm for.</strong> At 5:00 here it is 8:00 in Wilmington and 7:00 in Milwaukee and Nashville. That is the hour a tradesman answers — in the van, before the first job — and it is an hour you have never used, because until today every lead you had was in California.</p>
    <p>Say the town out loud early. Someone in Delaware answering a 619 number needs to know in the first sentence why San Diego is calling.</p>
  </div>

${slots.map((s) => `
  <div class="hour"><h2>${esc(s.label)}</h2><span>${s.rows.length} new · ${s.total} reachable</span></div>
  ${s.rows.length ? `<ul>${s.rows.slice(0, 12).map(row).join('')}</ul>` : '<p class="none">Nothing new opens this hour — keep working the list above.</p>'}`).join('')}
</div>`;
};
