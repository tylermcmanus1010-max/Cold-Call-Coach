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

async function assertOnline() {
  const probe = 'https://stooq.com/q/d/l/?s=spy.us&i=d';
  let res;
  try {
    res = await fetch(probe, { redirect: 'follow' });
  } catch (e) {
    throw new Error(
      `cannot reach the open internet (${e.cause?.code || e.message}).\n` +
      '  Run this on GitHub Actions instead: Actions → Market watch → Run workflow.');
  }
  const body = await res.text();
  if (!res.ok || !/^Date,Open,High,Low,Close/i.test(body.trim())) {
    throw new Error(
      `the network answered ${res.status} for a known-good ticker, so it is filtering us,\n` +
      '  not telling us the ticker does not exist. Run it on GitHub Actions instead.');
  }
}

function parseCsv(text) {
  const lines = text.trim().split('\n');
  if (!/^Date,Open,High,Low,Close/i.test(lines[0])) return null;
  return lines.slice(1).map((l) => {
    const [date, o, h, lo, c, v] = l.split(',');
    return { date, open: +o, high: +h, low: +lo, close: +c, volume: +v };
  }).filter((b) => Number.isFinite(b.close));
}

async function bars(symbol) {
  const s = String(symbol).toLowerCase().replace(/[^a-z0-9.\-]/g, '');
  if (!s) throw new Error('no symbol given');
  const url = `https://stooq.com/q/d/l/?s=${s}.us&i=d`;
  const res = await fetch(url, { redirect: 'follow' });
  const text = await res.text();
  const rows = parseCsv(text);
  // Stooq answers 200 with the word "Exceeded" or an empty body for an unknown
  // ticker. That is a real answer — "no such symbol" — not a network problem,
  // and the online guard above has already ruled out the network.
  if (!rows || !rows.length) return { symbol: s.toUpperCase(), rows: [], note: text.trim().slice(0, 80) || 'no data returned' };
  return { symbol: s.toUpperCase(), rows };
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
  await assertOnline();
  fs.mkdirSync(STORE, { recursive: true });
  const out = [];
  for (const sym of symbols) {
    try {
      const b = await bars(sym);
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
