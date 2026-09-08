// Renders business.json -> one self-contained index.html.
// No build step, no dependencies, no external requests: the file works
// from a double-click, an email attachment, or any host.

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const digits = (s) => String(s || '').replace(/[^\d+]/g, '');

function mapsUrl(a) {
  if (!a) return '';
  const q = [a.street, a.city, a.state, a.zip].filter(Boolean).join(', ');
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(q);
}

function addressLine(a) {
  if (!a) return '';
  return [a.street, [a.city, a.state].filter(Boolean).join(', '), a.zip].filter(Boolean).join(' · ');
}

// business.template.json ships a *plausible-looking* default (Mon-Fri
// 8-5, Sat 9-2, Sun closed) for a human to overwrite or delete — not blank,
// so the length/blank checks elsewhere in this file don't catch it. Caught
// for real: every autonomously-built page today showed this exact same
// invented schedule as if it were verified, for a bakery, a salon and an
// insurance agency alike. Only real hours — anything that doesn't match
// this signature — should ever render or reach the schema markup.
const PLACEHOLDER_HOURS_SIG = 'Mo-Fr 08:00-17:00|Sa 09:00-14:00';
function realHours(hours) {
  const sig = (hours || []).map((h) => h.schema || '').filter(Boolean).join('|');
  return sig && sig === PLACEHOLDER_HOURS_SIG ? [] : (hours || []);
}

// Reads the pixel dimensions straight out of an embedded JPEG or PNG header.
// Twenty lines beats a dependency, and the alternative is shipping blind.
// Returns null whenever it cannot tell — an unreadable photo is kept, never
// dropped on a guess.
function imageSize(src) {
  const m = /^data:image\/(jpeg|jpg|png|gif|webp);base64,(.+)$/i.exec(String(src || ''));
  if (!m) return null;
  let buf;
  try { buf = Buffer.from(m[2], 'base64'); } catch { return null; }
  const kind = m[1].toLowerCase();
  if (kind === 'png' && buf.length > 24 && buf.readUInt32BE(12) === 0x49484452) {
    return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), bytes: buf.length };
  }
  if (kind === 'jpeg' || kind === 'jpg') {
    let i = 2;
    while (i + 9 < buf.length) {
      if (buf[i] !== 0xff) { i += 1; continue; }
      const marker = buf[i + 1];
      // SOF0..SOF15, skipping the four that are not frame headers
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc, 0xd8].includes(marker)) {
        return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7), bytes: buf.length };
      }
      i += 2 + (i + 3 < buf.length ? buf.readUInt16BE(i + 2) : 0);
    }
  }
  return { w: 0, h: 0, bytes: buf.length };
}

// Caught for real: Impression Dental's hero was a solid black block, because
// the harvester had picked up an 11 x 658 pixel sliver — a border graphic off
// their old page — and object-fit:cover happily smeared it across the whole
// top of the page. It weighed 1 KB. Nothing complained, because a broken
// photo in a browser is just a rectangle.
//
// A photograph of a real business has some minimum substance to it. Anything
// that is a hairline, a spacer, or too few bytes to hold a scene is not
// evidence and must not lead the page. When the dimensions cannot be read at
// all, the photo stays — this drops what it can prove, never what it guesses.
function usablePhoto(src) {
  const s = imageSize(src);
  if (!s) return true;                       // not an embedded raster: leave it alone
  if (s.bytes < 2600) return false;          // too little data to be a photograph
  if (!s.w || !s.h) return true;             // header unreadable: keep it
  if (Math.min(s.w, s.h) < 140) return false;
  if (Math.max(s.w, s.h) / Math.min(s.w, s.h) > 6) return false;    // a hairline, not a shot
  return true;
}

// Some of what the harvester brings back is a banner off the old site — 950 x
// 270, the whole point of it the words across the middle. Cropped square for
// a phone hero it becomes an unreadable slice. A picture this wide is shown
// whole, at its own proportions, or not at all.
function photoShape(src) {
  const s = imageSize(src);
  const ar = s && s.w && s.h ? s.w / s.h : 0;
  return { ar, wide: ar >= 2 };
}

function jsonld(b) {
  const a = b.address || {};
  const data = {
    '@context': 'https://schema.org',
    '@type': b.schemaType || 'LocalBusiness',
    name: b.name,
    description: b.tagline,
    telephone: b.phone,
    url: b.liveUrl || b.newUrl || undefined,
    address: a.street ? {
      '@type': 'PostalAddress',
      streetAddress: a.street, addressLocality: a.city,
      addressRegion: a.state, postalCode: a.zip, addressCountry: 'US',
    } : undefined,
    areaServed: (b.serviceArea || []).map((n) => ({ '@type': 'Place', name: n })),
    openingHours: realHours(b.hours).map((h) => h.schema).filter(Boolean),
    priceRange: b.priceRange || undefined,
    aggregateRating: b.rating ? {
      '@type': 'AggregateRating',
      ratingValue: String(b.rating.value),
      reviewCount: String(b.rating.count),
    } : undefined,
  };
  // JSON-LD sits in a <script> block: escaping "<" as \u003c keeps the JSON
  // valid while making it impossible to open or close a tag from business data.
  return JSON.stringify(data, (k, v) => (v === undefined ? undefined : v), 2)
    .replace(/</g, '\\u003c');
}

function stars(n) {
  const full = Math.round(Number(n) || 0);
  return '<span class="stars" aria-label="' + esc(n) + ' out of 5">' +
    '★★★★★'.slice(0, full).padEnd(5, '☆') + '</span>';
}

// business.template.json also ships a *default accent* — the same teal-green
// on every scaffolded client — for a human to replace with a colour pulled
// from the business's own logo or sign. Nobody ever did: 59 of 90 client
// folders still carried this exact hex, so every page the autonomous path
// built came out the same green regardless of trade, and the per-voice
// palettes below were dead code that never once rendered. Same discipline as
// the hours signature above: a value nobody chose is not a choice.
const PLACEHOLDER_ACCENTS = new Set(['#0f6b5c']);
function chosenAccent(t) {
  const c = String((t || {}).accent || '').trim().toLowerCase();
  return c && !PLACEHOLDER_ACCENTS.has(c) ? c : '';
}

