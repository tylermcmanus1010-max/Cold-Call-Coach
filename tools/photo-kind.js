// What a photo is OF decides where it may go on the page. "Recent work"
// above a picture of a wall is a claim the page cannot back — the same
// class of mistake as an invented review. So every photo carries a `kind`:
//
//   work     the product: a finished cut, a cake, a re-roofed house, a
//            client in the chair. The only kind allowed under "Recent work".
//   place    the storefront, the interior, the chairs, the truck, the sign.
//   team     the people who work there.
//   product  something they sell, on a shelf.
//   other    real, theirs, but none of the above.
//
// Untagged means nobody has looked yet. Render treats that as "not work":
// it may lead the hero (a real photo of their place is honest anywhere the
// page makes no claim about it) but it never sits under "Recent work".
//
// guessKind is the cheap first pass, from what the harvester saw around
// the image: its URL, its alt text, and the heading it sat under. It says
// nothing when unsure. The designer agent looks at every photo (./cc shot
// writes them out) and settles the ones this could not.

const KINDS = ['work', 'place', 'team', 'product', 'other'];

const WORK = /\b(work|gallery|portfolio|before|after|results?|cuts?|colou?r|styles?|balayage|lashes|nails|cakes?|cupcakes?|projects?|installs?|installation|roofs?|roofing|repairs?|remodel|job|jobs|completed|finished|smile|smiles|transformation|treatment|our-work|recent)\b/i;
const TEAM = /\b(team|staff|meet|our-team|stylists?|barbers?|technicians?|crew|doctors?|dr|dds|dmd|owner|founder|about-us|about)\b/i;
const PLACE = /\b(store|storefront|shop|salon|office|interior|inside|exterior|location|front|building|lobby|reception|waiting|room|chairs?|station|truck|van|sign|entrance|door|window)\b/i;
const PRODUCT = /\b(products?|retail|shelf|shelves|menu|pastr(y|ies)|bread|display)\b/i;

// Words on a path: "/wp-content/uploads/2024/our-work/pink-mullet.jpg"
// becomes "wp content uploads 2024 our work pink mullet" so \b matches.
const words = (s) => String(s || '').replace(/[\/_\-.%+]+/g, ' ');

function guessKind({ url, alt, under } = {}) {
  // The heading the image sat under is the strongest signal — a site owner
  // put it there. Then alt, then the path.
  for (const s of [under, alt, url]) {
    const w = words(s);
    if (!w.trim()) continue;
    if (WORK.test(w)) return 'work';
    if (TEAM.test(w)) return 'team';
    if (PRODUCT.test(w)) return 'product';
    if (PLACE.test(w)) return 'place';
  }
  return undefined;
}

module.exports = { KINDS, guessKind };
