// A paper-trading journal that is hard to lie to.
//
// The reason to build this before anything that touches real money: almost
// nobody who wants to day trade has ever measured themselves, and the ones who
// have mostly stop. The published base rates are not close — across large
// samples of retail day traders, the share who beat a savings account net of
// costs over a sustained period lands in the low single digits.
//
// So the design goal is not to find trades. It is to make Tyler's own record
// legible to him, in a form he cannot rewrite after the fact:
//
//   - the thesis and the stop are written BEFORE the outcome exists
//   - a trade with no stop is refused, because it has no defined risk
//   - results are measured in R (multiples of the amount risked), not dollars,
//     so a lucky big position cannot flatter a bad decision
//   - nothing here can place an order, and nothing here holds a credential

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const FILE = path.join(ROOT, 'trading', 'journal.json');
const cfg = () => JSON.parse(fs.readFileSync(path.join(ROOT, 'config/trading.json'), 'utf8'));

function load() {
  if (!fs.existsSync(FILE)) return { trades: [], openedAt: new Date().toISOString().slice(0, 10) };
  return JSON.parse(fs.readFileSync(FILE, 'utf8'));
}
function save(j) {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(j, null, 2));
}

// How many shares, given what you are willing to lose if the stop is hit.
// This is the whole discipline in one function: the size follows from the
// stop, never the other way round.
function size(account, entry, stop, riskPct) {
  const perShare = Math.abs(entry - stop);
  if (!(perShare > 0)) return { error: 'the stop is at the entry price — that is not a stop' };
  const riskDollars = account * (riskPct / 100);
  const shares = Math.floor(riskDollars / perShare);
  return {
    shares,
    riskDollars: +riskDollars.toFixed(2),
    perShare: +perShare.toFixed(2),
    cost: +(shares * entry).toFixed(2),
    actualRisk: +(shares * perShare).toFixed(2),
  };
}

function open(t) {
  const c = cfg();
  const j = load();

  for (const k of ['symbol', 'entry', 'stop', 'thesis']) {
    if (t[k] == null || t[k] === '') return { error: `every trade needs a ${k}` };
  }
  const entry = Number(t.entry), stop = Number(t.stop), target = t.target ? Number(t.target) : null;
  if (!Number.isFinite(entry) || !Number.isFinite(stop)) return { error: 'entry and stop must be numbers' };
  if (c.risk.requireStop && entry === stop) return { error: 'a trade without a real stop has undefined risk — refused' };

  // A thesis written in five words is a thesis you cannot be held to later.
  if (String(t.thesis).trim().split(/\s+/).length < 8) {
    return { error: 'write a real thesis — at least a sentence saying what you expect and why. You are going to grade this later.' };
  }

  const openTrades = j.trades.filter((x) => !x.closedAt);
  if (openTrades.length >= c.risk.maxOpenPositions) {
    return { error: `already holding ${openTrades.length} positions, and the rule is ${c.risk.maxOpenPositions}` };
  }

  const equity = equityNow(j, c);
  const s = size(equity, entry, stop, c.risk.maxRiskPctPerTrade);
  if (s.error) return s;
  if (s.shares < 1) return { error: `at ${c.risk.maxRiskPctPerTrade}% of ${equity.toFixed(0)} you cannot afford one share with that stop` };

  const openRisk = openTrades.reduce((n, x) => n + (x.actualRisk || 0), 0);
  if (openRisk + s.actualRisk > equity * (c.risk.maxRiskPctTotal / 100)) {
    return { error: `that would put ${(((openRisk + s.actualRisk) / equity) * 100).toFixed(1)}% of the account at risk at once, over the ${c.risk.maxRiskPctTotal}% ceiling` };
  }

  if (target) {
    const rr = Math.abs(target - entry) / s.perShare;
    if (rr < c.risk.minRewardToRisk) {
      return { error: `that target is only ${rr.toFixed(2)}R away, under the ${c.risk.minRewardToRisk}R minimum. Either the target is too close or the stop is too far.` };
    }
  }

  const trade = {
    id: `${new Date().toISOString().slice(0, 10)}-${String(t.symbol).toUpperCase()}-${j.trades.length + 1}`,
    symbol: String(t.symbol).toUpperCase(),
    direction: t.direction === 'short' ? 'short' : 'long',
    openedAt: new Date().toISOString(),
    entry, stop, target,
    ...s,
    thesis: String(t.thesis).trim(),
    closedAt: null, exit: null, rMultiple: null, review: null,
  };
  j.trades.push(trade);
  save(j);
  return { trade, equity };
}

