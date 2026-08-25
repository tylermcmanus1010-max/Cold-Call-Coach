// Turns business.json + the audit flags into the audit table, the email
// you send with the rebuilt page, and the follow-up text.

const checks = require('./checks');

module.exports = function pitch(b, pricing) {
  const tierKey = b.tier || pricing.defaultTier;
  const tier = pricing.tiers[tierKey];
  if (!tier) throw new Error(`Unknown tier "${tierKey}" — options: ${Object.keys(pricing.tiers).join(', ')}`);

  const audit = b.audit || {};
  const scored = checks.map((c) => ({ ...c, pass: audit[c.key] === true }));
  const failed = scored.filter((c) => !c.pass);
  const score = scored.length - failed.length;
  const money = (t) => `${pricing.currency}${t.price.toLocaleString('en-US')}${t.unit || ''}`;
  const from = pricing.from;
  const care = pricing.tiers.care;
  const owner = b.owner || 'there';

  const table = scored.map((c) =>
    `| ${c.pass ? '✅' : '❌'} | ${c.label} | ${c.pass ? '—' : c.gap} |`).join('\n');

  const fixes = failed.length
    ? failed.map((c) => `- ${c.fixed}`).join('\n')
    : checks.slice(0, 5).map((c) => `- ${c.fixed}`).join('\n');

  const emailFixes = (failed.length ? failed : checks).slice(0, 5)
    .map((c) => `- ${c.fixed}`).join('\n');

  return `# ${b.name} — pitch sheet

**Current site:** ${b.currentSite || '_none found_'}
**Rebuilt page:** \`index.html\` (in this folder — attach it or host it)
**Score:** ${score}/${checks.length}
**Price to quote:** ${money(tier)} — ${tier.label}${care ? `, then ${money(care)} for hosting and updates` : ''}

---

## What's wrong with the site they have

| | Check | Problem |
|---|---|---|
${table}

## What the rebuild fixes

${fixes}

---

## Email to send

**Subject:** Rebuilt your website — take a look before you say no

Hi ${owner},

I'm ${from.name}${from.businessName ? `, I run ${from.businessName}` : ''}. I build websites for ${b.address?.city || 'local'} businesses.

I looked at ${b.currentSite ? 'your website' : "your listing online"} and rebuilt it. It's attached — open it on your phone.${b.liveUrl ? ` You can also see it here: ${b.liveUrl}` : ''}

What I changed:
${emailFixes}

Nothing is live. This is just so you can see what it would look like.

${money(tier)} for the ${tier.label.toLowerCase()}, live on your domain in ${tier.includes.find((i) => /live in/i.test(i))?.replace(/live in /i, '') || 'about a week'}.${care ? ` ${money(care)} after that if you want me hosting it and making changes for you.` : ''} ${pricing.guarantee}

Worth a 10-minute call?

${from.name}
${from.phone ? from.phone + '\n' : ''}${from.email}

---

## Follow-up text (day 3, if no reply)

> Hi ${owner}, ${from.name} here — I sent over a rebuilt version of your website earlier this week. Did it come through? Happy to walk you through it in 10 minutes. No cost to look.

## If they ask "why so cheap / what's the catch"

> No catch. I already built it — you're paying me to put it on your domain and keep it working. If you don't like it, you don't pay, and you keep the file.

## What's included at ${money(tier)}

${tier.includes.map((i) => `- ${i}`).join('\n')}
`;
};
