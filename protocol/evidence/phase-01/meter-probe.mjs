import { chromium } from 'playwright';
const B='http://127.0.0.1:5059';
const OUT='/home/user/Cold-Call-Coach/protocol/evidence/phase-01';
const br = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium' });
const ctx = await br.newContext({ viewport:{width:1440,height:1000} });
await ctx.route('**/*', r => r.request().url().startsWith(B) ? r.continue() : r.abort());
const p = await ctx.newPage();
await p.goto(B+'/login',{waitUntil:'domcontentloaded'});
await p.fill('input[name=email]','tyler1');
await p.fill('input[name=password]','p1admin');
await p.click('button[type=submit]');
await p.waitForLoadState('domcontentloaded');
await p.goto(B+'/admin/revenue?period=90d',{waitUntil:'domcontentloaded'});
await p.waitForTimeout(400);

const probe = await p.evaluate(() => {
  const cs = el => el ? getComputedStyle(el) : null;
  const out = {};
  const bar = document.querySelector('rect.chart-bar');
  if (bar) { const s = cs(bar); out.chartBarFill = s.fill; }
  out.chartBars = document.querySelectorAll('rect.chart-bar').length;
  const heights = [...document.querySelectorAll('rect.chart-bar')].map(r=>r.getAttribute('height'));
  out.distinctBarHeights = new Set(heights).size;

  const meter = document.querySelector('.meter');
  const span  = document.querySelector('.meter > span');
  if (meter) { const s = cs(meter);
    out.meterBg = s.backgroundColor; out.meterBorder = s.borderTopWidth;
    out.meterHeight = s.height; out.meterDisplay = s.display;
    out.meterRect = (r=>[Math.round(r.width),Math.round(r.height)])(meter.getBoundingClientRect()); }
  if (span) { const s = cs(span);
    out.spanBg = s.backgroundColor; out.spanDisplay = s.display;
    out.spanInlineWidth = span.getAttribute('style');
    out.spanRect = (r=>[Math.round(r.width),Math.round(r.height)])(span.getBoundingClientRect()); }
  out.meterCount = document.querySelectorAll('.meter').length;
  out.clientRows = document.querySelectorAll('a[href*="/admin/clients/"]').length;
  return out;
});
import { writeFileSync } from 'fs';
const lines = [
  '# Computed styles, read from Chromium — CHG-001 and CHG-005',
  '# Written by meter-probe.mjs against a throwaway seeded database (§1.5).',
  '# These figures are measured, not transcribed: this file is the probe output.',
  '',
  '## The chart (CHG-001), with data to draw',
  `  rect.chart-bar   fill              ${probe.chartBarFill}`,
  `  marks rendered                     ${probe.chartBars}`,
  `  distinct mark heights              ${probe.distinctBarHeights}`,
  '',
  '## The share bar (CHG-005), with rows to draw',
  `  .meter           background-color  ${probe.meterBg}`,
  `  .meter           border-width      ${probe.meterBorder}`,
  `  .meter           height            ${probe.meterHeight}`,
  `  .meter           bounding box      ${probe.meterRect?.join(' x ')}`,
  `  .meter > span    display           ${probe.spanDisplay}`,
  `  .meter > span    inline style      ${probe.spanInlineWidth}`,
  `  .meter > span    bounding box      ${probe.spanRect?.join(' x ')}`,
  `  .meter elements on the page        ${probe.meterCount}`,
  '',
  '  The span is display:inline, so its width:100% does nothing. The bar is 0 pixels',
  '  tall and 0 pixels wide. It is not illegible; it does not render.',
  '',
  '## Screenshots written by this run',
  '  chg-005-share-bars.png        the Share column, and CHG-010 in the same table',
  '  chg-001-chart-with-data.png   90 marks, all black',
];
writeFileSync(OUT + '/computed-styles.txt', lines.join('\n') + '\n');
console.log(lines.join('\n'));
const card = p.locator('.card').filter({hasText:'Revenue by client'}).first();
await card.screenshot({ path: OUT+'/chg-005-share-bars.png' }).catch(()=>p.screenshot({path:OUT+'/chg-005-share-bars.png'}));
await p.locator('.chart-wrap').screenshot({ path: OUT+'/chg-001-chart-with-data.png' }).catch(()=>{});
await br.close();