function close(id, exit, review) {
  const j = load();
  const t = j.trades.find((x) => x.id === id || (x.symbol === String(id).toUpperCase() && !x.closedAt));
  if (!t) return { error: `no open trade matching "${id}"` };
  if (t.closedAt) return { error: `${t.id} is already closed` };

  const px = Number(exit);
  if (!Number.isFinite(px)) return { error: 'exit must be a number' };

  const dir = t.direction === 'short' ? -1 : 1;
  const pnl = (px - t.entry) * t.shares * dir;
  t.closedAt = new Date().toISOString();
  t.exit = px;
  t.pnl = +pnl.toFixed(2);
  // R is the only unit that compares trades honestly: a win of 2R is twice as
  // good a decision as 1R regardless of how much money was on it.
  t.rMultiple = +(pnl / t.actualRisk).toFixed(2);
  t.review = review ? String(review).trim() : null;
  save(j);
  return { trade: t };
}

function equityNow(j, c) {
  const closed = j.trades.filter((x) => x.closedAt);
  return c.account.paperStart + closed.reduce((n, x) => n + (x.pnl || 0), 0);
}

function stats() {
  const c = cfg();
  const j = load();
  const closed = j.trades.filter((x) => x.closedAt);
  const wins = closed.filter((x) => x.rMultiple > 0);
  const losses = closed.filter((x) => x.rMultiple <= 0);

  const sumR = closed.reduce((n, x) => n + x.rMultiple, 0);
  const expectancy = closed.length ? sumR / closed.length : 0;

  // Worst peak-to-trough run of the equity curve, in percent.
  let equity = c.account.paperStart, peak = equity, maxDD = 0;
  for (const t of closed) {
    equity += t.pnl;
    peak = Math.max(peak, equity);
    maxDD = Math.max(maxDD, ((peak - equity) / peak) * 100);
  }

  const weeks = j.openedAt
    ? Math.floor((Date.now() - new Date(j.openedAt).getTime()) / (7 * 864e5)) : 0;

  const gate = c.gate;
  const checks = [
    { name: `${gate.minTrades} closed trades`, ok: closed.length >= gate.minTrades, have: `${closed.length}` },
    { name: `${gate.minWeeks} weeks of record`, ok: weeks >= gate.minWeeks, have: `${weeks}` },
    { name: `expectancy at or above ${gate.minExpectancyR}R`, ok: expectancy >= gate.minExpectancyR, have: `${expectancy.toFixed(2)}R` },
    { name: `drawdown under ${gate.maxDrawdownPct}%`, ok: maxDD <= gate.maxDrawdownPct, have: `${maxDD.toFixed(1)}%` },
  ];

  return {
    open: j.trades.filter((x) => !x.closedAt),
    closed: closed.length,
    wins: wins.length,
    losses: losses.length,
    winRate: closed.length ? +((wins.length / closed.length) * 100).toFixed(1) : null,
    expectancy: +expectancy.toFixed(3),
    totalR: +sumR.toFixed(2),
    pnl: +(equity - c.account.paperStart).toFixed(2),
    equity: +equity.toFixed(2),
    maxDrawdownPct: +maxDD.toFixed(1),
    weeks,
    checks,
    readyForRealMoney: checks.every((x) => x.ok),
  };
}

module.exports = { open, close, stats, size, load, cfg };
