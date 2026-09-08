// Skips near-duplicate photos — the same moment shot twice, a few frames
// apart, which a byte/dimension check won't catch (urban-cutz handed back
// two different-resolution photos of the identical haircut, half a second
// apart). Computes an 8x8 grayscale average-hash per image on the same
// Chromium canvas embed-photo.js already uses for resizing — no new
// dependency — and drops anything too close to one already kept.

const { chromium, EXEC } = require('./browser-audit');

const SIZE = 8;
const THRESHOLD = 10;   // out of 64 bits; near-identical crops land under ~6

function hamming(a, b) {
  let n = a ^ b, count = 0n;
  while (n) { count += n & 1n; n >>= 1n; }
  return count;
}

async function hashOf(page, buf, mime) {
  const src = `data:${mime};base64,${buf.toString('base64')}`;
  return page.evaluate(async ({ src, SIZE }) => {
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = src; });
    const c = document.createElement('canvas');
    c.width = SIZE; c.height = SIZE;
    const ctx = c.getContext('2d');
    ctx.drawImage(img, 0, 0, SIZE, SIZE);
    const data = ctx.getImageData(0, 0, SIZE, SIZE).data;
    const gray = [];
    for (let i = 0; i < data.length; i += 4) gray.push((data[i] + data[i + 1] + data[i + 2]) / 3);
    const avg = gray.reduce((a, b) => a + b, 0) / gray.length;
    let bits = 0n;
    for (const g of gray) { bits <<= 1n; if (g >= avg) bits |= 1n; }
    return bits.toString();
  }, { src, SIZE });
}

// files: [{ buf: Buffer, mime: string }]. Returns the indices worth keeping,
// in input order, with anything near-identical to an earlier one dropped.
async function keepDistinct(files, { browser } = {}) {
  const own = !browser;
  const b = browser || await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const page = await b.newPage();
  await page.goto('about:blank');
  const kept = [];
  const keptHashes = [];
  try {
    for (let i = 0; i < files.length; i++) {
      let h;
      try { h = BigInt(await hashOf(page, files[i].buf, files[i].mime)); }
      catch { continue; }   // a file that won't decode is dropped, not kept blind
      const tooClose = keptHashes.some((kh) => hamming(h, kh) < THRESHOLD);
      if (!tooClose) { kept.push(i); keptHashes.push(h); }
    }
  } finally {
    await page.close();
    if (own) await b.close();
  }
  return kept;
}

module.exports = { keepDistinct };
