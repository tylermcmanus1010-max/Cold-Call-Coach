// Daily price history, from a source that needs no key and no account.
//
// Stooq publishes plain CSV. That matters here for the same reason the rest of
// this repo avoids dependencies: a tool that needs a paid data subscription to
// answer "what did this actually do" will stop being run.
//
// Egress is blocked locally, so this runs on GitHub Actions like the scout —
// and it uses the same guard, because a proxy answering 403 looks exactly like
// a data source that has no such ticker, and one bad run would write "no data"
// across a whole watchlist.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const STORE = path.join(ROOT, 'trading', 'bars');

// Two sources, because one of them will be refusing us on any given day.
// Stooq is plain CSV and needs no key; Yahoo's chart endpoint is JSON and also
// needs no key. Neither is a contract, so the code says which one answered.
const SOURCES = [
  {
    name: 'stooq',
    url: (s) => `https://stooq.com/q/d/l/?s=${s}.us&i=d`,
    parse: (text) => parseCsv(text),
  },
  {
    name: 'yahoo',
    url: (s) => `https://query1.finance.yahoo.com/v8/finance/chart/${s.toUpperCase()}?range=2y&interval=1d`,
    parse: (text) => {
      let j;
      try { j = JSON.parse(text); } catch { return null; }
      const r = j?.chart?.result?.[0];
      const q = r?.indicators?.quote?.[0];
      if (!r?.timestamp || !q) return null;
      return r.timestamp.map((t, i) => ({
        date: new Date(t * 1000).toISOString().slice(0, 10),
        open: q.open[i], high: q.high[i], low: q.low[i], close: q.close[i], volume: q.volume[i],
      })).filter((b) => Number.isFinite(b.close));
    },
  },
];

// Which source is actually answering today. Chosen once per run against a
// ticker that certainly exists, so that a later empty response means "no such
// symbol" rather than "we are being filtered" — the distinction that matters,
// and the one a 403-answering proxy erases.
let CHOSEN = null;

async function assertOnline({ log = () => {} } = {}) {
  const failures = [];
  for (const src of SOURCES) {
    try {
      const res = await fetch(src.url('spy'), {
        redirect: 'follow',
        headers: { 'user-agent': 'cold-call-coach/1.0 (paper-trading journal)' },
      });
      const body = await res.text();
      const rows = res.ok ? src.parse(body) : null;
      if (rows && rows.length > 100) {
        CHOSEN = src;
        log(`  prices from ${src.name}`);
        return src;
      }
      const snippet = body.replace(/\s+/g, ' ').trim().slice(0, 120);
      failures.push(`${src.name}: HTTP ${res.status}${snippet ? ` — "${snippet}"` : ' — empty body'}`);
    } catch (e) {
      failures.push(`${src.name}: ${e.cause?.code || e.message}`);
    }
  }
  throw new Error(
    'no price source would answer with real data for SPY, which certainly exists.\n  ' +
    failures.join('\n  ') +
    '\n\n  That means we are being filtered, not that the tickers are wrong — so nothing\n' +
    '  has been written. Locally this is expected: run it on GitHub Actions instead.');
}

function parseCsv(text) {
  const lines = text.trim().split('\n');
  if (!/^Date,Open,High,Low,Close/i.test(lines[0])) return null;
  return lines.slice(1).map((l) => {
    const [date, o, h, lo, c, v] = l.split(',');
    return { date, open: +o, high: +h, low: +lo, close: +c, volume: +v };
  }).filter((b) => Number.isFinite(b.close));
}

async function bars(symbol, src = CHOSEN) {
  if (!src) src = await assertOnline();
  const s = String(symbol).toLowerCase().replace(/[^a-z0-9.\-]/g, '');
  if (!s) throw new Error('no symbol given');
  const res = await fetch(src.url(s), {
    redirect: 'follow',
    headers: { 'user-agent': 'cold-call-coach/1.0 (paper-trading journal)' },
  });
  const text = await res.text();
  const rows = res.ok ? src.parse(text) : null;
  // The source has already proved it answers properly for SPY, so an empty
  // response here is a real answer: no such symbol.
  if (!rows || !rows.length) {
    return { symbol: s.toUpperCase(), rows: [], note: `${src.name} has no data for this symbol` };
  }
  return { symbol: s.toUpperCase(), rows, source: src.name };
}

// Plain descriptive statistics. Nothing here predicts anything; it says what
// already happened, which is the only thing price data can honestly tell you.
function describe(rows, lookback = 60) {
  const r = rows.slice(-lookback);
  if (r.length < 20) return null;
  const closes = r.map((b) => b.close);
  const last = closes[closes.length - 1];
  const hi = Math.max(...r.map((b) => b.high));
  const lo = Math.min(...r.map((b) => b.low));

  // Average true range — how far this thing moves on an ordinary day. It is
  // the honest unit for a stop, because a stop tighter than a day's noise is
  // not a stop, it is a donation.
  let atr = 0;
  for (let i = 1; i < r.length; i++) {
    atr += Math.max(r[i].high - r[i].low,
                    Math.abs(r[i].high - r[i - 1].close),
                    Math.abs(r[i].low - r[i - 1].close));
  }
  atr /= (r.length - 1);

  const sma = (n) => closes.slice(-n).reduce((a, b) => a + b, 0) / Math.min(n, closes.length);
  const rets = closes.slice(1).map((c, i) => Math.log(c / closes[i]));
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const sd = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / rets.length);

  return {
    last,
    asOf: r[r.length - 1].date,
    days: r.length,
    high: hi,
    low: lo,
    atr: +atr.toFixed(2),
    atrPct: +((atr / last) * 100).toFixed(2),
    sma20: +sma(20).toFixed(2),
    sma50: +sma(50).toFixed(2),
    annualisedVolPct: +(sd * Math.sqrt(252) * 100).toFixed(1),
    pctOffHigh: +(((last - hi) / hi) * 100).toFixed(1),
  };
}

async function snapshot(symbols, { log = console.log } = {}) {
  const src = await assertOnline({ log });
  fs.mkdirSync(STORE, { recursive: true });
  const out = [];
  for (const sym of symbols) {
    try {
      const b = await bars(sym, src);
      if (!b.rows.length) { log(`  ? ${b.symbol} — ${b.note}`); out.push({ symbol: b.symbol, error: b.note }); continue; }
      fs.writeFileSync(path.join(STORE, `${b.symbol}.json`),
        JSON.stringify({ symbol: b.symbol, fetchedAt: new Date().toISOString(), rows: b.rows.slice(-400) }, null, 2));
      const d = describe(b.rows);
      out.push({ symbol: b.symbol, ...d });
      log(`  · ${b.symbol.padEnd(6)} ${d ? `${d.last}  ATR ${d.atrPct}%  vol ${d.annualisedVolPct}%  ${d.pctOffHigh}% off 60d high` : 'not enough history'}`);
    } catch (e) {
      log(`  ! ${sym} — ${e.message.split('\n')[0]}`);
      out.push({ symbol: String(sym).toUpperCase(), error: e.message.split('\n')[0] });
    }
  }
  return out;
}

module.exports = { bars, describe, snapshot, assertOnline, parseCsv };
