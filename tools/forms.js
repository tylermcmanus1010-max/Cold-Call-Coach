// Finds the contact form on a lead's own website.
//
// Tyler cannot make phone calls from his desk job, which until now has meant
// the business only ran at 5am and after 4pm. A contact form is the one
// channel that works at 11am on a Tuesday, and it solves a second problem at
// the same time: we hold email addresses for three of a hundred and eight
// leads, and guessing one is forbidden. A contact form is the business's own
// published inbox. Using it reaches the right person without inventing an
// address for them.
//
// This finds the form and describes it. It does not submit anything — see
// POLAR.md for how the submitting is done, and the limits on it.

const fs = require('fs');
const path = require('path');
const { chromium, EXEC } = require('./browser-audit');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'outreach');

const CONTACT_LINK = /contact|get.?in.?touch|reach.?us|request|quote|estimate|appointment|book|schedule|consult/i;

// A CAPTCHA is a deliberate "no automated submissions" sign. We record that it
// is there and stop; we do not solve it, and we do not work around it.
const CAPTCHA = /recaptcha|hcaptcha|turnstile|captcha/i;

// Some sites say it in words. That is a request, and it is honoured.
const NO_SOLICIT = /no solicit|no sales|not accepting solicit|do not contact.{0,20}sales|solicitors will be/i;

async function readForm(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);

  return page.evaluate(() => {
    const all = (s) => [...document.querySelectorAll(s)];
    const html = document.documentElement.innerHTML;
    const body = document.body.innerText || '';

    // The form most likely to be the contact form: the one with a textarea.
    // A single-line form is usually a search box or a newsletter signup.
    const forms = all('form').map((f) => {
      const fields = [...f.querySelectorAll('input,textarea,select')]
        .filter((el) => !/hidden|submit|button/i.test(el.type || ''))
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.type || '',
          name: el.name || el.id || '',
          label: (el.getAttribute('placeholder')
                  || el.getAttribute('aria-label')
                  || (el.labels && el.labels[0] && el.labels[0].innerText)
                  || '').replace(/\s+/g, ' ').trim().slice(0, 60),
          required: el.required === true,
        }));
      const submit = f.querySelector('[type=submit],button');
      return {
        fields,
        hasTextarea: fields.some((x) => x.tag === 'textarea'),
        submitText: submit ? (submit.value || submit.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40) : '',
      };
    }).filter((f) => f.fields.length >= 2);

    forms.sort((a, b) => (b.hasTextarea ? 1 : 0) - (a.hasTextarea ? 1 : 0) || b.fields.length - a.fields.length);

    return {
      url: location.href,
      form: forms[0] || null,
      formCount: forms.length,
      captcha: /recaptcha|hcaptcha|turnstile|captcha/i.test(html),
      noSolicit: /no solicit|no sales|not accepting solicit|solicitors will be/i.test(body),
      // An address the business publishes on its own contact page is not a
      // guessed address. Recorded, never used automatically — Tyler decides.
      published: [...new Set(all('a[href^="mailto:"]')
        .map((a) => a.getAttribute('href').replace(/^mailto:/, '').split('?')[0].trim().toLowerCase())
        .filter((e) => /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(e)))].slice(0, 4),
      // Some businesses only offer a third-party booker. Worth knowing: it
      // means somebody already sells them software.
      booker: [...new Set(all('a[href]').map((a) => a.href)
        .filter((h) => /calendly|acuity|vagaro|booksy|square|setmore|schedulicity|squarespace-scheduling/i.test(h)))].slice(0, 3),
    };
  });
}

async function findForm(browser, site, name) {
  const ctx = await browser.newContext({
    viewport: { width: 1200, height: 900 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
  });
  const page = await ctx.newPage();
  try {
    const home = await readForm(page, site);
    // A contact form on the homepage is the happy case.
    if (home.form && home.form.hasTextarea) return { ...home, foundOn: 'homepage' };

    const links = await page.evaluate((re) => {
      const rx = new RegExp(re, 'i');
      const origin = location.origin;
      return [...new Set([...document.querySelectorAll('a[href]')]
        .filter((a) => a.href.startsWith(origin) && (rx.test(a.href) || rx.test(a.innerText || '')))
        .map((a) => a.href.replace(/#.*$/, '')))].slice(0, 4);
    }, CONTACT_LINK.source);

    for (const url of links) {
      try {
        const r = await readForm(page, url);
        if (r.form && r.form.hasTextarea) return { ...r, foundOn: 'contact page' };
        if (r.published.length && !home.published.length) home.published = r.published;
      } catch { /* a page that will not load is not a form */ }
    }
    return { ...home, foundOn: home.form ? 'homepage (no message box)' : 'none found' };
  } finally {
    await ctx.close();
  }
}

async function run(rows, { log = console.log } = {}) {
  await require('./reaudit').assertOnline();
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const out = [];
  try {
    for (const r of rows) {
      try {
        const f = await findForm(browser, r.site, r.name);
        out.push({ slug: r.slug, name: r.name, phone: r.phone, state: r.state, city: r.city,
                   category: r.category, site: r.site, ...f });
        const tag = f.noSolicit ? 'NO SOLICITING — skipped'
          : f.captcha ? `${f.foundOn} · CAPTCHA`
          : f.form ? `${f.foundOn} · ${f.form.fields.length} fields`
          : 'no form';
        log(`  ${f.form && !f.noSolicit ? '✓' : '·'} ${r.name.slice(0, 34).padEnd(36)} ${tag}`);
      } catch (e) {
        out.push({ slug: r.slug, name: r.name, site: r.site, error: e.message.split('\n')[0] });
        log(`  ! ${r.name.slice(0, 34).padEnd(36)} ${e.message.split('\n')[0].slice(0, 50)}`);
      }
    }
  } finally {
    await browser.close();
  }

  fs.writeFileSync(path.join(OUT, 'forms.json'), JSON.stringify({
    _readMe: 'Contact forms found on leads\' own websites. Nothing has been submitted. ' +
             'Addresses under "published" were printed by the business on its own contact page — ' +
             'they are not guessed, but using one is a judgement call, not an automatic yes.',
    foundAt: new Date().toISOString(),
    sites: out,
  }, null, 2));
  return out;
}

module.exports = run;
module.exports.findForm = findForm;