// A barbershop should not read like an endodontist. Each trade gets its own
// voice — and a voice here is not a colour swap. It is the typeface class,
// the weight and tracking, the corner radius, the hero *shape*, whether
// sections are numbered, whether lists sit in boxes or hang off rules,
// whether the trust facts sit in a grid or run as a band, and how photography
// is toned. All of it built from system fonts, so the page still makes no
// network request and still opens instantly from an email attachment.
//
// Tokens:
//   display/body/weight/tracking  type
//   heroCase/heroSize/rule/radius shape
//   accent/ink/paper/soft/line    palette (accent is a default; theme.accent wins)
//   hero      accent | dark | calm | editorial | card | plain   hero construction
//   signals   band | grid | quiet     how real trust facts are presented
//   frame     boxed | ruled | plain   how service rows and cards are bounded
//   photo     bw | soft | full        photography treatment
//   numbered  section rhythm: 01 / 02 / 03 down the page
//   air       vertical rhythm multiplier for sections
const VOICES = {
  trade: {   // plumbers, roofers, HVAC, contractors, gutters
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 800, tracking: '-.035em', radius: '4px', caseLabel: 'uppercase',
    labelTrack: '.16em', heroSize: 'clamp(36px,7.2vw,68px)', heroCase: 'none', rule: '3px',
    accent: '#c2410c', ink: '#17140f', paper: '#fff', soft: '#f4f2ef', line: '#e0dcd6',
    texture: 'diagonal', hero: 'accent', signals: 'band', frame: 'ruled',
    photo: 'bw', numbered: true, air: '1',
  },
  barber: {  // barbershops, tattoo, men's grooming
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 900, tracking: '-.045em', radius: '0px', caseLabel: 'uppercase',
    labelTrack: '.22em', heroSize: 'clamp(31px,6.6vw,60px)', heroCase: 'uppercase', rule: '2px',
    accent: '#b0271f', ink: '#101010', paper: '#fff', soft: '#f2f1ef', line: '#dedbd6',
    texture: 'none', hero: 'dark', signals: 'band', frame: 'ruled',
    photo: 'bw', numbered: true, air: '1',
  },
  care: {    // dentists, doctors, clinics, vets, chiro, optician
    display: '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 600, tracking: '-.018em', radius: '18px', caseLabel: 'uppercase',
    labelTrack: '.15em', heroSize: 'clamp(32px,5.4vw,52px)', heroCase: 'none', rule: '1px',
    accent: '#0e6a72', ink: '#111a1d', paper: '#fff', soft: '#f2f7f7', line: '#e2ebeb',
    texture: 'none', hero: 'calm', signals: 'quiet', frame: 'plain',
    photo: 'full', numbered: false, air: '1.22',
  },
  beauty: {  // salons, nails, lash, spa, florists
    display: '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif',
    body: '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif',
    weight: 500, tracking: '.004em', radius: '0px', caseLabel: 'uppercase',
    labelTrack: '.3em', heroSize: 'clamp(33px,6vw,58px)', heroCase: 'none', rule: '1px',
    accent: '#8d3d5c', ink: '#1a1416', paper: '#fdfcfb', soft: '#f6f2f1', line: '#e6dedd',
    texture: 'none', hero: 'editorial', signals: 'quiet', frame: 'plain',
    photo: 'soft', numbered: true, air: '1.16',
  },
  food: {    // bakeries, cafés, restaurants, delis, caterers
    display: 'ui-rounded,"SF Pro Rounded","Segoe UI Variable Display",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 800, tracking: '-.03em', radius: '22px', caseLabel: 'uppercase',
    labelTrack: '.11em', heroSize: 'clamp(35px,6.6vw,62px)', heroCase: 'none', rule: '2px',
    // Deliberately not the cream-and-terracotta every generated page lands
    // on: white paper, a deep berry that reads patisserie rather than
    // "landing page", and warmth carried by the round type and the radius.
    accent: '#8a2846', ink: '#1d1416', paper: '#fff', soft: '#f8f4f2', line: '#e9dfda',
    texture: 'dot', hero: 'card', signals: 'grid', frame: 'boxed',
    photo: 'full', numbered: false, air: '1',
  },
  fitness: { // gyms, climbing, martial arts, yoga, training
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 900, tracking: '-.042em', radius: '2px', caseLabel: 'uppercase',
    labelTrack: '.2em', heroSize: 'clamp(34px,7.4vw,72px)', heroCase: 'uppercase', rule: '4px',
    accent: '#1d4ed8', ink: '#101116', paper: '#fff', soft: '#f1f2f5', line: '#dfe1e7',
    texture: 'diagonal', hero: 'dark', signals: 'band', frame: 'ruled',
    photo: 'bw', numbered: true, air: '1',
  },
  professional: { // law, insurance, finance, real estate, accounting
    display: 'Georgia,"Times New Roman",Times,serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 700, tracking: '-.012em', radius: '0px', caseLabel: 'uppercase',
    labelTrack: '.14em', heroSize: 'clamp(31px,5vw,50px)', heroCase: 'none', rule: '1px',
    accent: '#1e3a5f', ink: '#14181d', paper: '#fff', soft: '#f4f5f7', line: '#e0e3e8',
    texture: 'none', hero: 'plain', signals: 'quiet', frame: 'ruled',
    photo: 'soft', numbered: true, air: '1.1',
  },
  retail: {  // shops, boutiques, apparel, hardware, furniture, garden
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    body: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 700, tracking: '-.022em', radius: '12px', caseLabel: 'uppercase',
    labelTrack: '.13em', heroSize: 'clamp(34px,6.4vw,60px)', heroCase: 'none', rule: '2px',
    accent: '#2f6b3a', ink: '#141a15', paper: '#fff', soft: '#f3f6f3', line: '#e0e6e0',
    texture: 'dot', hero: 'card', signals: 'grid', frame: 'boxed',
    photo: 'full', numbered: false, air: '1',
  },
};

