// We pitch a twelve-point audit. Our own pages should pass it.
// This runs the exact same checks, in the same browser, against what we send.

const fs = require('fs');
const path = require('path');
const { auditRendered, chromium, EXEC } = require('./browser-audit');
const CHECKS = require('./checks');

async function selfCheck(dirs, root) {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const out = [];
  for (const slug of dirs) {
    const file = path.join(root, 'clients', slug, 'index.html');
    if (!fs.existsSync(file)) continue;
    const r = await auditRendered('file://' + file, { timeout: 20000, browser });
    // HTTPS is a property of where it gets hosted, not of the page itself.
    r.checks.https = true;
    const failed = CHECKS.filter((c) => !r.checks[c.key]);
    out.push({ slug, failed: failed.map((c) => c.key), pass: CHECKS.length - failed.length });
  }
  await browser.close().catch(() => {});
  return out;
}

module.exports = { selfCheck };
