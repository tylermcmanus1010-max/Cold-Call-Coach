// Reads a business's own website before we rebuild it.
//
// Every page built from guesses is a page of guesses. Pearl Cosmetic scored
// 10/12 on invented services and jumped to 12/12 the moment their real ones
// went in — because their actual site had a laser that does fillings with no
// needle, crowns finished in a single visit, a $399 membership plan and three
// testimonials with real names. None of that could be guessed, and all of it
// was sitting on their own homepage.
//
// So: harvest first, build second. This crawls the site and dumps what it
// finds into clients/<slug>/harvest.json for a human to read. It never writes
// business.json — the judgement about what is true and what belongs on the
// page stays with a person.

const fs = require('fs');
const path = require('path');
const { auditRendered, chromium, EXEC } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');
const MAX_PAGES = 9;

// The pages that carry the material worth having.
const WORTH_VISITING = /about|service|treatment|procedure|team|staff|doctor|meet|review|testimonial|contact|price|pricing|fee|membership|plan|technolog|hour/i;

async function readPage(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  // lazy content only exists once it has been scrolled past
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 600) {
      scrollTo(0, y); await new Promise((r) => setTimeout(r, 60));
    }
    scrollTo(0, 0);
  });
  await page.waitForTimeout(400);

  return page.evaluate(() => {
    const txt = (el) => (el.innerText || '').replace(/\s+/g, ' ').trim();
    const all = (sel) => [...document.querySelectorAll(sel)];
    const body = document.body.innerText || '';

    return {
      url: location.href,
      title: (document.title || '').trim(),
      headings: all('h1,h2,h3').map(txt).filter((t) => t && t.length < 120).slice(0, 60),

      // Anything that reads like someone talking about the business.
      quotes: all('blockquote, [class*="testimonial" i], [class*="review" i], [id*="testimonial" i]')
        .map(txt).filter((t) => t.length > 40 && t.length < 900).slice(0, 20),

      // Prices, with the sentence around them, so the number has meaning.
      prices: (body.match(/[^.\n]{0,90}\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?\/\s?(?:yr|year|mo|month))?[^.\n]{0,60}/gi) || [])
        .map((s) => s.replace(/\s+/g, ' ').trim()).slice(0, 25),

      emails: [...new Set([
        ...all('a[href^="mailto:"]').map((a) => a.getAttribute('href').replace(/^mailto:/, '').split('?')[0]),
        ...(body.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) || []),
      ])].slice(0, 10),

      phones: [...new Set(all('a[href^="tel:"]').map((a) => a.getAttribute('href').slice(4)))].slice(0, 6),

      // Days beside times — the shape opening hours actually take.
      hours: (body.match(/(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?[^\n]{0,60}\d{1,2}[:.]\d{2}\s?(?:am|pm)[^\n]{0,30}/gi) || [])
        .map((s) => s.replace(/\s+/g, ' ').trim()).slice(0, 15),

      // "Dr Smith", "Sarah Jones, DDS" — the people worth naming on a page.
      people: [...new Set(body.match(/\b(?:Dr\.?|Doctor)\s+[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+)?|\b[A-Z][A-Za-z'-]+\s+[A-Z][A-Za-z'-]+,\s*(?:DDS|DMD|MD|RDH|DVM|PhD)\b/g) || [])].slice(0, 12),

      social: [...new Set(all('a[href]').map((a) => a.href)
        .filter((h) => /facebook|instagram|yelp|twitter|x\.com|linkedin|youtube|tiktok|google\.com\/maps/i.test(h)))].slice(0, 10),

      links: all('a[href]').map((a) => a.href).filter((h) => /^https?:/.test(h)),
      text: body.replace(/\s+/g, ' ').trim().slice(0, 12000),
    };
  });
}

async function harvest(slug, { log = console.log } = {}) {
  const f = path.join(ROOT, 'clients', slug, 'business.json');
  if (!fs.existsSync(f)) throw new Error(`no such client: ${slug}`);
  const b = JSON.parse(fs.readFileSync(f, 'utf8'));
  const start = b.currentSite;
  if (!start) throw new Error(`${slug} has no currentSite to read`);

  // A sandboxed proxy answers CONNECT with 403, which reads identically to a
  // site refusing us — and "their site refused" is the wrong thing to tell
  // someone about a client who is about to pay them.
  await require('./reaudit').assertOnline();

  const probe = await auditRendered(start, { expectName: b.name });
  if (probe.blocked) throw new Error(`their site refused the check (${probe.reason}) — nothing to harvest`);
  if (probe.namesBusiness === false) {
    log(`  ⚠ the page never names ${b.name} — this may not be their site. Harvesting anyway; read it sceptically.`);
  }

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();
  const pages = [];
  const seen = new Set();

  try {
    const home = await readPage(page, start);
    seen.add(home.url.replace(/[#?].*$/, ''));
    pages.push(home);
    const origin = new URL(home.url).origin;

    const queue = [...new Set(home.links)]
      .filter((h) => h.startsWith(origin) && WORTH_VISITING.test(h))
      .filter((h) => !seen.has(h.replace(/[#?].*$/, '')))
      .slice(0, MAX_PAGES - 1);

    for (const url of queue) {
      const key = url.replace(/[#?].*$/, '');
      if (seen.has(key)) continue;
      seen.add(key);
      try { pages.push(await readPage(page, url)); log(`  read ${url}`); }
      catch (e) { log(`  skipped ${url} — ${e.message.split('\n')[0]}`); }
    }
  } finally {
    await browser.close();
  }

  // Fold the pages into one pile, deduplicated, for a person to read.
  const merge = (key) => [...new Set(pages.flatMap((p) => p[key] || []))];
  const out = {
    _readMe: 'Material taken off their own website. NOTHING here is verified and nothing has been ' +
             'written to business.json — decide what is true and what belongs on the page yourself. ' +
             'Quotes are the valuable part: real testimonials with real names are the one gap our own ' +
             'checks always flag, and they cannot be invented.',
    harvestedAt: new Date().toISOString().slice(0, 10),
    from: start,
    namesBusiness: probe.namesBusiness,
    pagesRead: pages.map((p) => p.url),
    emails: merge('emails'),
    phones: merge('phones'),
    hours: merge('hours'),
    people: merge('people'),
    prices: merge('prices'),
    social: merge('social'),
    headings: merge('headings'),
    quotes: merge('quotes'),
    pageText: Object.fromEntries(pages.map((p) => [p.url, p.text])),
  };

  fs.writeFileSync(path.join(ROOT, 'clients', slug, 'harvest.json'), JSON.stringify(out, null, 2));
  return out;
}

module.exports = harvest;
