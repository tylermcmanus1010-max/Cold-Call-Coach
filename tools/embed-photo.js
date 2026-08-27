// Embeds a local image into the page as a data URI, resized and re-encoded so
// the file stays small enough to email. Uses the browser we already have for
// auditing rather than adding an image library.

const fs = require('fs');
const path = require('path');
const { chromium, EXEC } = require('./browser-audit');

const MAX_W = 1400, QUALITY = 0.82;

async function embed(files) {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('about:blank');
  const out = [];
  for (const f of files) {
    const buf = fs.readFileSync(f);
    const mime = /\.png$/i.test(f) ? 'image/png' : /\.webp$/i.test(f) ? 'image/webp' : 'image/jpeg';
    const src = `data:${mime};base64,${buf.toString('base64')}`;
    const dataUri = await page.evaluate(async ({ src, MAX_W, QUALITY }) => {
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = src; });
      const scale = Math.min(1, MAX_W / img.naturalWidth);
      const c = document.createElement('canvas');
      c.width = Math.round(img.naturalWidth * scale);
      c.height = Math.round(img.naturalHeight * scale);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      return c.toDataURL('image/jpeg', QUALITY);
    }, { src, MAX_W, QUALITY });
    out.push({ file: path.basename(f), before: buf.length, after: dataUri.length, src: dataUri });
  }
  await browser.close().catch(() => {});
  return out;
}

module.exports = { embed };
