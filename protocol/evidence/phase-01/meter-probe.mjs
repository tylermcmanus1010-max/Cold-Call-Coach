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
console.log(JSON.stringify(probe,null,2));
const card = p.locator('.card').filter({hasText:'Revenue by client'}).first();
await card.screenshot({ path: OUT+'/chg-005-share-bars.png' }).catch(()=>p.screenshot({path:OUT+'/chg-005-share-bars.png'}));
await p.locator('.chart-wrap').screenshot({ path: OUT+'/chg-001-chart-with-data.png' }).catch(()=>{});
await br.close();
