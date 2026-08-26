// Turns business.json + the audit flags into the audit table, the email
// you send with the rebuilt page, and the follow-up text.

const checks = require('./checks');

// The email body, with nothing to strip out. pitch.md embeds it for context;
// email.txt is the version you actually paste into your mail client.
function emailBody(ctx) {
  const { b, from, owner, noSite, host, money, tier, care, pricing, emailFixes } = ctx;
  // "McManus Web Co." already ends in a period; do not add a second one.
  const intro = from.businessName
    ? `I'm ${from.name}, I run ${String(from.businessName).replace(/\.$/, '')}.`
    : `I'm ${from.name}.`;

  return `Hi ${owner},

${intro} I build websites for ${b.address?.city || 'local'} businesses.

${b.pitchOpener
  ? `${b.pitchOpener}

It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What's on it:`
  : noSite
  ? `I went looking for your website and ${host ? `${host} is showing a hosting placeholder page` : 'could not find one'} — the kind that says there is no site at this address. Anyone who looks you up and lands there assumes you closed.

So I built you one. It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What's on it:`
  : `I looked at your website and rebuilt it. It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What I changed:`}
${emailFixes}

Nothing is live. This is just so you can see what it would look like.

${money(tier)} for the ${noSite ? tier.label.toLowerCase().replace('rebuild', 'website') : tier.label.toLowerCase()}, live on your domain in ${tier.includes.find((i) => /live in/i.test(i))?.replace(/live in /i, '') || 'about a week'}.${care ? ` ${money(care)} after that if you want me hosting it and making changes for you.` : ''} ${pricing.guarantee}

Worth a 10-minute call?

${from.name}
${from.phone ? from.phone + '\n' : ''}${from.email}`;
}

module.exports = function pitch(b, pricing) {
  const tierKey = b.tier || pricing.defaultTier;
  const tier = pricing.tiers[tierKey];
  if (!tier) throw new Error(`Unknown tier "${tierKey}" — options: ${Object.keys(pricing.tiers).join(', ')}`);

  const audit = b.audit || {};
  // Findings never measured in a browser must not become claims. A raw-HTML
  // run cannot see JavaScript-rendered hours, phone links or layout.
  const unverified = b._scout && b._scout.rendered === false;
  const scored = checks.map((c) => ({ ...c, pass: audit[c.key] === true }));
  const failed = scored.filter((c) => !c.pass);
  const score = scored.length - failed.length;
  const money = (t) => `${pricing.currency}${t.price.toLocaleString('en-US')}${t.unit || ''}`;
  const from = pricing.from;
  const care = pricing.tiers.care;
  const owner = b.owner || 'there';
  // "McManus Web Co." already ends in a period; let it serve as the sentence's.
  const fromBiz = (from.businessName || '').replace(/\.\s*$/, '');

  // "I rebuilt your website" is the wrong opening line for someone who does not
  // have one. A domain showing a hosting placeholder needs to be named plainly.
  const status = b._scout?.currentSiteStatus || '';
  const noSite = !b.currentSite || /no website|does not resolve|parked|placeholder/i.test(status);
  const host = String(b.currentSite || '').replace(/^https?:\/\/(www\.)?/i, '').replace(/\/+$/, '');

  const table = scored.map((c) =>
    `| ${c.pass ? '✅' : '❌'} | ${c.label} | ${c.pass ? '—' : c.gap} |`).join('\n');

  const fixes = failed.length
    ? failed.map((c) => `- ${c.fixed}`).join('\n')
    : checks.slice(0, 5).map((c) => `- ${c.fixed}`).join('\n');

  // Only claim what the attached page actually delivers. Promising "hours
  // listed" when the hours section is empty gets noticed the moment they open it.
  const delivers = {
    hours:    (b.hours || []).some((h) => h.schema),
    address:  Boolean(b.address?.street),
    services: (b.services || []).some((x) => x.price),
    reviews:  (b.reviews || []).length > 0,
    phoneTap: Boolean(b.phone),
    cta:      Boolean(b.phone),
  };
  const shipped = (c) => delivers[c.key] !== false;

  const emailFixes = (failed.length ? failed : checks)
    .filter(shipped).slice(0, 5).map((c) => `- ${c.fixed}`).join('\n');

  const notYet = failed.filter((c) => !shipped(c));

  const subject = b.pitchOpener
    ? "You don't have a website of your own — I built you one"
    : noSite
    ? 'Your domain is showing a blank hosting page — I built you a website'
    : 'Rebuilt your website — take a look before you say no';
  const body = emailBody({ b, from, owner, noSite, host, money, tier, care, pricing, emailFixes });

  const sheet = `# ${b.name} — pitch sheet

**Current site:** ${b.currentSite || '_none found_'}
**Rebuilt page:** \`index.html\` (in this folder — attach it or host it)
**Score:** ${score}/${checks.length}${unverified ? ' — UNVERIFIED, read the warning below' : ''}
**Price to quote:** ${money(tier)} — ${tier.label}${care ? `, then ${money(care)} for hosting and updates` : ''}

---

${unverified ? `> **Do not send yet.** These findings come from the served HTML, not a rendered page.
> If this site builds itself with JavaScript, its hours, phone link and mobile layout may all be
> there and simply invisible to that check. Re-run the scout with a browser, or open the site
> yourself, before claiming any of this to the owner.

` : ''}## What's wrong with the site they have

| | Check | Problem |
|---|---|---|
${table}

## What the rebuild fixes

${fixes}

${notYet.length ? `> **Fill these in before you send.** The page does not yet show: ${notYet.map((c) => c.label.toLowerCase()).join(', ')}. They are on their Google listing — the email does not promise them until they are on the page.

` : ''}---

## Email to send

**Subject:** ${subject}

Hi ${owner},

I'm ${from.name}${fromBiz ? `, I run ${fromBiz}` : ''}. I build websites for ${b.address?.city || 'local'} businesses.

${b.pitchOpener
  ? `${b.pitchOpener}

It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What's on it:`
  : noSite
  ? `I went looking for your website and ${host ? `${host} is showing a hosting placeholder page` : 'could not find one'} — the kind that says there is no site at this address. Anyone who looks you up and lands there assumes you closed.

So I built you one. It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What's on it:`
  : `I looked at your website and rebuilt it. It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What I changed:`}
${emailFixes}

Nothing is live. This is just so you can see what it would look like.

${money(tier)} for the ${noSite ? tier.label.toLowerCase().replace('rebuild', 'website') : tier.label.toLowerCase()}, live on your domain in ${tier.includes.find((i) => /live in/i.test(i))?.replace(/live in /i, '') || 'about a week'}.${care ? ` ${money(care)} after that if you want me hosting it and making changes for you.` : ''} ${pricing.guarantee}

Worth a 10-minute call?

${from.name}
${from.phone ? from.phone + '\n' : ''}${from.email}

---

## Follow-up text (day 3, if no reply)

> Hi ${owner}, ${from.name} here — I sent over ${noSite ? 'a website I built for you' : 'a rebuilt version of your website'} earlier this week. Did it come through? Happy to walk you through it in 10 minutes. No cost to look.

## If they ask "why so cheap / what's the catch"

> No catch. I already built it — you're paying me to put it on your domain and keep it working. If you don't like it, you don't pay, and you keep the file.

## What's included at ${money(tier)} — ${noSite ? 'they have no site at all, so this is a build, not a rebuild' : tier.label}

${tier.includes.map((i) => `- ${i}`).join('\n')}
`;

  return { sheet, subject, body, notYet };
};

module.exports.emailBody = emailBody;
