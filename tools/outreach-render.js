// The send queue, built to be worked through at a desk in a spare ten minutes.
//
// Each card is one business: the form to open, the exact text to paste, and
// the field mapping. It is deliberately one-at-a-time and copy-first, because
// the difference between outreach and spam is whether a person read it before
// it went, and because a message sent to the wrong business is on the record
// in a way a misdialled phone call never is.

const { esc } = require('./board');

const FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap';

function card(q, i) {
  const fields = q.fields.filter((f) => f.value).map((f) => `
    <tr>
      <td class="fname">${esc(f.label || f.name || f.type)}${f.required ? ' <span class="req">*</span>' : ''}</td>
      <td class="fval">${f.value === '{{MESSAGE}}' ? '<em>the message below</em>' : esc(f.value)}</td>
    </tr>`).join('');

  return `
<article class="card" data-name="${esc((q.name + ' ' + q.where + ' ' + q.category).toLowerCase())}" data-captcha="${q.captcha ? '1' : '0'}">
  <header>
    <span class="n">${i + 1}</span>
    <div>
      <h2>${esc(q.name)}</h2>
      <p class="meta">${esc(q.category || 'business')} · ${esc(q.where)} · ${q.score == null ? '<b class="hot">no website</b>' : `${q.score}/7`}${q.flaw ? ' · ' + esc(q.flaw) : ''}</p>
    </div>
    <label class="done"><input type="checkbox" data-id="${esc(q.name)}"> sent</label>
  </header>

  <div class="acts">
    <a class="btn go" href="${esc(q.formUrl)}" target="_blank" rel="noopener noreferrer">Open their form ↗</a>
    <button class="btn copy" type="button">Copy the message</button>
    ${q.phone ? `<a class="btn tel" href="tel:+1${esc(q.phone.replace(/[^0-9]/g, ''))}">${esc(q.phone)}</a>` : ''}
  </div>

  ${q.captcha ? '<p class="warn">This form has a CAPTCHA. It has to be finished by hand — that is the site asking not to be automated, and we take it at its word.</p>' : ''}
  ${q.published.length ? `<p class="pub">They print <b>${q.published.map(esc).join(', ')}</b> on their own contact page. Not a guessed address — but emailing it directly instead of using the form is your call.</p>` : ''}
  ${q.booker.length ? '<p class="pub">They already pay for a booking tool, so somebody is selling them software. Expect a shorter conversation.</p>' : ''}

  <details>
    <summary>Their form (${q.fields.length} fields, found on the ${esc(q.foundOn)})</summary>
    <table>${fields}</table>
  </details>

  <pre class="msg">${esc(q.message)}</pre>
</article>`;
}

