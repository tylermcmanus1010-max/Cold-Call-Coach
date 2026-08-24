#!/usr/bin/env node
// Reads tracker.csv and reports which hook families and platforms actually work.
// Usage: node content-ops/tools/analyze.mjs [path/to/tracker.csv] [--min N]

import { readFileSync } from 'node:fs';

const args = process.argv.slice(2);
const minIdx = args.indexOf('--min');
const MIN_SAMPLE = minIdx !== -1 ? Number(args[minIdx + 1]) : 3;
const file = args.find((a) => !a.startsWith('--') && a !== String(MIN_SAMPLE))
  ?? 'content-ops/tools/tracker.csv';

// Minimal RFC4180-ish parser: handles quoted fields containing commas/quotes.
function parseCsv(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((f) => f.trim() !== ''));
}

let raw;
try {
  raw = readFileSync(file, 'utf8');
} catch {
  console.error(`Cannot read ${file}`);
  process.exit(1);
}

const rows = parseCsv(raw);
if (rows.length < 2) {
  console.log('No data yet. Log some posts in tracker.csv first.');
  process.exit(0);
}

const header = rows[0].map((h) => h.trim());
const posts = rows.slice(1).map((r) =>
  Object.fromEntries(header.map((h, i) => [h, (r[i] ?? '').trim()]))
);

const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

function summarize(label, groupKey, metric) {
  const groups = new Map();
  for (const p of posts) {
    const k = p[groupKey] || '(blank)';
    const v = num(p[metric]);
    if (v === null) continue;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(v);
  }
  const stats = [...groups.entries()]
    .map(([k, vals]) => ({
      k,
      n: vals.length,
      mean: vals.reduce((a, b) => a + b, 0) / vals.length,
    }))
    .filter((s) => s.n >= MIN_SAMPLE)
    .sort((a, b) => b.mean - a.mean);

  console.log(`\n## ${label} — by ${metric} (min ${MIN_SAMPLE} posts)`);
  if (!stats.length) {
    const total = groups.size;
    console.log(`  Not enough data. ${total} group(s) seen, none with ${MIN_SAMPLE}+ posts.`);
    return;
  }
  const width = Math.max(...stats.map((s) => s.k.length));
  for (const s of stats) {
    console.log(`  ${s.k.padEnd(width)}  ${s.mean.toFixed(1).padStart(7)}   (n=${s.n})`);
  }
}

console.log(`Analyzed ${posts.length} posts from ${file}`);
summarize('Hook families', 'hook_family', 'ret_3s_pct');
summarize('Hook families', 'hook_family', 'follows');
summarize('Platforms', 'platform', 'ret_3s_pct');
summarize('Platforms', 'platform', 'views');

// Follows-per-1k-views: the metric that separates real growth from empty reach.
const eff = posts
  .map((p) => ({ p, v: num(p.views), f: num(p.follows) }))
  .filter((x) => x.v > 0 && x.f !== null)
  .map((x) => ({ hook: x.p.hook_text || x.p.idea || '(untitled)', rate: (x.f / x.v) * 1000 }))
  .sort((a, b) => b.rate - a.rate);

if (eff.length) {
  console.log('\n## Top posts by follows per 1k views');
  for (const e of eff.slice(0, 5)) {
    console.log(`  ${e.rate.toFixed(2).padStart(6)}  ${e.hook.slice(0, 70)}`);
  }
  if (eff.length > 5) {
    console.log('\n## Bottom posts by follows per 1k views');
    for (const e of eff.slice(-3)) {
      console.log(`  ${e.rate.toFixed(2).padStart(6)}  ${e.hook.slice(0, 70)}`);
    }
  }
}
console.log('');
