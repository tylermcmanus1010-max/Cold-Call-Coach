// The 12 things a local business site has to get right.
// Each check you mark `false` in business.json becomes a line in the pitch email.

module.exports = [
  { key: 'mobile',      label: 'Works on a phone',            gap: 'Site is unusable on a phone — 70%+ of your customers are on one',           fixed: 'Rebuilt mobile-first; tested down to a 320px screen' },
  { key: 'https',       label: 'Secure (HTTPS)',              gap: 'No SSL — Chrome shows visitors a "Not secure" warning',                     fixed: 'HTTPS with a free auto-renewing certificate' },
  { key: 'speed',       label: 'Loads in under 2 seconds',    gap: 'Slow load — every extra second costs about 7% of conversions',              fixed: 'Single self-contained file, no trackers, loads instantly' },
  { key: 'phoneTap',    label: 'Tap-to-call phone number',    gap: 'Phone number is not tappable, so mobile visitors have to copy it by hand',   fixed: 'Tap-to-call in the header and a sticky call bar on mobile' },
  // SOFT — derived from page text, and therefore not reliable enough to put in
  // front of an owner. Lazy-loaded sections, text inside images and content
  // behind tabs all read as absent. Reported for your own eyes only; never
  // claimed in a pitch. See `hard` below.
  { key: 'hours',       soft: true, label: 'Hours listed',                gap: 'Hours are missing or out of date',                                          fixed: 'Hours listed on-page and marked up for Google' },
  { key: 'address', soft: true,     label: 'Address + directions',        gap: 'No address or one-tap directions',                                          fixed: 'Address with a one-tap Google Maps link' },
  { key: 'services', soft: true,    label: 'Services and pricing',        gap: 'Services are vague and no pricing is shown, so people call competitors',     fixed: 'Every service listed with a starting price' },
  { key: 'reviews', soft: true,     label: 'Reviews on the page',         gap: 'Your good reviews are stuck on Yelp instead of on your own site',           fixed: 'Best reviews pulled onto the homepage' },
  { key: 'cta', soft: true,         label: 'Clear call to action',        gap: 'No obvious next step — visitors land and leave',                            fixed: 'One clear action above the fold on every screen size' },
  { key: 'seo',         label: 'Google business markup',      gap: 'No structured data, so Google cannot show your hours, rating or map card',   fixed: 'LocalBusiness schema so Google can read hours, phone, rating and location' },
  { key: 'meta',        label: 'Title + description',         gap: 'Page title and description are empty or default, hurting search ranking',    fixed: 'Written page title, description and social preview card' },
  { key: 'social',      label: 'Shareable link preview',      gap: 'Link looks blank when shared in a text or on Facebook',                      fixed: 'Open Graph tags so the link previews properly when shared' },
];
