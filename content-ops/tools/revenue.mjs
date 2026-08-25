#!/usr/bin/env node
// Models the path to YouTube monetization and revenue at scale.
//
//   node content-ops/tools/revenue.mjs
//   node content-ops/tools/revenue.mjs --rpm 9 --length 12 --retention 42 --uploads 2

const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  if (i === -1) return dflt;
  const v = Number(args[i + 1]);
  if (!Number.isFinite(v)) {
    console.error(`--${name} needs a number`);
    process.exit(1);
  }
  return v;
};

const RPM       = arg('rpm', 9);         // $ per 1000 long-form views
const LENGTH    = arg('length', 11);     // minutes
const RETENTION = arg('retention', 45);  // percent
const UPLOADS   = arg('uploads', 2);     // long-form per week
const SHORTS_RPM = arg('shorts-rpm', 0.20);

const WATCH_HOURS_TARGET = 4000;
const SUBS_TARGET = 1000;

const minutesPerView = LENGTH * (RETENTION / 100);
const viewsForThreshold = (WATCH_HOURS_TARGET * 60) / minutesPerView;

const fmt = (n) => n.toLocaleString('en-US', { maximumFractionDigits: 0 });
const money = (n) => '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });

console.log(`
ASSUMPTIONS
  Long-form RPM        $${RPM.toFixed(2)} per 1,000 views
  Video length         ${LENGTH} min
  Average retention    ${RETENTION}%
  Watch time per view  ${minutesPerView.toFixed(1)} min
  Uploads              ${UPLOADS}/week
`);

console.log(`PATH TO MONETIZATION  (${fmt(SUBS_TARGET)} subs + ${fmt(WATCH_HOURS_TARGET)} watch hours)`);
console.log(`  Long-form views needed     ${fmt(viewsForThreshold)}`);
for (const months of [6, 9, 12]) {
  const videos = UPLOADS * 4.33 * months;
  const perVideo = viewsForThreshold / videos;
  console.log(`  In ${String(months).padStart(2)} months  ${fmt(videos).padStart(4)} videos  ->  ${fmt(perVideo).padStart(6)} views per video`);
}

// Shorts path, for contrast.
const shortsPath = 10_000_000 / 90;
console.log(`\n  Shorts path instead: 10M views/90 days = ${fmt(shortsPath)} views per DAY`);

console.log(`\nREVENUE AT SCALE  (long-form ad revenue only)`);
console.log(`  ${'Monthly views'.padEnd(16)} ${'Per month'.padStart(11)} ${'Per year'.padStart(11)}`);
for (const v of [25_000, 100_000, 250_000, 500_000, 1_000_000]) {
  const m = (v / 1000) * RPM;
  console.log(`  ${fmt(v).padEnd(16)} ${money(m).padStart(11)} ${money(m * 12).padStart(11)}`);
}

console.log(`\nEQUIVALENCE`);
const ratio = RPM / SHORTS_RPM;
console.log(`  1 long-form view = ${ratio.toFixed(0)} Shorts views at $${SHORTS_RPM.toFixed(2)} Shorts RPM`);
console.log(`  1M Shorts views  = ${money((1_000_000 / 1000) * SHORTS_RPM)}`);
console.log(`  1M long-form     = ${money((1_000_000 / 1000) * RPM)}`);

const weeklyViewsNeeded = viewsForThreshold / 52;
console.log(`\nTHE ONE NUMBER TO TRACK`);
console.log(`  ${fmt(weeklyViewsNeeded)} long-form views per week hits the threshold in 12 months.`);
console.log('');
