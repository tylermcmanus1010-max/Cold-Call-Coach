import { chromium } from 'playwright';
const B='http://127.0.0.1:5080';
const OUT='/home/user/Cold-Call-Coach/protocol/evidence/phase-01';
const br=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
const ctx=await br.newContext({viewport:{width:1440,height:1000}});
await ctx.route('**/*',r=>r.request().url().startsWith(B)?r.continue():r.abort());
const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
const ok=[],bad=[]; const t=(n,c,d='')=>c?ok.push(n):bad.push(n+(d?` — ${d}`:''));

await p.goto(B+'/login',{waitUntil:'domcontentloaded'});
await p.fill('input[name=email]','tyler1'); await p.fill('input[name=password]','fixpw');
await p.click('button[type=submit]'); await p.waitForLoadState('domcontentloaded');
await p.goto(B+'/admin/revenue?period=90d',{waitUntil:'domcontentloaded'});
await p.waitForTimeout(500);

const m = await p.evaluate(()=>{
  const cs=e=>e?getComputedStyle(e):null; const box=e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)];};
  const o={};
  const bar=document.querySelector('rect.chart-bar');
  if(bar){o.barFill=cs(bar).fill; o.bars=document.querySelectorAll('rect.chart-bar').length;
    o.heights=new Set([...document.querySelectorAll('rect.chart-bar')].map(r=>r.getAttribute('height'))).size;}
  const g=document.querySelector('.chart-grid line'); if(g)o.gridStroke=cs(g).stroke;
  const ax=document.querySelector('.chart-axis text'); if(ax)o.axisFill=cs(ax).fill;
  const mt=document.querySelector('.meter'), sp=document.querySelector('.meter > span');
  if(mt){o.meterBox=box(mt); o.meterBg=cs(mt).backgroundColor;}
  if(sp){o.spanBox=box(sp); o.spanBg=cs(sp).backgroundColor; o.spanDisplay=cs(sp).display;}
  const rb=document.querySelector('.range-btn'), ra=document.querySelector('.range-btn.active');
  if(rb){o.rangeBg=cs(rb).backgroundColor; o.rangePad=cs(rb).paddingLeft; o.rangeBorder=cs(rb).borderRightWidth;}
  if(ra){o.activeBg=cs(ra).backgroundColor; o.activeColor=cs(ra).color;}
  const bd=cs(document.body); o.bodyColor=bd.color;
  o.rootText=getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
  o.rootSunk=getComputedStyle(document.documentElement).getPropertyValue('--sunk').trim();
  o.rootLine=getComputedStyle(document.documentElement).getPropertyValue('--line').trim();
  return o;
});
console.log(JSON.stringify(m,null,1));
t('chart bars are brand green, not black', m.barFill && m.barFill!=='rgb(0, 0, 0)', m.barFill);
t('grid lines are visible', m.gridStroke && m.gridStroke!=='none', m.gridStroke);
t('axis labels are muted, not default black', m.axisFill && m.axisFill!=='rgb(0, 0, 0)', m.axisFill);
t('share bar has height', m.meterBox && m.meterBox[1] > 0, JSON.stringify(m.meterBox));
t('share bar fill has width and colour', m.spanBox && m.spanBox[0] > 0 && m.spanBg!=='rgba(0, 0, 0, 0)', JSON.stringify(m.spanBox));
t('period buttons have padding and a border', m.rangePad!=='0px' && m.rangeBorder!=='0px', `pad ${m.rangePad} border ${m.rangeBorder}`);
t('the selected period is visibly selected', m.activeBg && m.activeBg!=='rgba(0, 0, 0, 0)', m.activeBg);
t('--text resolves', !!m.rootText); t('--sunk resolves', !!m.rootSunk); t('--line resolves', !!m.rootLine);

await p.locator('.chart-wrap').screenshot({path:OUT+'/engine-chart-fixed.png'}).catch(()=>{});
await p.screenshot({path:OUT+'/engine-revenue-fixed.png'});
console.log('\nPASS:'); ok.forEach(x=>console.log('  ✓',x));
if(bad.length){console.log('FAIL:'); bad.forEach(x=>console.log('  ✗',x));}
console.log('pageerrors:',errs.length?errs:'none');
await br.close(); process.exit(bad.length?1:0);