function voiceOf(b) {
  if (b.voice && VOICES[b.voice]) return b.voice;
  const c = (b.category || '').toLowerCase();
  // A barbershop is filed under "hairdresser" by every data source we pull
  // from, so the category alone routes six real shops into the salon voice —
  // Palatino and wide-tracked small caps for a place that does skin fades.
  // The name is where the trade actually shows.
  const n = ((b.name || '') + ' ' + (b.category || '')).toLowerCase();
  // \b on both sides, or "Facades Inc" — a construction firm — comes out a
  // barbershop.
  if (/\bbarber|\btattoo\b|\bmen'?s? (?:cut|groom)|\bfades?\b/.test(n)) return 'barber';
  if (/dent|endodont|orthodont|medical|doctor|clinic|health|vet|chiro|ortho|optic|eyeglass|pharmac/.test(c)) return 'care';
  if (/salon|nail|spa|beauty|hair|massage|florist|flower|lash|brow|wax|groom/.test(c)) return 'beauty';
  if (/baker|café|cafe|coffee|restaurant|deli|food|cater|patisserie|cheesecake|cupcake|bar\b/.test(c)) return 'food';
  if (/climb|fitness|gym|martial|jitsu|jiu|yoga|pilates|training(?! systems)|gymnasium/.test(c)) return 'fitness';
  if (/law|attorney|legal|insurance|finance|accounting|realt|real estate|title company/.test(c)) return 'professional';
  if (/shop|store|apparel|boutique|hardware|furniture|nursery|garden|parts|sportswear|interior/.test(c)) return 'retail';
  if (/plumb|roof|auto|repair|smog|tyre|tire|electric|hvac|contractor|construct|landscap|clean|gutter|upholster|window|mechanical|pool|tub/.test(c)) return 'trade';
  return 'trade';
}

function render(b) {
  const tel = digits(b.phone);
  const a = b.address || {};
  const voice = voiceOf(b);
  const v = VOICES[voice];
  // A human-chosen color (from business.json) always wins. Absent one — the
  // autonomous outreach path, where nobody sat down and picked a hex from a
  // logo — the voice's own default palette stands in, so the page still
  // reads as fitted to the trade rather than every unbranded lead landing on
  // the same green. The template's own shipped default counts as "absent".
  const accent = chosenAccent(b.theme) || v.accent;

  // A template placeholder — every field blank, left over from
  // business.template.json — is not content. It used to sail straight
  // through the old `b.services?.length` checks (the array has length 1,
  // it's just full of empty strings) and render as a blank, broken-looking
  // stub section. Caught for real: an autonomously-built page with an
  // empty "Services" row nobody could tap, an empty team card with no
  // name. Real emptiness — the array deleted, per this repo's own
  // convention — is the only thing that should hide a section now.
  const real = (arr, keys) => (arr || []).filter((o) =>
    keys.some((k) => String((o || {})[k] || '').trim()));
  const services = real(b.services, ['name']);
  const team = real(b.team, ['name']);
  const reviews = real(b.reviews, ['text']);
  const highlights = real(b.highlights, ['value', 'label']);
  const photos = (b.photos || [])
    .map((p) => (typeof p === 'string' ? { src: p } : p))
    .filter((p) => p && p.src && usablePhoto(p.src))
    .map((p) => ({ ...p, ...photoShape(p.src) }));
  const hours = realHours(b.hours);

  // A menu earns its layout only when there is something to choose between.
  const cents = (p) => {
    const m = String(p || '').match(/(\d+(?:\.\d{1,2})?)/);
    return m ? Math.round(parseFloat(m[1]) * 100) : 0;
  };
  const mins = (d) => {
    const m = String(d || '').match(/(\d+)\s*(h|hr|hour|m|min)/i);
    if (!m) return 0;
    return /^h/i.test(m[2]) ? +m[1] * 60 : +m[1];
  };
  const groups = (() => {
    const out = new Map();
    for (const s of services) {
      const k = s.group || '';
      if (!out.has(k)) out.set(k, []);
      out.get(k).push(s);
    }
    return [...out.entries()];
  })();
  const ink = b.theme?.ink || v.ink;
  const hero = b.theme?.heroImage;

  // The reference the owner sent paces itself with 01 / 02 / 03 down the
  // page. The numbers here are the page's own real section order — computed
  // as sections are emitted, never a fixed list — so a page with three
  // sections counts to three and a page with six counts to six.
  // `tagline` is whatever the scout could scrape, which for thirteen of these
  // clients is the old site's whole meta description — 496 characters, in
  // Studio Mani's case. Set at hero display size that is not a headline, it
  // is a wall of type that fills a 390px screen before the phone number.
  // A paragraph is a paragraph: it drops to the lede, where it reads fine,
  // and the headline slot takes the one short true thing we already have —
  // their name. Nothing here is invented; the same words appear either way.
  const HEADLINE_MAX = 90;
  const rawHead = String(b.headline || b.tagline || '').trim();
  const headTooLong = !b.headline && rawHead.length > HEADLINE_MAX;
  const headline = headTooLong ? b.name : rawHead;
  const subhead = b.subhead || (headTooLong ? rawHead : '');
  // An authored headline is theirs to be long if they want it, but it still
  // has to fit: past this length the hero steps down a size instead of
  // running off the screen.
  const headLong = String(headline || '').length > 62;

  let secN = 0;
  const eyebrow = (text) => {
    secN += 1;
    return `<div class="eyebrow">${v.numbered
      ? `<span class="num">${String(secN).padStart(2, '0')}</span>` : ''}${esc(text)}</div>`;
  };

  // Real trust facts, presented three different ways depending on the voice:
  // a moving band for the loud trades, a bordered grid for the shops, and a
  // quiet ruled row where calm is the product. Nothing is invented — this
  // renders only what `highlights` already holds, and nothing at all when
  // it holds nothing.
  const signalItems = highlights.map((h) =>
    `<span class="sig"><b>${esc(h.value)}</b>${h.label ? `<i>${esc(h.label)}</i>` : ''}</span>`).join('');
  // A band needs enough content to read as a run rather than a stray line.
  const bandOn = v.signals === 'band' && highlights.length >= 3;
  const signalBand = bandOn ? `
<div class="band" role="list" aria-label="At a glance">
  <div class="band-track">
    <div class="band-run">${signalItems}</div>
    <div class="band-run" aria-hidden="true">${signalItems}</div>
  </div>
</div>` : '';
  const signalBlock = (!highlights.length || bandOn) ? '' :
    `<div class="trust ${v.signals === 'quiet' ? 'quiet' : 'grid'} rise" style="--i:5">${highlights.map((h) =>
      `<div><b>${esc(h.value)}</b><span>${esc(h.label)}</span></div>`).join('')}</div>`;

  const nav = [
    services.length && ['Services', '#services'],
    photos.length > 1 && ['Work', '#work'],
    team.length && ['Team', '#team'],
    b.about && ['About', '#about'],
    reviews.length && ['Reviews', '#reviews'],
    ['Contact', '#contact'],
  ].filter(Boolean);

  return `<!doctype html>
<html lang="en" class="v-${voice} f-${v.frame} ph-${v.photo}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(b.name)}${b.category ? ' — ' + esc(b.category) : ''}${a.city ? ' in ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</title>
<meta name="description" content="${esc(b.tagline)}${b.phone ? ' Call ' + esc(b.phone) + '.' : ''}">
<meta property="og:type" content="website">${b.liveUrl ? `
<link rel="canonical" href="${esc(b.liveUrl)}">
<meta property="og:url" content="${esc(b.liveUrl)}">` : ''}
<meta property="og:title" content="${esc(b.name)}">
<meta property="og:description" content="${esc(b.tagline)}">
<meta name="twitter:card" content="summary_large_image">${b.logo ? `
<meta property="og:image" content="${esc(b.logo)}">` : ''}
<meta name="theme-color" content="${esc(accent)}">
<link rel="icon" href="${b.logo ? esc(b.logo) : 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="${accent}"/><text x="16" y="22" font-size="17" font-family="system-ui,sans-serif" font-weight="700" fill="#fff" text-anchor="middle">${(b.name || '?').trim()[0].toUpperCase()}</text></svg>`
)}">
<script type="application/ld+json">
${jsonld(b)}
</script>
<script>document.documentElement.className+=' js';</script>
<style>
  :root{
    --accent:${accent};
    --accent-ink:#fff;
    --ink:${ink};
    --muted:color-mix(in srgb, ${ink} 58%, #fff);
    --line:${v.line};
    --bg:${v.paper};
    --card:#fff;
    --soft:${v.soft};
    --radius:${v.radius};
    --wrap:1080px;
    --display:${v.display};
    --body:${v.body};
    --display-weight:${v.weight};
    --tracking:${v.tracking};
    --label-case:${v.caseLabel};
    --label-track:${v.labelTrack};
    --hero-size:${v.heroSize};
    --hero-case:${v.heroCase};
    --rule:${v.rule};
    --air:${v.air};
    --btn-radius:${{ trade: '3px', barber: '0px', care: '999px', beauty: '0px',
      food: '999px', fitness: '2px', professional: '0px', retail: '999px' }[voice] || '999px'};
    --ease:cubic-bezier(.2,.7,.2,1);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    margin:0;background:var(--bg);color:var(--ink);
    font:16px/1.62 var(--body);
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}
  a{color:inherit}
  h1,h2,h3{line-height:1.13;margin:0;font-family:var(--display);
    font-weight:var(--display-weight);letter-spacing:var(--tracking);text-wrap:balance}
  h2{font-size:clamp(25px,3.6vw,36px);margin-bottom:10px}
  p{margin:0 0 14px}
  /* the header is sticky, so an anchored jump must leave room for it or the
     first line of the section lands underneath. */
  section{padding:calc(64px * var(--air)) 0;border-top:1px solid var(--line);scroll-margin-top:72px}
  /* Section headers carry the page's rhythm. A hairline the width of the
     column above the label does more for hierarchy than another box. */
  .eyebrow{font-size:11.5px;font-weight:700;letter-spacing:var(--label-track);
    text-transform:var(--label-case);color:var(--accent);margin-bottom:14px;
    display:flex;align-items:baseline;gap:12px}
  .eyebrow .num{font-family:var(--display);font-size:12.5px;font-weight:var(--display-weight);
    font-variant-numeric:tabular-nums;letter-spacing:0;color:var(--ink);opacity:.34}
  .lede{color:var(--muted);max-width:60ch;font-size:17px}

  /* a supplied logo leads the hero. Stacked wordmarks (name inside the art)
     are unreadable in a 66px header bar, so they belong here at full size. */
  .hero .logo{display:block;max-width:min(100%,var(--logo-w,300px));height:auto;
    margin:0 0 24px;mix-blend-mode:multiply}
  /* multiply needs something light behind it; on a full-bleed accent hero the
     logo keeps its own white card instead. */
  .v-trade .hero .logo,.v-barber .hero .logo,.v-fitness .hero .logo{
    mix-blend-mode:normal;background:#fff;border-radius:6px;padding:10px}
  .v-care .hero .logo,.v-food .hero .logo{margin-left:auto;margin-right:auto}

  /* header */
  header{position:sticky;top:0;z-index:50;background:color-mix(in srgb, var(--bg) 92%, transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .bar{display:flex;align-items:center;gap:18px;height:66px}
  .brand{font-family:var(--display);font-weight:var(--display-weight);letter-spacing:var(--tracking);
    font-size:18px;text-decoration:none;margin-right:auto;display:flex;align-items:center;gap:10px;
    min-width:0}
  /* the bar is a fixed height, so a long name has to shrink rather than wrap */
  .brand .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  @media (max-width:520px){ .brand{font-size:16px} }
  @media (max-width:400px){ .brand{font-size:15px} }
  .mark{width:30px;height:30px;border-radius:clamp(0px,var(--radius),9px);background:var(--accent);color:#fff;display:grid;place-items:center;font-size:15px;flex:none}
  /* a stacked logo is unreadable in a 66px bar, so the header takes a compact
     mark and sets the name in type beside it. */
  .mark-img{width:30px;height:30px;object-fit:contain;flex:none;display:block}
  nav{display:flex;gap:22px}
  nav a{color:var(--muted);text-decoration:none;font-size:15px;font-weight:500}
  nav a:hover{color:var(--ink)}
  /* Pill buttons on every page is one of the tells that a page came off a
     template. The shape follows the voice: a pill for the soft trades, a
     square edge for the ones whose whole pitch is that they are not soft. */
  .btn{
    display:inline-flex;align-items:center;justify-content:center;gap:8px;
    padding:13px 22px;border-radius:var(--btn-radius);font-weight:650;font-size:15px;
    text-decoration:none;border:1px solid transparent;white-space:nowrap;
  }
  .v-barber .btn,.v-fitness .btn{text-transform:uppercase;letter-spacing:.09em;
    font-size:13px;font-weight:800;padding:14px 22px}
  .v-beauty .btn{letter-spacing:.14em;text-transform:uppercase;font-size:12px;
    font-family:var(--display);font-weight:600;padding:15px 26px}
  .btn-primary{background:var(--accent);color:var(--accent-ink)}
  .btn-primary:hover{filter:brightness(.92)}
  .btn-ghost{border-color:var(--line);background:var(--card);color:var(--ink)}
  .btn-ghost:hover{border-color:var(--ink)}
  .v-barber .btn-ghost,.v-professional .btn-ghost,.v-beauty .btn-ghost{border-color:var(--ink);background:transparent}

  /* hero */
  .hero{padding:74px 0 66px;position:relative;overflow:hidden}
  .hero::before{
    content:"";position:absolute;inset:0;z-index:-1;
    background:
      ${v.texture === 'diagonal'
        ? 'repeating-linear-gradient(-45deg, color-mix(in srgb, var(--accent) 5%, transparent) 0 2px, transparent 2px 22px),'
        : v.texture === 'dot'
        ? 'radial-gradient(color-mix(in srgb, var(--accent) 14%, transparent) 1.6px, transparent 1.6px) 0 0/22px 22px,'
        : ''}
      radial-gradient(760px 420px at 78% -8%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%),
      linear-gradient(180deg, var(--soft), var(--bg));
  }
  ${hero ? `.hero::after{content:"";position:absolute;inset:0;z-index:-2;background:url("${esc(hero)}") center/cover;opacity:.14}` : ''}

  /* A real photo of the actual business, not a texture — this is the
     difference between a page that looks like a template and one that
     looks like theirs. Stacked by default (photo reads as evidence right
     under the pitch); side-by-side on wide screens for the voices where a
     strong image belongs beside the headline, not under it. */
  .hero-shot{border-radius:var(--radius);overflow:hidden;margin-top:28px;
    aspect-ratio:4/3;background:var(--soft);border:1px solid var(--line)}
  .hero-shot img{width:100%;height:100%;object-fit:cover;display:block}
  /* A banner shown at its own proportions, whole. --ar carries the real
     ratio measured out of the file at render time. */
  .hero-shot.wide{aspect-ratio:var(--ar);background:var(--soft)}
  .hero-shot.wide img{object-fit:contain}
  /* On a phone — where this actually gets read — a photo boxed inside the
     page margins reads as a thumbnail. Bleeding it to the screen edges,
     taller, is what makes it feel like the front of the business rather
     than an attachment. */
  @media (max-width:760px){
    .hero-shot{margin:28px -22px 0;border-radius:0;border-left:0;border-right:0;
      aspect-ratio:1/1}
    /* A photo bled to the screen edges with nothing after it left a bar of
       hero colour hanging below it — most obvious on the dark heroes, where
       it read as an empty black band. If the photo is the last thing in the
       hero, it ends the hero. */
    .hero:has(.hero-grid.has-photo:last-child){padding-bottom:0}
  }
  @media (min-width:900px){
    .hero-grid.has-photo{display:grid;grid-template-columns:1fr;gap:0}
    .v-trade .hero-grid.has-photo,.v-food .hero-grid.has-photo,
    .v-fitness .hero-grid.has-photo,.v-retail .hero-grid.has-photo,
    .v-barber .hero-grid.has-photo{
      grid-template-columns:1.05fr .95fr;gap:40px;align-items:center}
    .v-trade .hero-grid.has-photo .hero-shot,.v-food .hero-grid.has-photo .hero-shot,
    .v-fitness .hero-grid.has-photo .hero-shot,.v-retail .hero-grid.has-photo .hero-shot,
    .v-barber .hero-grid.has-photo .hero-shot{
      margin-top:0;aspect-ratio:1/1}
  }
  .v-trade .hero-shot,.v-barber .hero-shot,.v-fitness .hero-shot{border-color:rgba(255,255,255,.28)}

  /* A second photo, cropped round, doing one job: proof this page was
     built from their real place, sitting right where the ask is made. */
  .cta-shot{width:104px;height:104px;border-radius:50%;overflow:hidden;
    margin:0 auto 20px;border:3px solid var(--bg);
    box-shadow:0 0 0 1px var(--line),0 10px 24px -10px rgba(16,32,40,.35)}
  .cta-shot img{width:100%;height:100%;object-fit:cover;display:block}
  .hero h1{font-size:var(--hero-size);max-width:17ch;text-wrap:balance;text-transform:var(--hero-case)}
  .hero h1.long{font-size:clamp(26px,4.6vw,40px);max-width:24ch;line-height:1.18}
  h2{text-wrap:balance}
  /* a measure set for desktop is a straitjacket on a 390px screen — it forces
     breaks the width itself would not. Let the phone use what it has. */
  .hero .lede{margin:18px 0 28px;font-size:19px;max-width:56ch}
  /* A scraped description standing in for a strapline is a paragraph, and it
     needs a paragraph's size to be read rather than skimmed past. */
  .hero .lede.long{font-size:16.5px;line-height:1.62}
  .actions{display:flex;flex-wrap:wrap;gap:12px}
  .hero-note{margin-top:20px;font-size:14px;color:var(--muted);
    padding-top:16px;border-top:var(--rule) solid color-mix(in srgb, var(--accent) 35%, transparent);
    display:inline-block}

  /* ── the trust facts, three ways ─────────────────────────────────────────
     Same real data (business.json highlights, nothing invented), presented to
     suit the trade. A grid of cells for the shops; a quiet ruled row where
     calm is the product; and a running band for the loud ones. */

  /* GRID — cell borders rather than a gap over a coloured container: an odd
     number of highlights used to leave the container colour showing as an
     empty grey box. */
  .trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:44px}
  .trust.grid{border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:var(--card)}
  .trust.grid div{background:var(--card);padding:20px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
  .trust b{display:block;font-size:26px;letter-spacing:-.02em;font-family:var(--display);
    font-weight:var(--display-weight)}
  .trust span{font-size:13px;color:var(--muted)}
  /* QUIET — no boxes at all. One hairline above, then air. */
  .trust.quiet{border-top:1px solid var(--line);margin-top:48px;
    grid-template-columns:repeat(auto-fit,minmax(136px,1fr))}
  .trust.quiet div{padding:24px 20px 4px 0}
  .trust.quiet b{font-size:29px;margin-bottom:4px}

  /* BAND — a continuous run of the same facts, edge to edge. The duplicate
     run is aria-hidden and exists only so the loop has no seam; the first run
     alone is complete, so with the animation off (reduced motion, old
     browsers, print) nothing is missing, it simply stops moving. */
  .band{overflow:hidden;background:var(--ink);color:var(--bg);
    border-top:var(--rule) solid var(--accent)}
  .band-track{display:flex;width:max-content}
  .band-run{display:flex;flex:none}
  .sig{display:flex;align-items:baseline;gap:9px;padding:15px 24px;white-space:nowrap;
    border-right:1px solid color-mix(in srgb, var(--bg) 18%, transparent)}
  .sig b{font-family:var(--display);font-weight:var(--display-weight);font-size:17px;
    letter-spacing:-.02em}
  .sig i{font-style:normal;font-size:11.5px;text-transform:uppercase;
    letter-spacing:.15em;opacity:.62}

  /* menu — grouped, priced, and selectable, the way a booking platform does it */
  .menu{margin-top:26px;display:flex;flex-direction:column;gap:26px}
  .mgroup h3{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
    color:var(--accent);margin:0 0 10px;padding-left:10px;border-left:3px solid var(--accent)}
  /* This list used to be called .rows — the same class the hours table in the
     About panel uses. The panel's display:flex + gap:9px therefore also
     applied here, prising every service row apart by 9px on top of its own
     bottom border, which is why the menu read as a stack of floating slabs
     instead of one list. Its own name now. */
  .svc-rows{background:var(--card)}
  .f-boxed .svc-rows{border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
  .f-ruled .svc-rows{border-top:var(--rule) solid var(--ink);background:transparent}
  .f-plain .svc-rows{background:transparent}
  /* a button carries a chunky default border on every side — left unreset it
     turns a clean list into a stack of boxes. */
  .row-svc{position:relative;display:flex;align-items:flex-start;gap:13px;padding:14px 16px;
    border:0;border-bottom:1px solid var(--line);border-radius:0;
    width:100%;text-align:left;background:transparent;font:inherit;color:inherit;-webkit-appearance:none;appearance:none}
  .f-boxed .row-svc{background:var(--card)}
  .f-ruled .row-svc,.f-plain .row-svc{padding:17px 4px 17px 0}
  .f-plain .row-svc{padding-top:19px;padding-bottom:19px}
  .row-svc:last-child{border-bottom:0}
  .f-ruled .row-svc:last-child,.f-plain .row-svc:last-child{border-bottom:1px solid var(--line)}
  .js .row-svc{cursor:pointer}
  .js .row-svc:hover{background:color-mix(in srgb, var(--accent) 5%, transparent)}
  /* the one deliberate micro-interaction on the list: an accent rule that
     grows out of the left edge under the pointer. It is a transform on a
     pseudo-element, so it costs nothing and disappears entirely under
     reduced motion. */
  .row-svc::before{content:"";position:absolute;left:0;top:0;bottom:0;width:2px;
    background:var(--accent);transform:scaleY(0);transform-origin:50% 100%}
  .js .row-svc:hover::before,.js .row-svc:focus-visible::before,.row-svc.on::before{transform:scaleY(1)}
  .row-svc .tick{flex:none;width:21px;height:21px;margin-top:1px;
    border-radius:clamp(0px,var(--radius),7px);
    border:1.5px solid var(--line);display:grid;place-items:center;
    font-size:11px;color:#fff;background:var(--card)}
  html:not(.js) .row-svc .tick{display:none}
  .row-svc.on{background:color-mix(in srgb, var(--accent) 8%, transparent)}
  .row-svc.on .tick{background:var(--accent);border-color:var(--accent)}
  .row-svc.on .tick::after{content:"\\2713"}
  /* these are spans, because a <button> may only hold phrasing content —
     so each one has to be told to take its own line. */
  .svc-main{flex:1;min-width:0;display:block}
  .svc-name{display:block;font-size:15.5px;font-weight:650;letter-spacing:-.01em;line-height:1.3}
  .v-barber .svc-name,.v-fitness .svc-name{font-family:var(--display);font-weight:800;
    text-transform:uppercase;letter-spacing:-.01em;font-size:15px}
  .v-beauty .svc-name,.v-care .svc-name,.v-professional .svc-name{
    font-family:var(--display);font-weight:var(--display-weight);font-size:17.5px;letter-spacing:0}
  /* FOOD — a counter list is a menu, and a menu runs the name to the price on
     a leader. Only where there is a price to run to; a leader ending in
     nothing would just be a dotted line to nowhere. */
  .v-food .row-svc:has(.svc-price) .svc-name::after{
    content:"";display:inline-block;width:100%;margin:0 0 0 8px;vertical-align:.24em;
    border-bottom:1.5px dotted color-mix(in srgb, var(--ink) 28%, transparent)}
  .v-food .row-svc:has(.svc-price) .svc-name{display:flex;align-items:baseline;white-space:nowrap;overflow:hidden}
  .v-food .svc-price{font-family:var(--display);font-weight:var(--display-weight)}
  .svc-desc{display:block;font-size:12.5px;line-height:1.45;color:var(--muted);margin-top:3px}
  .svc-meta{flex:none;display:block;text-align:right;padding-left:4px}
  .svc-price{display:block;font-size:15.5px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.3}
  .svc-price .svc-unit{font-size:12px;font-weight:600;color:var(--muted)}
  .svc-dur{display:block;font-size:12px;color:var(--muted);margin-top:3px;white-space:nowrap}

  /* the running basket — appears once something is chosen */
  .basket{position:fixed;left:0;right:0;bottom:0;z-index:70;background:var(--accent);color:#fff;
    padding:12px 16px calc(12px + env(safe-area-inset-bottom));display:none;
    box-shadow:0 -8px 24px -12px rgba(0,0,0,.4)}
  .basket.up{display:flex;align-items:center;gap:14px}
  .basket .sum{flex:1;min-width:0;font-size:13.5px;line-height:1.3}
  .basket .sum b{display:block;font-size:16px;font-variant-numeric:tabular-nums}
  .basket .btn{background:#fff;color:var(--accent);border-color:#fff;white-space:nowrap}
  .basket .clear{background:transparent;color:rgba(255,255,255,.85);border:0;font-size:13px;
    text-decoration:underline;padding:6px}

  /* team */
  .team{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:26px}
  .member{border:1px solid var(--line);border-radius:var(--radius);padding:18px;text-align:center;background:var(--card)}
  .f-plain .member,.f-ruled .member{border:0;border-top:1px solid var(--line);border-radius:0;
    padding:20px 0 0;text-align:left;background:transparent}
  .f-plain .member .av,.f-ruled .member .av{margin:0 0 12px}
  /* a one-person business is a selling point, but a lone card floating in a
     full-width box reads as an unfinished page. Lay it on its side instead. */
  .team.solo{grid-template-columns:1fr}
  .team.solo .member{display:flex;align-items:center;gap:16px;text-align:left;padding:16px 18px}
  .team.solo .member .av{margin:0}
  .member .av{width:52px;height:52px;border-radius:50%;margin:0 auto 10px;display:grid;place-items:center;
    background:color-mix(in srgb, var(--accent) 12%, var(--card));color:var(--accent);
    font-family:var(--display);font-weight:700;font-size:19px}
  .member b{display:block;letter-spacing:-.01em;font-family:var(--display);font-weight:var(--display-weight);font-size:17px}
  .member span{font-size:12.5px;color:var(--muted)}

  /* services */
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px;margin-top:30px}
  .card{border:1px solid var(--line);border-radius:var(--radius);padding:22px;background:var(--card)}
  .card h3{font-size:18px;margin-bottom:6px}
  .card p{color:var(--muted);font-size:15px;margin:0}
  .price{display:inline-block;margin-top:14px;font-weight:700;font-size:14px;color:var(--accent);background:color-mix(in srgb, var(--accent) 10%, var(--card));padding:5px 11px;border-radius:999px}

  /* about */
  .split{display:grid;grid-template-columns:1.15fr .85fr;gap:44px;align-items:start}
  .panel{background:var(--soft);border:1px solid var(--line);border-radius:var(--radius);padding:24px}
  .f-plain .panel,.f-ruled .panel{background:transparent;border:0;
    border-top:var(--rule) solid var(--ink);border-radius:0;padding:22px 0 0}
  .panel h3{font-size:15px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:14px}
  .rows{display:flex;flex-direction:column;gap:9px;font-size:15px}
  .row{display:flex;justify-content:space-between;gap:16px}
  .row span:first-child{color:var(--muted)}
  ul.ticks{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:10px}
  ul.ticks li{padding-left:28px;position:relative;color:var(--muted)}
  ul.ticks li::before{content:"\\2713";position:absolute;left:0;top:4px;width:18px;height:18px;border-radius:50%;
    background:var(--accent);color:#fff;font-size:11px;font-weight:700;line-height:18px;text-align:center}

  /* gallery — for businesses whose work IS the product */
  #work{background:var(--soft)}
  .shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:28px}
  .shots figure{margin:0;border-radius:var(--radius);overflow:hidden;background:var(--bg);
    border:1px solid var(--line);aspect-ratio:1/1}
  .shots img{width:100%;height:100%;object-fit:cover;display:block}
  .shots figure:first-child{grid-column:span 2;grid-row:span 2;aspect-ratio:1/1}
  /* Tonally consistent photography, one image left in full colour — the
     trades whose work photographs as texture and metal, not as produce.
     A bakery's pastries and a florist's stems are the product; they stay in
     colour. The lead shot keeps its colour everywhere, because on a phone
     there is no hover to reveal it with. */
  .ph-bw .shots img,.ph-bw .hero-shot img{filter:grayscale(1) contrast(1.06)}
  .ph-soft .shots img{filter:saturate(.78)}
  .ph-bw .shots figure:first-child img,.ph-bw .hero-shot img:hover,
  .ph-bw .shots figure:hover img,.ph-soft .shots figure:hover img{filter:none}
  /* A grid this small on a phone is four postage stamps. A horizontal,
     snap-scrolling row of real-sized photos reads like an actual gallery
     someone can swipe through, not a cropped thumbnail strip. */
  /* A wide picture spans; it is not going to survive a square crop. */
  .shots figure.wide{aspect-ratio:var(--ar);grid-column:1/-1;grid-row:auto}
  .shots figure.wide img{object-fit:contain}
  /* When every picture is a banner, a snap-scrolling row of them is the wrong
     shape entirely — they stack, full width, at their own proportions. */
  .shots.allwide{display:grid;grid-template-columns:1fr}
  @media (max-width:640px){
    .shots{display:flex;gap:12px;margin:28px -22px 0;padding:0 22px 4px;
      overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}
    .shots::-webkit-scrollbar{display:none}
    .shots figure{flex:0 0 80%;aspect-ratio:4/5;scroll-snap-align:start;
      grid-column:unset;grid-row:unset}
    .shots.allwide{display:grid;grid-template-columns:1fr;gap:14px;
      margin:28px 0 0;padding:0;overflow:visible}
    .shots.allwide figure{flex:none;aspect-ratio:var(--ar)}
  }

  /* reviews */
  .stars{color:#e8a33d;letter-spacing:2px}
  .quote{border:1px solid var(--line);border-radius:var(--radius);padding:24px;background:var(--card)}
  .quote p{font-size:16px}
  .quote footer{font-size:14px;color:var(--muted);font-weight:600}
  /* Where the voice hangs everything off rules, a quote is set as a quote —
     no card, a heavy rule above it and the words at reading size. */
  .f-plain .quote,.f-ruled .quote{border:0;border-top:var(--rule) solid var(--ink);
    border-radius:0;padding:22px 0 0;background:transparent}
  .f-plain .quote p,.f-ruled .quote p{font-family:var(--display);font-size:19px;line-height:1.45}

  /* contact */
  .contact{background:var(--soft)}
  .cta-box{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:32px;text-align:center}
  .f-plain .cta-box,.f-ruled .cta-box{border:0;border-radius:0;background:transparent;padding:8px 0}
  .cta-box h2{margin-bottom:8px}
  .cta-box .eyebrow{justify-content:center}
  .cta-box .actions{justify-content:center;margin-top:22px}
  .big-phone{font-family:var(--display);font-size:clamp(28px,5vw,42px);
    font-weight:var(--display-weight);letter-spacing:var(--tracking);
    text-decoration:none;display:inline-block;margin:6px 0}

  footer.site{padding:30px 0;color:var(--muted);font-size:14px;display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between}

  /* sticky mobile call bar */
  .callbar{display:none}
  @media (max-width:760px){
    nav{display:none}
    .hero{padding:44px 0 40px}
    .split{grid-template-columns:1fr;gap:28px}
    section{padding:48px 0}
    body{padding-bottom:74px}
    .callbar{
      display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;gap:10px;padding:10px 14px;
      background:color-mix(in srgb, var(--bg) 96%, transparent);backdrop-filter:blur(10px);
      border-top:1px solid var(--line);
    }
    .callbar .btn{flex:1}
    .bar .btn span.label{display:none}
  }
  /* ── hero shape per voice ─────────────────────────────────────────────────
     Type alone could not separate two sans voices without loading web fonts,
     which would break the "no external requests" promise in the pitch. So the
     hero is structurally different instead — and so is everything under it. */

  /* A hero laid over a solid dark or accent field: the copy has to invert,
     and the invert is identical whichever field it is. */
  .hero.dark .eyebrow{color:color-mix(in srgb, var(--accent) 72%, #fff)}
  .hero.dark h1{color:#fff}
  .hero.dark .lede{color:rgba(255,255,255,.86)}
  .hero.dark .hero-note{color:rgba(255,255,255,.72);border-top-color:rgba(255,255,255,.3)}
  .hero.dark .btn-primary{background:#fff;color:var(--ink);border-color:#fff}
  .hero.dark .btn-ghost{background:transparent;color:#fff;border-color:rgba(255,255,255,.5)}
  .hero.dark .trust.grid{border-color:rgba(255,255,255,.28);margin-top:38px}
  .hero.dark .trust.quiet{border-top-color:rgba(255,255,255,.3)}
  .hero.dark .trust.quiet b,.hero.dark .trust.quiet span{color:rgba(255,255,255,.9)}

  /* TRADE — a full-bleed block of colour. Reads like a work truck. */
  .v-trade .hero{background:var(--accent);padding-top:56px}
  .v-trade .hero::before{opacity:.18}
  .v-trade .hero .eyebrow{color:rgba(255,255,255,.75)}

  /* BARBER — a black shopfront, the name shouted in caps, one red line under
     it. Nothing rounded anywhere on the page. */
  .v-barber .hero{background:#101010;padding:62px 0 54px}
  .v-barber .hero::before{opacity:.28;
    background:linear-gradient(180deg,rgba(255,255,255,.06),transparent 60%)}
  .v-barber .hero h1{line-height:1.02}
  .v-barber .hero .eyebrow{color:var(--accent);letter-spacing:.24em}
  .v-barber .hero-note{border-top-width:2px;border-top-color:var(--accent)}
  .v-barber h2{text-transform:uppercase}
  .v-barber .band{border-top-color:var(--accent)}

  /* FITNESS — the same dark field, but the type is the loudest thing on it. */
  .v-fitness .hero{background:#101116;padding:66px 0 56px}
  .v-fitness .hero::before{opacity:.3}
  .v-fitness .hero h1{line-height:1.03}

  /* CARE — centred and unhurried. Calm is the product. */
  .v-care .hero{padding:88px 0 74px;text-align:center}
  .v-care .hero h1,.v-care .hero .lede{margin-left:auto;margin-right:auto}
  .v-care .hero .actions{justify-content:center}
  .v-care .hero .eyebrow{justify-content:center}
  .v-care .hero-inner{max-width:44rem;margin:0 auto}
  .v-care .hero .hero-note{margin-left:auto;margin-right:auto}
  /* centred text needs symmetric cells, or every figure sits a few pixels
     left of where the eye expects it */
  .v-care .trust.quiet div{padding:24px 14px 6px}

  /* BEAUTY — editorial: a rule down the side, deep top margin, nothing rushed. */
  .v-beauty .hero{padding:96px 0 72px}
  .v-beauty .hero-inner{border-left:2px solid var(--accent);padding-left:28px}
  .v-beauty .hero h1{max-width:14ch}
  .v-beauty .eyebrow{padding-bottom:14px;border-bottom:1px solid var(--line);
    display:inline-flex;width:auto}

  /* PROFESSIONAL — set like a document: flush left, ruled, no ornament. */
  .v-professional .hero{padding:70px 0 58px}
  .v-professional .hero::before{background:linear-gradient(180deg,var(--soft),var(--bg))}
  .v-professional .hero-inner{border-top:3px solid var(--ink);padding-top:26px}
  .v-professional section{border-top-color:var(--line)}

  /* FOOD / RETAIL — the copy sits on a card, like something on a counter. */
  .v-food .hero,.v-retail .hero{padding:40px 0 52px}
  .v-food .hero-inner,.v-retail .hero-inner{
    background:color-mix(in srgb, var(--accent) 7%, var(--card));
    border:1px solid color-mix(in srgb, var(--accent) 18%, var(--line));
    border-radius:calc(var(--radius) + 4px);padding:36px 32px}
  .v-food .trust,.v-retail .trust{margin-top:20px}

  /* Measures tuned for a desktop column are a straitjacket on a 390px screen:
     they force line breaks the width itself would never make. This has to sit
     after the per-voice rules — it matches their specificity, so order decides. */
  @media (max-width:640px){
    .hero h1,.v-trade .hero h1,.v-care .hero h1,.v-beauty .hero h1,
    .v-food .hero h1,.v-barber .hero h1{max-width:none}
  }

  @media (max-width:760px){
    .v-food .hero-inner,.v-retail .hero-inner{padding:26px 20px}
    .v-beauty .hero-inner{padding-left:18px}
    .v-care .hero{padding:54px 0 46px}
    .v-beauty .hero{padding:58px 0 46px}
    .v-professional .hero{padding:46px 0 40px}
    .sig{padding:13px 18px}
    .trust.quiet div{padding:20px 16px 4px 0}
  }

  /* ── motion ──────────────────────────────────────────────────────────────
     A short load sequence in the hero, then sections arrive as you reach them.
     Everything below is opt-out: with reduced motion the page renders finished. */
  @media (prefers-reduced-motion:no-preference){
    /* Scoped to .js — set by an inline script before paint. With scripting off
       or blocked (some mail clients preview attachments that way) nothing is
       ever hidden, and the page simply renders finished. */
    .js .rise{opacity:0;transform:translateY(14px)}
    .js .in .rise,.js .rise.in{opacity:1;transform:none;
      transition:opacity .62s var(--ease),transform .62s var(--ease)}
    .js .hero .rise{transition-delay:calc(var(--i,0) * 90ms)}
    /* A photo arriving reads better as a soft settle than a slide — closer
       to how an actual gallery feels loading in, not text sliding up. */
    .js .photo-in{opacity:0;transform:scale(1.045)}
    .js .in .photo-in,.js .photo-in.in{opacity:1;transform:none;
      transition:opacity .8s var(--ease),transform 1s var(--ease)}
    .card{transition:transform .28s var(--ease),border-color .28s var(--ease),box-shadow .28s var(--ease)}
    .card:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 45%,var(--line));
      box-shadow:0 10px 24px -14px rgba(16,32,40,.35)}
    .shots img,.hero-shot img{transition:transform .5s var(--ease),filter .5s var(--ease)}
    .shots figure:hover img,.hero-shot:hover img{transform:scale(1.06)}
    .row-svc,.row-svc::before{transition:background .2s var(--ease),transform .22s var(--ease)}
    .btn{transition:transform .18s var(--ease),filter .18s var(--ease),
      background .2s var(--ease),color .2s var(--ease),border-color .2s var(--ease)}
    .btn:active{transform:scale(.97)}
    .trust div{transition:background .3s var(--ease)}
    .trust.grid div:hover{background:color-mix(in srgb,var(--accent) 5%,var(--card))}
    /* The band runs. The second copy of the facts exists only so the loop has
       no seam — it is aria-hidden, and translating exactly -50% lands run two
       where run one started. Pauses under the pointer so a fact can be read. */
    .band-track{animation:bandroll ${Math.max(18, highlights.length * 7)}s linear infinite}
    .band:hover .band-track,.band:focus-within .band-track{animation-play-state:paused}
    .js .callbar{transform:translateY(110%);transition:transform .38s var(--ease)}
    .js .callbar.up{transform:none}
    .tel-pulse{position:relative}
  }
  @keyframes bandroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
  @media (prefers-reduced-motion:reduce){
    .rise,.js .rise,.photo-in,.js .photo-in{opacity:1;transform:none}
    .callbar,.js .callbar{transform:none}
    /* The band stops. It does not disappear: run one is the complete set of
       facts and it is what stays on screen. Motion is a preference; the
       content behind it is not negotiable. */
    .band-track{animation:none}
  }

  @media print{header,.callbar{position:static}.rise{opacity:1;transform:none}
    .band-track{animation:none}}
</style>
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="#top">${
      b.mark ? `<img class="mark-img" src="${esc(b.mark)}" alt="">`
      : b.logo ? ''
      : `<span class="mark">${esc((b.name || '?').trim()[0].toUpperCase())}</span>`
    }<span class="nm">${esc(b.shortName || b.name)}</span></a>
    <nav>${nav.map(([t, h]) => `<a href="${h}">${esc(t)}</a>`).join('')}</nav>
    ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call <span class="label">${esc(b.phone)}</span></a>` : ''}
  </div>
</header>

<main id="top">

<div class="hero${v.hero === 'dark' || v.hero === 'accent' ? ' dark' : ''}">
  <div class="wrap">
    <div class="hero-grid${photos.length ? ' has-photo' : ''}">
    <div class="hero-inner">
    ${b.logo ? `<img class="logo rise" style="--i:0" src="${esc(b.logo)}" alt="${esc(b.name)}" width="${esc(b.logoWidth || 300)}">` : ''}
    ${b.category ? `<div class="eyebrow rise" style="--i:0">${esc(b.category)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</div>` : ''}
    <h1 class="rise${headLong ? ' long' : ''}" style="--i:1">${esc(headline)}</h1>
    ${subhead ? `<p class="lede rise${headTooLong ? ' long' : ''}" style="--i:2">${esc(subhead)}</p>` : ''}
    <div class="actions rise" style="--i:3">
      ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">${esc(b.cta?.primary || 'Call ' + b.phone)}</a>` : ''}
      ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Get directions</a>` : ''}
    </div>
    ${b.heroNote ? `<div class="hero-note rise" style="--i:4">${esc(b.heroNote)}</div>` : ''}
    </div>
    ${photos.length ? `<div class="hero-shot photo-in${photos[0].wide ? ' wide' : ''}" style="--i:2;--ar:${photos[0].ar || 1}"><img src="${esc(photos[0].src)}" alt="${esc(photos[0].alt || b.name)}" loading="eager"></div>` : ''}
    </div>
    ${signalBlock}
  </div>
</div>
${signalBand}

${services.length ? `
<section id="services">
  <div class="wrap">
    ${eyebrow('Services')}
    <h2>${esc(b.servicesHeading || 'What we do')}</h2>
    ${b.servicesLede ? `<p class="lede">${esc(b.servicesLede)}</p>` : ''}
    ${''/* Every service list is a menu people choose from, not a row of cards.
           Prices and durations show when the business has given them; when it
           has not, the choosing and the request still work. We never invent a
           number to fill the column. */}
    ${`<div class="menu">${groups.map(([name, items]) => `
        <div class="mgroup">
          ${name ? `<h3>${esc(name)}</h3>` : ''}
          <div class="svc-rows">
            ${items.map((s) => `<button type="button" class="row-svc" data-price="${esc(cents(s.price))}" data-mins="${esc(mins(s.duration))}" data-unit="${esc(s.unit || '')}" data-name="${esc(s.name)}">
              <span class="tick" aria-hidden="true"></span>
              <span class="svc-main">
                <span class="svc-name">${esc(s.name)}</span>
                ${s.desc ? `<span class="svc-desc">${esc(s.desc)}</span>` : ''}
              </span>
              <span class="svc-meta">
                ${s.price ? `<span class="svc-price">${esc(s.price)}${s.unit ? `<span class="svc-unit">${esc(s.unit)}</span>` : ''}</span>` : ''}
                ${s.duration ? `<span class="svc-dur">${esc(s.duration)}</span>` : ''}
              </span>
            </button>`).join('')}
          </div>
        </div>`).join('')}</div>`}
  </div>
</section>` : ''}

${team.length ? `
<section id="team">
  <div class="wrap">
    ${eyebrow('Our team')}
    <h2>${esc(b.teamHeading || 'Who you will see')}</h2>
    ${b.teamLede ? `<p class="lede">${esc(b.teamLede)}</p>` : ''}
    <div class="team${team.length === 1 ? ' solo' : ''}">
      ${team.map((m) => `<div class="member">
        <div class="av">${esc((m.name || '?').trim()[0].toUpperCase())}</div>
        <b>${esc(m.name)}</b>
        ${m.role ? `<span>${esc(m.role)}</span>` : ''}
      </div>`).join('')}
    </div>
  </div>
</section>` : ''}

${(() => {
  // photos[0] already leads the hero — repeating it here would read as
  // padding, not more evidence. Only worth a section when there's more.
  const rest = photos.slice(1);
  return rest.length ? `
<section id="work">
  <div class="wrap">
    ${eyebrow(b.galleryEyebrow || 'Our work')}
    <h2>${esc(b.galleryHeading || 'Recent work')}</h2>
    ${b.galleryLede ? `<p class="lede">${esc(b.galleryLede)}</p>` : ''}
    <div class="shots${rest.every((p) => p.wide) ? ' allwide' : ''}">
      ${rest.map((p, i) => `<figure${p.wide ? ' class="wide"' : ''} style="--ar:${p.ar || 1}"><img src="${esc(p.src)}" alt="${esc(p.alt || b.name + ' — photo ' + (i + 2))}" loading="lazy"></figure>`).join('')}
    </div>
  </div>
</section>` : '';
})()}

${b.about ? `
<section id="about">
  <div class="wrap split">
    <div>
      ${eyebrow('About')}
      <h2>${esc(b.aboutHeading || 'About ' + b.name)}</h2>
      ${String(b.about).split('\n\n').map((p) => `<p class="lede">${esc(p)}</p>`).join('')}
      ${b.points?.length ? `<ul class="ticks">${b.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>` : ''}
    </div>
    <div class="panel">
      ${hours.length ? `<h3>Hours</h3><div class="rows">${hours.map((h) =>
        `<div class="row"><span>${esc(h.days)}</span><span>${esc(h.time)}</span></div>`).join('')}</div>` : ''}
      ${b.serviceArea?.length ? `<h3 style="margin-top:22px">Service area</h3><p style="color:var(--muted);font-size:15px;margin:0">${esc(b.serviceArea.join(' · '))}</p>` : ''}
      ${a.street ? `<h3 style="margin-top:22px">Find us</h3>
        <p style="font-size:15px;margin:0 0 12px">${esc(addressLine(a))}</p>
        <a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Open in Maps</a>` : ''}
    </div>
  </div>
</section>` : ''}

${reviews.length ? `
<section id="reviews">
  <div class="wrap">
    ${eyebrow('Reviews')}
    <h2>${esc(b.reviewsHeading || 'What customers say')}</h2>
    ${b.rating ? `<p class="lede">${stars(b.rating.value)} ${esc(b.rating.value)} from ${esc(b.rating.count)} reviews${b.rating.source ? ' on ' + esc(b.rating.source) : ''}.</p>` : ''}
    <div class="grid">
      ${reviews.map((r) => `<blockquote class="quote">
        ${r.stars ? stars(r.stars) : stars(5)}
        <p>“${esc(r.text)}”</p>
        <footer>— ${esc(r.author)}${r.source ? ', ' + esc(r.source) : ''}</footer>
      </blockquote>`).join('')}
    </div>
  </div>
</section>` : ''}

<section id="contact" class="contact">
  <div class="wrap">
    <div class="cta-box">
      ${photos[1] && !photos[1].wide ? `<div class="cta-shot"><img src="${esc(photos[1].src)}" alt="" loading="lazy"></div>` : ''}
      ${eyebrow('Contact')}
      <h2>${esc(b.ctaHeading || 'Ready when you are')}</h2>
      <p class="lede" style="margin:0 auto">${esc(b.ctaLede || 'Call and talk to a real person.')}</p>
      ${b.phone ? `<a class="big-phone" href="tel:${esc(tel)}" style="color:var(--accent)">${esc(b.phone)}</a>` : ''}
      <div class="actions">
        ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call now</a>` : ''}
        ${b.email ? `<a class="btn btn-ghost" href="mailto:${esc(b.email)}">Email us</a>` : ''}
        ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Directions</a>` : ''}
      </div>
    </div>
  </div>
</section>

</main>

<footer class="site">
  <div class="wrap" style="display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;width:100%">
    <span>© ${new Date().getFullYear()} ${esc(b.name)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</span>
    <span>${esc(b.phone || '')}${b.license ? ' · ' + esc(b.license) : ''}</span>
  </div>
</footer>

${services.length ? `<div class="basket" id="basket" hidden>
  <div class="sum"><b id="bkTotal"></b><span id="bkMeta"></span></div>
  <button type="button" class="clear" id="bkClear">Clear</button>
  <a class="btn" id="bkGo" href="#">Request</a>
</div>` : ''}

${b.phone ? `<div class="callbar">
  <a class="btn btn-primary" href="tel:${esc(tel)}">Call ${esc(b.phone)}</a>
  ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Map</a>` : ''}
</div>` : ''}

<script>
(function(){
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero');

  // Motion is a preference. Booking is a function. Reducing one must never
  // remove the other — an early return here once disabled the whole menu.
  if (reduce) {
    document.querySelectorAll('.rise, .photo-in').forEach(function(el){ el.classList.add('in'); });
  } else {
    requestAnimationFrame(function(){ hero && hero.classList.add('in'); });

    var targets = document.querySelectorAll('section .eyebrow, section h2, section .lede, .card, .quote, .panel, .cta-box, ul.ticks li');
    targets.forEach(function(el){ el.classList.add('rise'); });
    // Photos settle rather than slide — .shots figure and .cta-shot get the
    // scale-fade defined for .photo-in instead of the text .rise.
    var photoTargets = document.querySelectorAll('.shots figure, .cta-shot');
    photoTargets.forEach(function(el){ el.classList.add('photo-in'); });
    var allTargets = [].concat([].slice.call(targets), [].slice.call(photoTargets));
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (!e.isIntersecting) return;
          e.target.classList.add('in');
          io.unobserve(e.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
      allTargets.forEach(function(el){ io.observe(el); });
    } else {
      allTargets.forEach(function(el){ el.classList.add('in'); });
    }
  }

  // Choose services, see the running total, then send the request as a text or
  // an email. No backend, no booking account — it composes the message and the
  // customer sends it from their own phone.
  var basket = document.getElementById('basket');
  if (basket) {
    var picked = [];
    var TEL = ${JSON.stringify(digits(b.phone || ''))};
    var MAIL = ${JSON.stringify(b.email || '')};
    var BOOKURL = ${JSON.stringify(b.booking?.url || '')};
    var BIZ = ${JSON.stringify(b.name || '')};
    // A quote trade is not a booking trade. Nobody books a re-roof; they ask
    // someone to come and look at it.
    var QUOTES = ${JSON.stringify(!services.some((s) => s.price))};
    // Some trades travel to the customer; for everyone else the customer
    // travels to them. "When could you come out?" to a dentist is nonsense.
    var VISITS = ${JSON.stringify(/plumb|roof|electric|hvac|contractor|construct|carpenter|painter|glaz|floor|tiler|locksmith|garden|landscap|pool|spa service|hot tub|clean|pest|gutter|window|upholster|mov|haul/i.test(b.category || ''))};

    var money = function(c){ return '$' + (c/100).toFixed(2).replace(/\.00$/,''); };
    // People book in hours and minutes, not decimals. "3.3 hr" is not a time.
    var time = function(m){
      if (m < 60) return m + ' min';
      var h = Math.floor(m / 60), r = m % 60;
      return h + ' hr' + (r ? ' ' + r + ' min' : '');
    };

    var paint = function(){
      if (!picked.length) {
        basket.hidden = true; basket.classList.remove('up');
        document.body.style.paddingBottom = '';
        return;
      }
      // A $145/mo plan and a $395 one-off job cannot be added into one number.
      // Sum each unit separately: "$395 + $145/mo", never a meaningless $540.
      var sums = {}, order = [];
      picked.forEach(function(p){
        var u = p.unit || '';
        if (!(u in sums)) { sums[u] = 0; if (u) order.push(u); }
        sums[u] += p.price;
      });
      var parts = [];
      if (sums['']) parts.push(money(sums['']));
      order.forEach(function(u){ if (sums[u]) parts.push(money(sums[u]) + u); });
      var priced = parts.join(' + ');

      // Time on site only means something for a one-off visit; a monthly plan
      // is not "about 90 minutes".
      var dur = picked.reduce(function(n,p){ return n + (p.unit ? 0 : p.mins); }, 0);

      basket.hidden = false; basket.classList.add('up');
      document.getElementById('bkTotal').textContent =
        picked.length + (picked.length === 1 ? ' service' : ' services') + (priced ? ' · ' + priced : '');
      document.getElementById('bkMeta').textContent = dur ? 'about ' + time(dur) : '';

      var lines = picked.map(function(p){
        return '• ' + p.name + (p.price ? ' (' + money(p.price) + (p.unit || '') + ')' : '');
      }).join('\\n');
      var msg = 'Hi ' + BIZ + ', ' +
                (!QUOTES ? 'I would like to book:'
                 : VISITS ? 'could I get an estimate for:'
                 : 'could I book in for:') + '\\n' + lines +
                (priced ? '\\n\\nTotal: ' + priced : '') +
                (dur ? '\\nAbout ' + time(dur) + ' on site' : '') +
                '\\n\\n' + (!QUOTES ? 'What times do you have?'
                                : VISITS ? 'When could you come out?'
                                : 'When could you fit me in?');
      var go = document.getElementById('bkGo');
      if (BOOKURL) { go.href = BOOKURL; go.textContent = 'Book online'; }
      else if (QUOTES && TEL) { go.href = 'sms:' + TEL + '?&body=' + encodeURIComponent(msg);
                                go.textContent = VISITS ? 'Get a quote' : 'Request appointment'; }
      else if (TEL) { go.href = 'sms:' + TEL + '?&body=' + encodeURIComponent(msg); go.textContent = 'Text this'; }
      else if (MAIL) { go.href = 'mailto:' + MAIL + '?subject=' + encodeURIComponent('Booking request') +
                        '&body=' + encodeURIComponent(msg); go.textContent = 'Email this'; }
      else { go.href = '#'; go.textContent = 'Call us'; }
    };

    document.querySelectorAll('.row-svc').forEach(function(el){
      el.addEventListener('click', function(){
        var name = el.dataset.name;
        var i = picked.findIndex(function(p){ return p.name === name; });
        if (i > -1) { picked.splice(i,1); el.classList.remove('on'); }
        else { picked.push({ name: name, price: +el.dataset.price || 0, mins: +el.dataset.mins || 0,
                             unit: el.dataset.unit || '' });
               el.classList.add('on'); }
        paint();
      });
    });
    document.getElementById('bkClear').addEventListener('click', function(){
      picked = [];
      document.querySelectorAll('.row-svc.on').forEach(function(el){ el.classList.remove('on'); });
      paint();
    });
  }

  // The call bar stays out of the way until you have actually started reading.
  var bar = document.querySelector('.callbar');
  if (bar) {
    var show = function(){
      var busy = basket && !basket.hidden;
      bar.classList.toggle('up', (reduce || scrollY > 220) && !busy);
    };
    if (basket) new MutationObserver(show).observe(basket, { attributes: true });
    addEventListener('scroll', show, { passive: true }); show();
  }
})();
</script>
</body>
</html>
`;
};

// A single stray backslash in the emitted <script> once shipped a page whose
// entire booking system was dead on arrival — and nothing said a word, because
// broken JavaScript in a browser just quietly does nothing. No page leaves this
// file again without its script being parsed first.
module.exports = function renderChecked(b) {
  const html = render(b);
  for (const [, attrs, js] of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    if (/^\s*$/.test(js)) continue;
    const type = (attrs.match(/type\s*=\s*["']([^"']+)/i) || [])[1];
    if (type && !/javascript|module/i.test(type)) continue;   // JSON-LD is not code
    try { new Function(js); } catch (e) {
      throw new Error(`${b.slug || b.name || 'page'}: emitted page script will not parse — ${e.message}`);
    }
  }
  return html;
};
module.exports.unchecked = render;