module.exports = function render(batch, skipped, total) {
  return `<title>Send Queue</title>
<link rel="stylesheet" href="${FONTS}">
<style>
  :root{--ground:#F4F6F6;--surface:#fff;--sunk:#EAEEEE;--ink:#10181B;--ink2:#3C4A4F;--muted:#68787D;
        --line:#D6DEDF;--accent:#0B5E6B;--accent-soft:#E2EFF1;--on-accent:#fff;--warn:#8A5A0B;--good:#1F6B3F;
        --mono:"IBM Plex Mono",ui-monospace,monospace;--ui:"Archivo",system-ui,sans-serif}
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
    --ground:#0D1315;--surface:#151F22;--sunk:#101A1C;--ink:#E7EEEF;--ink2:#B4C3C6;--muted:#86989C;
    --line:#27383C;--accent:#5FB9C9;--accent-soft:#122E34;--on-accent:#08191C;--warn:#E0B056;--good:#67C08C}}
  :root[data-theme="dark"]{
    --ground:#0D1315;--surface:#151F22;--sunk:#101A1C;--ink:#E7EEEF;--ink2:#B4C3C6;--muted:#86989C;
    --line:#27383C;--accent:#5FB9C9;--accent-soft:#122E34;--on-accent:#08191C;--warn:#E0B056;--good:#67C08C}
  *{box-sizing:border-box}
  body{background:var(--ground);color:var(--ink);font-family:var(--ui);margin:0;line-height:1.45}
  .w{max-width:820px;margin:0 auto;padding:26px 16px 80px}
  h1{font-size:clamp(26px,6vw,36px);margin:0;letter-spacing:-.02em}
  .lede{color:var(--muted);font-size:14.5px;margin:6px 0 0;max-width:62ch}
  .rules{background:var(--accent-soft);border:1px solid var(--accent);border-radius:8px;padding:14px 16px;margin:20px 0 0}
  .rules p{margin:0 0 8px;font-size:13.5px;color:var(--ink2)}
  .rules p:last-child{margin:0}
  .rules b{color:var(--ink)}
  .bar{position:sticky;top:0;z-index:5;background:var(--ground);padding:12px 0;border-bottom:1px solid var(--line);
       display:flex;gap:8px;align-items:center;margin-top:22px}
  input[type=search]{flex:1;min-width:0;font:inherit;font-size:15px;padding:9px 12px;border:1px solid var(--line);
                     border-radius:8px;background:var(--surface);color:var(--ink)}
  .count{font-family:var(--mono);font-size:12px;color:var(--muted);white-space:nowrap}
  .card{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);
        border-radius:8px;padding:14px 16px;margin:10px 0}
  .card.is-done{opacity:.45}
  .card header{display:flex;gap:12px;align-items:flex-start}
  .n{font-family:var(--mono);font-size:12px;color:var(--muted);padding-top:4px}
  .card h2{font-size:17px;margin:0;letter-spacing:-.01em}
  .meta{font-size:12.5px;color:var(--muted);margin:2px 0 0}
  .hot{color:var(--accent)}
  .done{margin-left:auto;font-size:12px;color:var(--muted);display:flex;gap:5px;align-items:center;white-space:nowrap;cursor:pointer}
  .acts{display:flex;flex-wrap:wrap;gap:6px;margin:11px 0 0}
  .btn{font:inherit;font-size:13px;font-weight:500;text-decoration:none;padding:7px 11px;border-radius:6px;
       border:1px solid var(--line);background:var(--sunk);color:var(--ink);cursor:pointer;-webkit-appearance:none;appearance:none}
  .btn.go{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
  .btn.copy.ok{background:var(--good);border-color:var(--good);color:var(--surface)}
  .btn.tel{font-family:var(--mono)}
  .warn{font-size:13px;color:var(--warn);margin:10px 0 0;font-weight:500}
  .pub{font-size:12.5px;color:var(--ink2);margin:8px 0 0;background:var(--sunk);padding:8px 10px;border-radius:6px}
  details{margin:10px 0 0}
  summary{font-size:12.5px;color:var(--muted);cursor:pointer}
  table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px}
  td{padding:4px 6px;border-bottom:1px solid var(--line);vertical-align:top}
  .fname{color:var(--muted);width:42%}
  .fval{font-family:var(--mono);word-break:break-word}
  .req{color:var(--warn)}
  .msg{background:var(--sunk);border:1px solid var(--line);border-radius:6px;padding:12px;margin:11px 0 0;
       font-family:var(--ui);font-size:13.5px;white-space:pre-wrap;word-wrap:break-word;color:var(--ink2)}
  .skips{margin-top:34px;border-top:1px solid var(--line);padding-top:16px}
  .skips h3{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:0 0 8px}
  .skips li{font-size:13px;color:var(--ink2);margin-bottom:4px}
  a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="w">
  <h1>Send Queue</h1>
  <p class="lede">${batch.length} businesses you can contact from a desk, without saying a word out loud. Each one links to <em>their own</em> contact form — the inbox they publish for exactly this — so no address has to be guessed.</p>

  <div class="rules">
    <p><b>One message per business, ever.</b> If there is no reply, that is the answer. A second one is what turns outreach into spam, and it is the thing that gets a small sender blocked everywhere at once.</p>
    <p><b>Read each one before it goes.</b> The name, the town and the finding are filled in from our data, and our data has been wrong about a URL six times in one week. On the phone you can correct that mid-sentence; in writing it is permanent.</p>
    <p><b>A CAPTCHA means no.</b> Where a form has one it is marked, and it gets finished by hand or not at all.</p>
    <p><b>Ten a day, not a hundred.</b> This works because each message names something true about that specific business. Volume is what breaks it.</p>
  </div>

  <div class="bar">
    <input type="search" id="q" placeholder="Search name, trade or town…" aria-label="Search the queue">
    <span class="count" id="count"></span>
  </div>

  ${batch.map(card).join('')}

  ${skipped.length ? `<div class="skips">
    <h3>Left out (${skipped.length})</h3>
    <ul>${skipped.slice(0, 40).map((s) => `<li><b>${esc(s.name)}</b> — ${esc(s.why)}</li>`).join('')}</ul>
  </div>` : ''}
  <p class="lede" style="margin-top:22px">${total} businesses have a usable form in total; this batch is the ${batch.length} with the most to say.</p>
</div>

<script>
(function(){
  var cards = [].slice.call(document.querySelectorAll('.card'));
  var q = document.getElementById('q');
  var count = document.getElementById('count');

  // Which ones have gone, kept in this browser only. It never leaves the
  // device and nothing else reads it.
  var done = {};
  try { done = JSON.parse(localStorage.getItem('outreach.sent') || '{}'); } catch (e) {}

  cards.forEach(function(c){
    var box = c.querySelector('input[type=checkbox]');
    var id = box.dataset.id;
    if (done[id]) { box.checked = true; c.classList.add('is-done'); }
    box.addEventListener('change', function(){
      if (box.checked) { done[id] = new Date().toISOString().slice(0,10); }
      else { delete done[id]; }
      c.classList.toggle('is-done', box.checked);
      try { localStorage.setItem('outreach.sent', JSON.stringify(done)); } catch (e) {}
      apply();
    });

    var btn = c.querySelector('.copy');
    var msg = c.querySelector('.msg').textContent;
    btn.addEventListener('click', function(){
      function ok(){ btn.textContent = 'Copied'; btn.classList.add('ok');
        setTimeout(function(){ btn.textContent = 'Copy the message'; btn.classList.remove('ok'); }, 1600); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(msg).then(ok, fallback);
      } else { fallback(); }
      function fallback(){
        var ta = document.createElement('textarea');
        ta.value = msg; ta.setAttribute('readonly','');
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); ok(); }
        catch (e) { btn.textContent = 'Select it below and copy'; }
        document.body.removeChild(ta);
      }
    });
  });

  function apply(){
    var term = q.value.trim().toLowerCase();
    var shown = 0, sent = 0;
    cards.forEach(function(c){
      var ok = !term || c.dataset.name.indexOf(term) !== -1;
      c.hidden = !ok;
      if (ok) shown++;
      if (c.classList.contains('is-done')) sent++;
    });
    count.textContent = sent + ' sent · ' + shown + ' shown';
  }
  q.addEventListener('input', apply);
  apply();
})();
</script>`;
};
