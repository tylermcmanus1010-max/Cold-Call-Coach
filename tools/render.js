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

function jsonld(b) {
  const a = b.address || {};
  const data = {
    '@context': 'https://schema.org',
    '@type': b.schemaType || 'LocalBusiness',
    name: b.name,
    description: b.description || b.tagline,
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

// The grain on every ground. An SVG feTurbulence noise, inlined as a data:
// URI so it costs no request — the pitch promises the page opens on a plane.
// Grey with a low alpha, so one tile works on paper (dark specks) and on ink
// (light specks). One tile of 220px; the browser rasterises it once and
// repeats it. Keep the alpha ceiling low: this is meant to be felt, not seen.
const GRAIN = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .16"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#g)"/></svg>`
);

// A barbershop should not read like an endodontist. Each trade gets its own
// voice — typeface class, weight, button radius, letter-spacing, hero
// treatment, AND a default palette — built from system fonts so the page
// still makes no network request and still opens instantly from an email
// attachment. The ground texture is not a voice choice: every page gets the
// same grain and grid (see GRAIN), because a flat fill is a flat fill in any
// colour. The palette is a *default*, not a limit: a human (or a color
// pulled from the business's own logo/sign) still overrides it via
// business.json's theme.accent/theme.ink. It exists so a page built with
// nobody in the loop — the autonomous outreach path — still looks like it
// was made for this business, not stamped from one template in one color.
const VOICES = {
  trade: {   // plumbers, roofers, auto, smog, contractors, electricians
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 800, tracking: '-.035em', radius: '4px', caseLabel: 'uppercase',
    labelTrack: '.14em', heroSize: 'clamp(32px,10.5vw,62px)', rule: '3px',
    accent: '#d3491d', ink: '#191512',
  },
  care: {    // dentists, doctors, clinics, vets, chiro
    display: '"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif',
    weight: 600, tracking: '-.015em', radius: '999px', caseLabel: 'uppercase',
    labelTrack: '.12em', heroSize: 'clamp(30px,9.4vw,56px)', rule: '1px',
    accent: '#1d6f6a', ink: '#141c1e',
  },
  beauty: {  // salons, nails, spa, florists, lashes
    display: '"Iowan Old Style",Palatino,Georgia,serif',
    weight: 500, tracking: '.005em', radius: '0', caseLabel: 'uppercase',
    labelTrack: '.18em', heroSize: 'clamp(30px,9.4vw,58px)', rule: '1px',
    accent: '#a9436b', ink: '#1c1417',
  },
  food: {    // bakeries, cafés, restaurants, delis
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 750, tracking: '-.03em', radius: '12px', caseLabel: 'uppercase',
    labelTrack: '.1em', heroSize: 'clamp(31px,10vw,60px)', rule: '2px',
    accent: '#c07a1e', ink: '#201a12',
  },
  fitness: { // gyms, climbing, martial arts, training
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 850, tracking: '-.04em', radius: '2px', caseLabel: 'uppercase',
    labelTrack: '.14em', heroSize: 'clamp(33px,10.8vw,68px)', rule: '4px',
    accent: '#2a2f8f', ink: '#111217',
  },
  professional: { // law, insurance, finance, real estate, accounting
    display: 'Georgia,"Times New Roman",Times,serif',
    weight: 700, tracking: '-.01em', radius: '2px', caseLabel: 'uppercase',
    labelTrack: '.12em', heroSize: 'clamp(28px,8.8vw,52px)', rule: '1px',
    accent: '#1c3a5e', ink: '#14181d',
  },
  retail: {  // shops, boutiques, apparel, hardware, furniture
    display: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif',
    weight: 700, tracking: '-.02em', radius: '8px', caseLabel: 'uppercase',
    labelTrack: '.12em', heroSize: 'clamp(31px,10vw,60px)', rule: '2px',
    accent: '#2f6b3a', ink: '#151a15',
  },
};

function voiceOf(b) {
  if (b.voice && VOICES[b.voice]) return b.voice;
  const c = (b.category || '').toLowerCase();
  if (/dent|endodont|medical|doctor|clinic|health|vet|chiro|ortho/.test(c)) return 'care';
  if (/salon|nail|spa|beauty|hair|barber|massage|florist|flower|lash/.test(c)) return 'beauty';
  if (/baker|café|cafe|coffee|restaurant|deli|food|catering/.test(c)) return 'food';
  if (/climb|fitness|gym|martial|yoga|pilates|training(?! systems)/.test(c)) return 'fitness';
  if (/law|attorney|legal|insurance|finance|accounting|realt|real estate|title company/.test(c)) return 'professional';
  if (/shop|store|apparel|boutique|hardware|furniture|nursery|garden center/.test(c)) return 'retail';
  if (/plumb|roof|auto|repair|smog|tyre|tire|electric|hvac|contractor|construct|landscap|clean/.test(c)) return 'trade';
  return 'trade';
}

function render(b) {
  const tel = digits(b.phone);
  const a = b.address || {};
  const v = VOICES[voiceOf(b)];
  // A human-chosen color (from business.json) always wins. Absent one — the
  // autonomous outreach path, where nobody sat down and picked a hex from a
  // logo — the voice's own default palette stands in, so the page still
  // reads as fitted to the trade rather than every unbranded lead landing on
  // the same green.
  const accent = b.theme?.accent || v.accent;

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
  const photos = (b.photos || []).filter((p) => (typeof p === 'string' ? p : p?.src));
  // What a photo is OF decides where it may go (tools/photo-kind.js). Only
  // `work` — a finished cut, a cake, a client in the chair — may sit under
  // "Recent work"; that heading is a claim about the picture beneath it, and
  // Portal Salon shipped with the sink wall there. Untagged means nobody has
  // looked yet, so it is treated as not-work. The hero and the print beside
  // the ask both prefer work; a real photo of their place is honest anywhere
  // the page makes no claim about it, so both fall back to whatever leads.
  //
  // `other` is kept on file and never shown. It is what a stock photo off
  // their site becomes once someone has looked: a piggyback in a field, a
  // toothbrush on a leaf, Pinterest nails. Under "Around Palm Dental" it
  // implies their premises; leading the hero it is fake evidence. Nothing
  // real, nothing shown — the page adapts, as it does for a missing section.
  const kindOf = (p) => (p && typeof p === 'object' && p.kind) || '';
  const isWork = (p) => kindOf(p) === 'work';
  const shown = photos.filter((p) => kindOf(p) !== 'other');
  const heroPhoto = shown.find(isWork) || shown[0];
  const otherPhotos = shown.filter((p) => p !== heroPhoto);
  const workShots = otherPhotos.filter(isWork);
  const placeShots = otherPhotos.filter((p) => !isWork(p));
  const askPhoto = otherPhotos.find(isWork) || otherPhotos[0];
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

  // Display size follows the words, not just the voice. Three words get the
  // width of the column; a full sentence gets a size it can hold at 320px
  // without breaking a word. Sized off the longest word, because that is the
  // thing that overflows — never the sentence. The floor in each voice's
  // heroSize is deliberately low so the vw term rules on a phone: if the
  // longest word fits at 390 it fits at 320 too.
  const hl = String(b.headline || b.tagline || '').trim();
  const longest = Math.max(0, ...hl.split(/\s+/).map((w) => w.length));
  const heroScale = longest <= 9 && hl.length <= 30 ? 1.5
                  : longest <= 11 && hl.length <= 50 ? 1.25
                  : longest <= 14 ? 1 : 0.85;

  // Sections count — "01 / Services", "02 / About" — in the order they land
  // on the page, skipping any that are not rendered.
  let n = 0;
  const num = () => String(++n).padStart(2, '0');

  // A caption under a print is decoration, so it may only say what the page
  // already knows: a caption someone wrote for that photo, the city, the
  // name. Never a description of the work — that would be a claim about a
  // job we know nothing about. The auto alt from ./cc photo ("Name — photo
  // 2") is not a caption, so it falls through to the place.
  const place = [a.city, a.state].filter(Boolean).join(', ');
  const caption = (p, i) => {
    if (p && typeof p === 'object' && String(p.caption || '').trim()) return p.caption;
    const alt = p && typeof p === 'object' ? String(p.alt || '') : '';
    const auto = !alt || /— photo \d+$/.test(alt) || alt === b.name;
    if (!auto) return alt;
    return i % 2 === 0 ? (place || b.shortName || b.name) : (b.shortName || b.name);
  };

  const nav = [
    services.length && ['Services', '#services'],
    workShots.length ? ['Work', '#work'] : placeShots.length && ['Photos', '#place'],
    team.length && ['Team', '#team'],
    b.about && ['About', '#about'],
    reviews.length && ['Reviews', '#reviews'],
    ['Contact', '#contact'],
  ].filter(Boolean);

  return `<!doctype html>
<html lang="en" class="v-${voiceOf(b)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(b.name)}${b.category ? ' — ' + esc(b.category) : ''}${a.city ? ' in ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</title>
<meta name="description" content="${esc(b.description || b.tagline)}${b.phone ? ' Call ' + esc(b.phone) + '.' : ''}">
<meta property="og:type" content="website">${b.liveUrl ? `
<link rel="canonical" href="${esc(b.liveUrl)}">
<meta property="og:url" content="${esc(b.liveUrl)}">` : ''}
<meta property="og:title" content="${esc(b.name)}">
<meta property="og:description" content="${esc(b.description || b.tagline)}">
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
    --paper:#f4f0e7;
    --paper-2:#ebe6da;
    --card:#fbf9f4;
    --muted:color-mix(in srgb, var(--ink) 64%, var(--paper));
    --line:color-mix(in srgb, var(--ink) 16%, var(--paper));
    --grid-line:rgba(30,24,16,.042);
    --grain:url("${GRAIN}");
    --radius:${v.radius};
    --wrap:1080px;
    --display:${v.display};
    --display-weight:${v.weight};
    --tracking:${v.tracking};
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --label-track:${v.labelTrack};
    --hero-size:${v.heroSize};
    --hero-scale:${heroScale};
    --rule:${v.rule};
    --ease:cubic-bezier(.2,.7,.2,1);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    margin:0;color:var(--ink);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}
  a{color:inherit}

  /* ── grounds ────────────────────────────────────────────────────────────
     Nothing on the page is a flat hex fill. Every ground carries the same two
     layers: a grain — an inline SVG feTurbulence noise as a data: URI, so the
     page still makes no request — and a faint grid under it. The grain is
     grey at a low alpha, so one tile reads as dark specks on paper and light
     specks on ink. It is meant to be felt, not seen: if the noise itself is
     visible from arm's length it is too strong. */
  body,#work,.contact,footer.site{
    background-image:var(--grain),
      linear-gradient(var(--grid-line) 1px,transparent 1px),
      linear-gradient(90deg,var(--grid-line) 1px,transparent 1px);
    background-size:220px 220px,36px 36px,36px 36px}
  body{background-color:var(--paper)}
  #work{background-color:var(--paper-2)}
  /* ink: the second ground. Text, hairlines and the grid all go light here. */
  .contact,footer.site{background-color:var(--ink);color:var(--paper);
    --grid-line:rgba(255,255,255,.04);--line:rgba(255,255,255,.16);--muted:rgba(255,255,255,.6)}

  /* ── type: three scales, far apart ──────────────────────────────────────
     Labels are tiny mono, uppercase, tracked. Display type takes as much of
     the column as the words allow. The distance between the two is the
     design; an 11.5px sans eyebrow over a 34px heading is what a template
     looks like. */
  h1,h2,h3{line-height:1.02;margin:0;font-family:var(--display);
    font-weight:var(--display-weight);letter-spacing:var(--tracking);text-wrap:balance;
    overflow-wrap:break-word}
  h2{font-size:clamp(34px,10vw,64px);margin-bottom:18px}
  p{margin:0 0 14px}
  /* the header is sticky, so an anchored jump must leave room for it or the
     first line of the section lands underneath. */
  section{padding:clamp(56px,11vw,96px) 0;border-top:1px solid var(--line);scroll-margin-top:72px}
  .eyebrow{font-family:var(--mono);font-size:10.5px;font-weight:600;line-height:1.5;
    letter-spacing:var(--label-track);text-transform:uppercase;color:var(--accent)}
  /* section labels count: the number on the left, the label on the right,
     one baseline. */
  .sec{display:flex;justify-content:space-between;gap:16px;margin-bottom:26px;color:var(--muted)}
  .sec .n{color:var(--accent)}
  .lede{color:var(--muted);max-width:60ch;font-size:17px}

  /* the category is a sticker: solid fill, hard offset shadow, a degree off
     square. Stuck on, not typeset. The rotation lives on the span and the
     reveal on the wrapper, because a reveal transform would replace it. */
  .tag{display:inline-block;max-width:100%;background:var(--accent);color:var(--paper);
    padding:7px 10px 6px;box-shadow:3px 3px 0 var(--ink);transform:rotate(-1.4deg);
    transform-origin:left center;text-wrap:balance}
  .tagwrap{margin-bottom:28px}

  /* a supplied logo leads the hero. Stacked wordmarks (name inside the art)
     are unreadable in a 64px header bar, so they belong here at full size. */
  .hero .logo{display:block;max-width:min(100%,var(--logo-w,300px));height:auto;
    margin:0 0 24px;mix-blend-mode:multiply}
  /* multiply needs something light behind it; on a full-bleed accent hero the
     logo keeps its own white card — squared off and given a hard shadow, so it
     reads as a label stuck on the truck rather than a floating panel. */
  .v-trade .hero .logo{mix-blend-mode:normal;background:#fff;padding:10px;box-shadow:6px 6px 0 var(--ink)}
  .v-care .hero .logo,.v-food .hero .logo{margin-left:auto;margin-right:auto}

  /* header */
  header{position:sticky;top:0;z-index:50;background:color-mix(in srgb, var(--paper) 88%, transparent);
    backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  .bar{display:flex;align-items:center;gap:18px;height:64px}
  .brand{font-family:var(--display);font-weight:var(--display-weight);letter-spacing:var(--tracking);
    font-size:18px;text-decoration:none;margin-right:auto;display:flex;align-items:center;gap:10px;
    min-width:0}
  /* the bar is a fixed height, so a long name has to shrink rather than wrap */
  .brand .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  @media (max-width:520px){ .brand{font-size:16px} }
  @media (max-width:400px){ .brand{font-size:15px} }
  .mark{width:30px;height:30px;background:var(--accent);color:var(--paper);display:grid;place-items:center;
    font-family:var(--display);font-weight:var(--display-weight);font-size:15px;flex:none}
  /* a stacked logo is unreadable in a 64px bar, so the header takes a compact
     mark and sets the name in type beside it. */
  .mark-img{width:30px;height:30px;object-fit:contain;flex:none;display:block}
  nav{display:flex;gap:22px}
  nav a{color:var(--muted);text-decoration:none;font:600 11px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase}
  nav a:hover{color:var(--ink)}
  /* Corners live on buttons and on photos inside their frames, nowhere else.
     The radius is the voice's own: a pill for care, near-square for trade. */
  .btn{
    display:inline-flex;align-items:center;justify-content:center;gap:8px;
    padding:13px 20px;border-radius:var(--radius);font-weight:650;font-size:15px;
    text-decoration:none;border:1px solid transparent;white-space:nowrap;
  }
  .btn-primary{background:var(--accent);color:var(--accent-ink)}
  .btn-primary:hover{filter:brightness(.92)}
  .btn-ghost{border-color:color-mix(in srgb, var(--ink) 32%, transparent);background:transparent;color:var(--ink)}
  .btn-ghost:hover{border-color:var(--ink)}

  /* hero */
  .hero{padding:clamp(52px,9vw,88px) 0 clamp(48px,8vw,76px);position:relative;overflow:hidden}
  .hero::before{
    content:"";position:absolute;inset:0;z-index:-1;
    background-image:var(--grain),
      linear-gradient(var(--grid-line) 1px,transparent 1px),
      linear-gradient(90deg,var(--grid-line) 1px,transparent 1px),
      radial-gradient(760px 420px at 78% -8%, color-mix(in srgb, var(--accent) 9%, transparent), transparent 70%);
    background-size:220px 220px,36px 36px,36px 36px,auto;
  }
  ${hero ? `.hero::after{content:"";position:absolute;inset:0;z-index:-2;background:url("${esc(hero)}") center/cover;opacity:.14}` : ''}

  /* A real photo of the actual business, not a texture — this is the
     difference between a page that looks like a template and one that
     looks like theirs. It is treated as an object: a print with a solid
     offset shadow, not a rounded thumbnail with a hairline. Stacked by
     default (the photo reads as evidence right under the pitch); beside the
     headline on wide screens for the voices where a strong image belongs
     next to the words, not under them. */
  .hero-shot{margin-top:34px;aspect-ratio:4/3;background:var(--paper-2);overflow:hidden;
    box-shadow:10px 10px 0 var(--accent)}
  .hero-shot img{width:100%;height:100%;object-fit:cover;display:block}
  /* On a phone the print stays inside the column so the shadow has somewhere
     to fall; square, so it still fills the fold. */
  @media (max-width:760px){
    .hero-shot{margin:34px 0 0;aspect-ratio:1/1}
  }
  @media (min-width:900px){
    .hero-grid.has-photo{display:grid;grid-template-columns:1fr;gap:0}
    .v-trade .hero-grid.has-photo,.v-food .hero-grid.has-photo,
    .v-fitness .hero-grid.has-photo,.v-retail .hero-grid.has-photo{
      grid-template-columns:1.05fr .95fr;gap:48px;align-items:center}
    .v-trade .hero-grid.has-photo .hero-shot,.v-food .hero-grid.has-photo .hero-shot,
    .v-fitness .hero-grid.has-photo .hero-shot,.v-retail .hero-grid.has-photo .hero-shot{
      margin-top:0;aspect-ratio:1/1}
  }
  /* on an accent ground the shadow is paper, so the print has a paper edge */
  .v-trade .hero-shot{box-shadow:10px 10px 0 var(--paper)}

  .hero h1{font-size:calc(var(--hero-size) * var(--hero-scale));color:var(--accent)}
  /* a measure keeps a desktop headline stacked instead of running the width
     of the wrap; on a phone the width itself is the measure (see below). */
  @media (min-width:641px){ .hero h1{max-width:15ch} }
  .hero .lede{margin:20px 0 30px;font-size:19px}
  /* under a headline that is already five lines, a 19px lede is a second
     headline. On a phone it steps back to a reading size. */
  @media (max-width:640px){ .hero .lede{font-size:17px;margin:16px 0 26px} }
  .actions{display:flex;flex-wrap:wrap;gap:12px}
  .hero-note{margin-top:22px;padding-top:14px;display:inline-block;
    border-top:var(--rule) solid color-mix(in srgb, var(--accent) 35%, transparent);
    font:500 11px/1.6 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

  /* trust strip — a hairline grid on the ground, not white boxes on it. Values
     in display type, labels in mono: the two scales side by side. */
  .trust{display:grid;grid-template-columns:1fr 1fr;margin-top:44px;
    border-top:1px solid var(--line);border-left:1px solid var(--line)}
  .trust div{padding:18px 16px 16px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
  /* an odd count used to leave an empty box on the phone grid; the last cell
     takes the whole row instead. */
  .trust div:last-child:nth-child(odd){grid-column:1/-1}
  .trust b{display:block;font-family:var(--display);font-weight:var(--display-weight);
    font-size:clamp(24px,6.6vw,34px);letter-spacing:var(--tracking);line-height:1.05}
  .trust span{display:block;margin-top:8px;font:500 10.5px/1.45 var(--mono);letter-spacing:.1em;
    text-transform:uppercase;color:var(--muted)}
  @media (min-width:700px){
    .trust{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
    .trust div:last-child:nth-child(odd){grid-column:auto}
  }

  /* menu — grouped, priced, and selectable, the way a booking platform does it.
     Rows sit straight on the paper with a hairline between them; a white box
     around a list is the other tell of a template. */
  .menu{margin-top:30px;display:flex;flex-direction:column;gap:34px}
  .mgroup h3{display:flex;gap:14px;font:600 11px/1.5 var(--mono);letter-spacing:.12em;
    text-transform:uppercase;color:var(--accent);margin:0 0 6px}
  .mgroup h3 .n{color:var(--muted)}
  .rows{border-top:1px solid var(--line)}
  /* a button carries a chunky default border on every side — left unreset it
     turns a clean list into a stack of boxes. */
  .row-svc{display:flex;align-items:flex-start;gap:14px;padding:15px 8px 15px 4px;
    border:0;border-bottom:1px solid var(--line);border-radius:0;
    width:100%;text-align:left;background:transparent;font:inherit;color:inherit;-webkit-appearance:none;appearance:none}
  .js .row-svc{cursor:pointer}
  .js .row-svc:hover{background:color-mix(in srgb, var(--accent) 6%, transparent)}
  .row-svc .tick{flex:none;width:20px;height:20px;margin-top:2px;
    border:1px solid color-mix(in srgb, var(--ink) 40%, transparent);display:grid;place-items:center;
    font-size:11px;color:var(--paper)}
  html:not(.js) .row-svc .tick{display:none}
  .row-svc.on{background:color-mix(in srgb, var(--accent) 10%, transparent)}
  .row-svc.on .tick{background:var(--accent);border-color:var(--accent)}
  .row-svc.on .tick::after{content:"\\2713"}
  /* these are spans, because a <button> may only hold phrasing content —
     so each one has to be told to take its own line. */
  .svc-main{flex:1;min-width:0;display:block}
  .svc-name{display:block;font-size:16px;font-weight:650;letter-spacing:-.01em;line-height:1.3}
  .svc-desc{display:block;font-size:13px;line-height:1.45;color:var(--muted);margin-top:4px}
  .svc-meta{flex:none;display:block;text-align:right;padding-left:4px}
  .svc-price{display:block;font:600 14px/1.4 var(--mono);letter-spacing:.02em;font-variant-numeric:tabular-nums}
  .svc-price .svc-unit{font-size:11px;font-weight:500;color:var(--muted)}
  .svc-dur{display:block;font:500 10.5px/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;
    color:var(--muted);margin-top:3px;white-space:nowrap}

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
  .team{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:30px}
  .member{border:1px solid var(--line);padding:18px;text-align:center}
  /* a one-person business is a selling point, but a lone card floating in a
     full-width box reads as an unfinished page. Lay it on its side instead. */
  .team.solo{grid-template-columns:1fr}
  .team.solo .member{display:flex;align-items:center;gap:16px;text-align:left;padding:16px 18px}
  .team.solo .member .av{margin:0}
  .member .av{width:48px;height:48px;margin:0 auto 10px;display:grid;place-items:center;
    background:var(--accent);color:var(--paper);font-family:var(--display);font-weight:var(--display-weight);font-size:20px}
  .member b{display:block;letter-spacing:-.01em}
  .member span{display:block;margin-top:4px;font:500 10.5px/1.4 var(--mono);letter-spacing:.08em;
    text-transform:uppercase;color:var(--muted)}

  /* cards — a hairline, never a radius */
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px;margin-top:30px}
  .card{border:1px solid var(--line);padding:22px}
  .card h3{font-size:18px;margin-bottom:6px}
  .card p{color:var(--muted);font-size:15px;margin:0}
  .price{display:inline-block;margin-top:14px;font:600 12px/1.6 var(--mono);letter-spacing:.06em;color:var(--accent);
    background:color-mix(in srgb, var(--accent) 10%, transparent);padding:3px 9px}

  /* about */
  .about-body{max-width:62ch}
  ul.ticks{list-style:none;padding:0;margin:20px 0 0;display:grid;gap:10px}
  ul.ticks li{padding-left:28px;position:relative;color:var(--muted)}
  ul.ticks li::before{content:"\\2713";position:absolute;left:0;top:4px;width:18px;height:18px;
    background:var(--accent);color:var(--paper);font-size:11px;font-weight:700;line-height:18px;text-align:center}

  /* gallery — for businesses whose work IS the product. Each photo is a
     print: a paper frame, a strip of tape at the top, a degree or two off
     square, a caption underneath. The reveal fades the photo in inside the
     frame, so the tilt on the frame is never touched by a transform. */
  .shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:36px 28px;
    margin-top:40px;padding:14px 8px 8px}
  .shots figure{margin:0;position:relative;background:#fcfbf7;padding:10px 10px 10px;
    box-shadow:0 1px 0 rgba(0,0,0,.05),0 16px 30px -18px rgba(20,16,10,.55);
    transform:rotate(var(--tilt,0deg))}
  .shots figure:nth-child(odd){--tilt:-1.4deg}
  .shots figure:nth-child(even){--tilt:1.1deg}
  .shots figure:nth-child(3n){--tilt:-.6deg}
  .shots figure::before,.cta-shot::before{content:"";position:absolute;left:50%;top:-11px;width:84px;height:24px;
    margin-left:-42px;background:rgba(226,208,150,.62);transform:rotate(-2.5deg);
    box-shadow:0 1px 2px rgba(0,0,0,.08)}
  .shots figure:nth-child(even)::before{transform:rotate(2deg)}
  .shots .ph{aspect-ratio:1/1;overflow:hidden;background:var(--paper-2);border-radius:2px}
  .shots img{width:100%;height:100%;object-fit:cover;display:block}
  .shots figcaption{min-height:1.3em;margin-top:12px;padding:0 2px 6px;text-align:center;
    font:italic 400 14.5px/1.3 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
    color:color-mix(in srgb, var(--ink) 72%, transparent)}
  .shots figure:first-child{grid-column:span 2;grid-row:span 2}
  /* A grid this small on a phone is four postage stamps. A horizontal,
     snap-scrolling row of real-sized prints reads like a stack someone can
     flick through. The vertical padding is room for the tape and the tilt;
     an overflow-x container clips on both axes. */
  @media (max-width:640px){
    .shots{display:flex;gap:20px;margin:34px -22px 0;padding:18px 22px 26px;
      overflow-x:auto;scroll-snap-type:x mandatory;scroll-padding-left:22px;-webkit-overflow-scrolling:touch}
    .shots::-webkit-scrollbar{display:none}
    .shots figure{flex:0 0 78%;scroll-snap-align:start;grid-column:unset;grid-row:unset}
    .shots .ph{aspect-ratio:4/5}
  }

  /* reviews */
  .stars{color:var(--accent);letter-spacing:2px}
  .quote{border:1px solid var(--line);padding:22px;margin:0}
  .quote p{font-size:16px}
  .quote footer{font:600 11px/1.5 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

  /* ── contact: a paper card on ink ───────────────────────────────────────
     This is where the ask is made, so it is the most confident moment on the
     page: the ground goes to ink, a corner-bracketed frame, and inside it a
     paper card carrying the heading and the number. Under the card, a spec
     table of what the business has actually told us — hours, area, address,
     licence — and a numbered list of ways to reach them. A row with nothing
     real behind it is never drawn; there is no "TBC". */
  .ask{position:relative;padding:22px 18px 10px}
  /* Frames are four corner marks, not a rounded box. Drawn with background
     gradients so they need no extra markup and no pseudo-elements. */
  .brk{--b:rgba(255,255,255,.5);background-image:
      linear-gradient(var(--b),var(--b)),linear-gradient(var(--b),var(--b)),
      linear-gradient(var(--b),var(--b)),linear-gradient(var(--b),var(--b)),
      linear-gradient(var(--b),var(--b)),linear-gradient(var(--b),var(--b)),
      linear-gradient(var(--b),var(--b)),linear-gradient(var(--b),var(--b));
    background-repeat:no-repeat;
    background-size:18px 1px,1px 18px,18px 1px,1px 18px,18px 1px,1px 18px,18px 1px,1px 18px;
    background-position:top left,top left,top right,top right,bottom left,bottom left,bottom right,bottom right}
  .ask-tag{margin-bottom:14px}
  .ask-tag .eyebrow{color:var(--muted)}
  /* room above the card for the print pinned over its corner, and room on
     the right so the label wraps before it runs underneath the print */
  .ask.has-shot .ask-tag{min-height:100px;padding-right:136px}
  .cta-box{position:relative;background:var(--card);color:var(--ink);padding:32px 24px 28px;
    --muted:color-mix(in srgb, var(--ink) 64%, var(--paper));--line:color-mix(in srgb, var(--ink) 16%, var(--paper));
    box-shadow:8px 8px 0 color-mix(in srgb, var(--accent) 85%, var(--ink))}
  .cta-box h2{color:var(--accent);font-size:clamp(30px,8.6vw,52px);margin-bottom:12px}
  .cta-box .lede{margin:0 0 20px;font-size:16px}
  .cta-box .actions{margin-top:0}
  .big-phone{display:block;font-family:var(--display);font-weight:var(--display-weight);
    font-size:clamp(22px,7.6vw,46px);letter-spacing:-.03em;line-height:1;color:var(--accent);
    text-decoration:none;margin:0 0 22px;font-variant-numeric:tabular-nums}
  .big-mail{display:block;font:600 clamp(14px,4.4vw,20px)/1.3 var(--mono);letter-spacing:.02em;
    color:var(--ink);text-decoration:none;margin:0 0 22px;overflow-wrap:anywhere}
  /* The second photo, pinned over the corner of the card like a print left on
     a desk: proof this page was built from their real place, right where the
     ask is made. */
  .cta-shot{position:absolute;right:6px;top:-6px;width:112px;margin:0;padding:6px 6px 16px;z-index:2;
    background:#fcfbf7;box-shadow:0 12px 24px -14px rgba(0,0,0,.7);transform:rotate(3deg)}
  .cta-shot::before{width:64px;margin-left:-32px;top:-9px;height:20px}
  .cta-shot .ph{aspect-ratio:1/1;overflow:hidden;border-radius:2px;background:var(--paper-2)}
  .cta-shot img{width:100%;height:100%;object-fit:cover;display:block}
  .spec{margin:22px 0 0;padding:0;border-top:1px solid var(--line)}
  .spec>div{padding:12px 0 13px;border-bottom:1px solid var(--line)}
  .spec dt{font:500 10px/1.5 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:3px}
  .spec dd{margin:0;font:600 12.5px/1.55 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--paper)}
  .spec dd a{text-decoration:none}
  .spec .hrs{display:grid;grid-template-columns:auto 1fr;gap:2px 16px}
  .links{list-style:none;margin:26px 0 0;padding:0}
  .links li{border-bottom:1px solid var(--line)}
  .links a{display:flex;align-items:center;gap:18px;padding:19px 4px;text-decoration:none;color:var(--paper);
    font:600 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
  .links .n{color:var(--muted);font-weight:500;font-size:10px}
  .links .arr{margin-left:auto;font-size:15px}
  .links a:hover{color:var(--accent)}
  @media (max-width:400px){
    .ask{padding:18px 12px 8px}
    .cta-box{padding:26px 18px 24px}
  }

  footer.site{padding:26px 0 30px;border-top:1px solid var(--line);
    font:500 10.5px/1.7 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

  /* sticky mobile call bar */
  .callbar{display:none}
  @media (max-width:760px){
    nav{display:none}
    body{padding-bottom:74px}
    .callbar{
      display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;gap:10px;padding:10px 14px;
      background:color-mix(in srgb, var(--paper) 94%, transparent);backdrop-filter:blur(10px);border-top:1px solid var(--line);
    }
    .callbar .btn{flex:1}
    .bar .btn span.label{display:none}
  }
  /* ── hero shape per voice ─────────────────────────────────────────────────
     Type alone could not separate two sans voices without loading web fonts,
     which would break the "no external requests" promise in the pitch. So the
     hero is structurally different instead. */

  /* TRADE — a full-bleed block of colour. Reads like a work truck. The grain
     and grid ride on top of the accent; everything on it goes to paper. */
  .v-trade .hero{background-color:var(--accent);color:#fff;
    --muted:rgba(255,255,255,.8);--line:rgba(255,255,255,.3);--grid-line:rgba(255,255,255,.06)}
  .v-trade .hero::before{
    background-image:var(--grain),
      linear-gradient(var(--grid-line) 1px,transparent 1px),
      linear-gradient(90deg,var(--grid-line) 1px,transparent 1px);
    background-size:220px 220px,36px 36px,36px 36px}
  .v-trade .hero h1{color:#fff}
  .v-trade .tag{background:var(--paper);color:var(--accent)}
  .v-trade .hero-note{border-top-color:rgba(255,255,255,.35)}
  .v-trade .hero .btn-primary{background:var(--paper);color:var(--accent);border-color:var(--paper)}
  .v-trade .hero .btn-ghost{color:#fff;border-color:rgba(255,255,255,.55)}

  /* CARE — centred and unhurried. Calm is the product. */
  .v-care .hero{text-align:center}
  .v-care .hero h1,.v-care .hero .lede{margin-left:auto;margin-right:auto}
  .v-care .hero .actions{justify-content:center}
  .v-care .hero-inner{max-width:44rem;margin:0 auto}
  .v-care .tag{transform-origin:center}

  /* BEAUTY — editorial: a rule down the side, deep top margin, nothing rushed. */
  .v-beauty .hero{padding-top:clamp(56px,10vw,100px)}
  .v-beauty .hero-inner{border-left:2px solid var(--accent);padding-left:26px}
  .v-beauty .sec{padding-bottom:12px;border-bottom:1px solid var(--line)}

  /* Measures tuned for a desktop column are a straitjacket on a 390px screen:
     they force line breaks the width itself would never make. On a phone the
     width is the measure. */
  @media (max-width:640px){
    .hero h1{max-width:none}
  }

  /* FOOD — the copy sits on a card, like something propped on the counter:
     paper, a hairline, a hard shadow. */
  .v-food .hero{padding-top:40px}
  .v-food .hero-inner{background:var(--card);border:1px solid var(--line);
    box-shadow:8px 8px 0 var(--accent);padding:36px 32px}
  .v-food .trust{margin-top:28px}

  @media (max-width:760px){
    .v-food .hero-inner{padding:26px 20px}
    .v-beauty .hero-inner{padding-left:18px}
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
       to how a print develops than text sliding up. It sits on the inner
       frame, never on a tilted element, or the tilt would be overwritten. */
    .js .photo-in{opacity:0;transform:scale(1.045)}
    .js .in .photo-in,.js .photo-in.in{opacity:1;transform:none;
      transition:opacity .8s var(--ease),transform 1s var(--ease)}
    .card{transition:transform .28s var(--ease),border-color .28s var(--ease),box-shadow .28s var(--ease)}
    .card:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 45%,var(--line));
      box-shadow:0 10px 24px -14px rgba(16,32,40,.35)}
    .shots img,.hero-shot img{transition:transform .5s var(--ease)}
    .shots figure:hover img,.hero-shot:hover img{transform:scale(1.06)}
    .btn{transition:transform .18s var(--ease),filter .18s var(--ease)}
    .btn:active{transform:scale(.97)}
    .trust div{transition:background .3s var(--ease)}
    .trust div:hover{background:color-mix(in srgb,var(--accent) 6%,transparent)}
    .js .callbar{transform:translateY(110%);transition:transform .38s var(--ease)}
    .js .callbar.up{transform:none}
    .tel-pulse{position:relative}
  }
  @media (prefers-reduced-motion:reduce){
    .rise,.js .rise,.photo-in,.js .photo-in{opacity:1;transform:none}
    .callbar,.js .callbar{transform:none}
  }

  @media print{header,.callbar{position:static}.rise{opacity:1;transform:none}}
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

<div class="hero">
  <div class="wrap">
    <div class="hero-grid${photos.length ? ' has-photo' : ''}">
    <div class="hero-inner">
    ${b.logo ? `<img class="logo rise" style="--i:0" src="${esc(b.logo)}" alt="${esc(b.name)}" width="${esc(b.logoWidth || 300)}">` : ''}
    ${b.category ? `<div class="tagwrap rise" style="--i:0"><span class="eyebrow tag">${esc(b.category)}${a.city ? ' · ' + esc(a.city) + ', ' + esc(a.state || '') : ''}</span></div>` : ''}
    <h1 class="rise" style="--i:1">${esc(b.headline || b.tagline)}</h1>
    ${b.subhead ? `<p class="lede rise" style="--i:2">${esc(b.subhead)}</p>` : ''}
    <div class="actions rise" style="--i:3">
      ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">${esc(b.cta?.primary || 'Call ' + b.phone)}</a>` : ''}
      ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Get directions</a>` : ''}
    </div>
    ${b.heroNote ? `<div class="hero-note rise" style="--i:4">${esc(b.heroNote)}</div>` : ''}
    </div>
    ${heroPhoto ? `<div class="hero-shot photo-in" style="--i:2"><img src="${esc(typeof heroPhoto === 'string' ? heroPhoto : heroPhoto.src)}" alt="${esc(typeof heroPhoto === 'object' && heroPhoto.alt || b.name)}" loading="eager"></div>` : ''}
    </div>
    ${highlights.length ? `<div class="trust rise" style="--i:5">${highlights.map((h) =>
      `<div><b>${esc(h.value)}</b><span>${esc(h.label)}</span></div>`).join('')}</div>` : ''}
  </div>
</div>

${services.length ? `
<section id="services">
  <div class="wrap">
    <div class="eyebrow sec"><span class="n">${num()}</span><span>Services</span></div>
    <h2>${esc(b.servicesHeading || 'What we do')}</h2>
    ${b.servicesLede ? `<p class="lede">${esc(b.servicesLede)}</p>` : ''}
    ${''/* Every service list is a menu people choose from, not a row of cards.
           Prices and durations show when the business has given them; when it
           has not, the choosing and the request still work. We never invent a
           number to fill the column. */}
    ${`<div class="menu">${groups.map(([name, items], gi) => `
        <div class="mgroup">
          ${name ? `<h3><span class="n">${String(gi + 1).padStart(2, '0')}</span>${esc(name)}</h3>` : ''}
          <div class="rows">
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
    <div class="eyebrow sec"><span class="n">${num()}</span><span>Our team</span></div>
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
  // The hero photo already leads — repeating it here would read as padding,
  // not more evidence. Two galleries, each only when there is something for
  // it: the work under "Recent work", and everything else — the storefront,
  // the chairs, the team — under the place's own name, which claims nothing.
  const prints = (list, offset) => list.map((p, i) =>
    `<figure><div class="ph"><img src="${esc(p.src || p)}" alt="${esc(p.alt || b.name + ' — photo ' + (i + offset))}" loading="lazy"></div><figcaption>${esc(caption(p, i))}</figcaption></figure>`).join('');
  const work = workShots.length ? `
<section id="work">
  <div class="wrap">
    <div class="eyebrow sec"><span class="n">${num()}</span><span>${esc(b.galleryEyebrow || 'Our work')}</span></div>
    <h2>${esc(b.galleryHeading || 'Recent work')}</h2>
    ${b.galleryLede ? `<p class="lede">${esc(b.galleryLede)}</p>` : ''}
    <div class="shots">${prints(workShots, 2)}</div>
  </div>
</section>` : '';
  const around = placeShots.length ? `
<section id="place">
  <div class="wrap">
    <div class="eyebrow sec"><span class="n">${num()}</span><span>${esc(b.placeEyebrow || 'The place')}</span></div>
    <h2>${esc(b.placeHeading || 'Around ' + (b.shortName || b.name))}</h2>
    <div class="shots">${prints(placeShots, 2 + workShots.length)}</div>
  </div>
</section>` : '';
  return work + around;
})()}

${b.about ? `
<section id="about">
  <div class="wrap">
    <div class="eyebrow sec"><span class="n">${num()}</span><span>About</span></div>
    <h2>${esc(b.aboutHeading || 'About ' + b.name)}</h2>
    <div class="about-body">
      ${String(b.about).split('\n\n').map((p) => `<p class="lede">${esc(p)}</p>`).join('')}
      ${b.points?.length ? `<ul class="ticks">${b.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>` : ''}
    </div>
  </div>
</section>` : ''}

${reviews.length ? `
<section id="reviews">
  <div class="wrap">
    <div class="eyebrow sec"><span class="n">${num()}</span><span>Reviews</span></div>
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

${(() => {
  // The spec table under the card. Only what business.json actually holds:
  // an empty row would be a claim by implication, so it is simply not drawn.
  const spec = [
    hours.length && `<div><dt>Hours</dt><dd><span class="hrs">${hours.map((h) =>
      `<span>${esc(h.days)}</span><span>${esc(h.time)}</span>`).join('')}</span></dd></div>`,
    b.serviceArea?.length && `<div><dt>Service area</dt><dd>${esc(b.serviceArea.join(' · '))}</dd></div>`,
    a.street && `<div><dt>Address</dt><dd><a href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">${esc(addressLine(a))}</a></dd></div>`,
    b.phone && b.email && `<div><dt>Email</dt><dd><a href="mailto:${esc(b.email)}">${esc(b.email)}</a></dd></div>`,
    b.license && `<div><dt>License</dt><dd>${esc(b.license)}</dd></div>`,
  ].filter(Boolean);
  // Every way to reach them, numbered. One link alone is not a list.
  const links = [
    b.phone && ['Call', 'tel:' + tel],
    b.email && ['Email', 'mailto:' + b.email],
    a.street && ['Directions', mapsUrl(a)],
    b.booking?.url && ['Book online', b.booking.url],
  ].filter(Boolean);
  return `
<section id="contact" class="contact">
  <div class="wrap">
    <div class="ask brk${askPhoto ? ' has-shot' : ''}">
      <div class="ask-tag"><span class="eyebrow">${num()} / Contact${place ? ' / ' + esc(place) : ''}</span></div>
      ${askPhoto ? `<figure class="cta-shot"><div class="ph"><img src="${esc((askPhoto.src || askPhoto))}" alt="" loading="lazy"></div></figure>` : ''}
      <div class="cta-box">
        <h2>${esc(b.ctaHeading || 'Ready when you are')}</h2>
        <p class="lede">${esc(b.ctaLede || 'Call and talk to a real person.')}</p>
        ${b.phone ? `<a class="big-phone" href="tel:${esc(tel)}">${esc(b.phone)}</a>`
          : b.email ? `<a class="big-mail" href="mailto:${esc(b.email)}">${esc(b.email)}</a>` : ''}
        <div class="actions">
          ${b.phone ? `<a class="btn btn-primary" href="tel:${esc(tel)}">Call now</a>`
            : b.email ? `<a class="btn btn-primary" href="mailto:${esc(b.email)}">Email us</a>` : ''}
          ${a.street ? `<a class="btn btn-ghost" href="${esc(mapsUrl(a))}" target="_blank" rel="noopener">Directions</a>` : ''}
        </div>
      </div>
      ${spec.length ? `<dl class="spec">${spec.join('')}</dl>` : ''}
      ${links.length > 1 ? `<ol class="links">${links.map(([t, h], i) =>
        `<li><a href="${esc(h)}"${/^https?:/.test(h) ? ' target="_blank" rel="noopener"' : ''}><span class="n">${String(i + 1).padStart(2, '0')}</span>${esc(t)}<span class="arr" aria-hidden="true">\u2197</span></a></li>`).join('')}</ol>` : ''}
    </div>
  </div>
</section>`;
})()}

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

    var targets = document.querySelectorAll('section .sec, section h2, section .lede, .card, .quote, .cta-box, .spec, .links li, ul.ticks li');
    targets.forEach(function(el){ el.classList.add('rise'); });
    // Photos settle rather than slide — the inner frame of each print gets
    // the scale-fade defined for .photo-in instead of the text .rise. The
    // inner frame, not the figure: the figure carries the tilt.
    var photoTargets = document.querySelectorAll('.shots .ph, .cta-shot .ph');
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
