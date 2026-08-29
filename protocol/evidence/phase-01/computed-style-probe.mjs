import { chromium } from 'playwright';
const B='http://127.0.0.1:5058';
const OUT='/home/user/Cold-Call-Coach/protocol/evidence/phase-01';
const br = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium' });
const ctx = await br.newContext({ viewport:{width:1440,height:900} });
await ctx.route('**/*', r => r.request().url().startsWith(B) ? r.continue() : r.abort());
const p = await ctx.newPage();
await p.goto(B+'/login',{waitUntil:'domcontentloaded'});
await p.fill('input[name=email]','admin@montimakesit.com');
await p.fill('input[name=password]','p1admin');
await p.click('button[type=submit]');
await p.waitForLoadState('domcontentloaded');
await p.goto(B+'/admin/revenue',{waitUntil:'domcontentloaded'});
await p.waitForTimeout(400);

const probe = await p.evaluate(() => {
  const out = {};
  const bar = document.querySelector('rect.chart-bar');
  const grid = document.querySelector('.chart-grid line');
  const svg = document.querySelector('svg.chart-svg');
  const btn = document.querySelector('.range-btn');
  const meter = document.querySelector('.meter span');
  const cs = el => el ? getComputedStyle(el) : null;
  if (bar)  { const s = cs(bar);  out.barFill = s.fill; out.barStroke = s.stroke; }
  if (grid) { const s = cs(grid); out.gridStroke = s.stroke; }
  if (svg)  { const r = svg.getBoundingClientRect(); out.svgBox = [Math.round(r.width), Math.round(r.height)]; }
  if (btn)  { const s = cs(btn);  out.rangeBtnBg = s.backgroundColor; out.rangeBtnBorder = s.borderTopWidth; out.rangeBtnPad = s.paddingLeft; }
  if (meter){ const s = cs(meter); out.meterFill = s.backgroundColor; out.meterWidth = s.width; }
  out.barCount = document.querySelectorAll('rect.chart-bar').length;
  out.rootGreen = getComputedStyle(document.documentElement).getPropertyValue('--green').trim();
  return out;
});
console.log(JSON.stringify(probe, null, 2));
await p.locator('.chart-wrap').screenshot({ path: OUT + '/chg-001-revenue-chart.png' }).catch(async()=>{
  await p.screenshot({ path: OUT + '/chg-001-revenue-chart.png' });
});
await p.screenshot({ path: OUT + '/chg-001-revenue-full.png', fullPage:false });
await br.close();
