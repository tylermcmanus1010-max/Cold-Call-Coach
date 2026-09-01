// The advice block on the board.
//
// Written from the numbers in front of it, not from general sales wisdom —
// every claim here has to be recomputed each build, so it can never drift into
// saying something the data stopped supporting.

const { esc } = require('./board');

module.exports = function advice(rows) {
  const callable = rows.filter((r) => !r.blocked);
  const agency = rows.filter((r) => r.blocked === 'has an agency');
  const wrongUrl = rows.filter((r) => r.checkUrl && !r.blocked);
  const captcha = rows.filter((r) => /bot check/.test(r.blocked || ''));
  const noEmail = rows.filter((r) => !r.email);
  const unmeasured = rows.filter((r) => !r.rendered);
  const zero = callable.filter((r) => r.passed === 0);
  const nearlyFine = callable.filter((r) => r.passed >= 5);
  const parked = callable.filter((r) => r.parked);
  const noNumber = rows.filter((r) => /no number in the listing/.test(r.blocked || ''));
  const derived = rows.filter((r) => r.stateDerived);

  // Which trades actually have broken sites, so effort goes where the gaps are.
  const byTrade = {};
  for (const r of callable) {
    const t = (r.category || 'other').toLowerCase();
    const g = t.match(/dent|dds|ortho/) ? 'dental'
      : t.match(/plumb|roof|electric|hvac|contract|paint|carpent|floor|tiler|window|metal/) ? 'trades'
      : t.match(/car|auto|tyre|tire/) ? 'auto'
      : t.match(/hair|beauty|nail|massage|salon|spa/) ? 'beauty'
      : t.match(/doctor|veterin|vet|medic/) ? 'clinics'
      : t.match(/lawyer|account|insur|estate|financial/) ? 'professional'
      : 'other';
    byTrade[g] = byTrade[g] || { n: 0, gaps: 0 };
    byTrade[g].n++;
    byTrade[g].gaps += (7 - r.passed);
  }
  const trades = Object.entries(byTrade)
    .filter(([, v]) => v.n >= 3)
    .map(([k, v]) => [k, v.n, (v.gaps / v.n).toFixed(1)])
    .sort((a, b) => b[2] - a[2]);

  const pct = (n) => Math.round((n / Math.max(1, rows.length)) * 100);

  return `
<p>Everything below is recomputed from this build. Nothing here is a rule of thumb — if the numbers change, the advice changes with them.</p>

<h3>Only ${callable.length} of ${rows.length} are worth dialling</h3>
<p>The rest are filtered out for a reason printed on their row. That is the single most valuable thing this board does: <strong>a bad lead costs a real phone call, and some of them cost your reputation.</strong> The commonest disqualifiers here are an agency already being paid, a toll-free number that reaches a call centre, and a URL that may not belong to the business at all.</p>

${agency.length ? `<h3>${agency.length} already have an agency — and they cluster</h3>
<p>Doctible, WEO Media and the like. Someone is being paid to maintain those sites and updated them recently. Dental in particular is one of the most heavily farmed verticals in local marketing; agencies have been calling those practices for years. If the next few dentists also come back agency-run, the answer is not to call more dentists — it is to weight the scout toward trades, where nobody is farming them.</p>` : ''}

<h3>${noEmail.length} of ${rows.length} have no email address, and that is correct</h3>
<p>An address that is not in the record does not exist. Two guessed addresses hard-bounced on 30 August, and one was retried eleven minutes after a permanent <code>550</code> — the exact behaviour that gets a personal Gmail account flagged as a bulk sender. Every piece of outreach you do runs through that one account, so the downside is not two lost emails, it is losing the ability to send at all. <strong>Get the address on the call.</strong> That is what the number is for, and it is how every address you do have was obtained.</p>

${wrongUrl.length ? `<h3>${wrongUrl.length} rows are flagged "open this first"</h3>
<p>The domain shares no distinctive word with the business name — which usually means the directory gave us a stale domain, a reseller's placeholder, or a competitor's page. It is a rough signal and it does over-flag acronym domains, so it warns rather than drops the lead. Six wrong URLs turned up in a single week — Estrella, House of Stemms, Big Kahuna's, RT Roofing, Right Lawyers, Palm Dental — and <em>every one was caught by you opening the site on your phone before pitching.</em> That habit is doing more for lead quality than any code in this repo.</p>` : ''}

${captcha.length ? `<h3>${captcha.length} are behind a bot check and were dropped</h3>
<p>Their URL is a CAPTCHA interstitial — <code>/.well-known/sgcaptcha/</code> and the like. Those answer 200 and render like a page, so every check ran against the challenge rather than the site. Left in, this board would have had you tell six plumbers and salons their phone number was untappable when what we measured was a robot test. A site behind a firewall usually has someone maintaining it anyway.</p>` : ''}

${unmeasured.length ? `<h3>${unmeasured.length} were not measured in a real browser</h3>
<p>Findings read off raw HTML cannot see hours, phone links or layout that JavaScript builds after load. Those rows are fine for deciding who to ring, but <strong>do not read their findings out to an owner</strong> until a browser run confirms them.</p>` : ''}

${parked.length ? `<h3>${parked.length} have no website at all — start here</h3>
<p>Their domain resolves to a registrar placeholder or a marketplace listing: a <code>/lander</code> page, or HugeDomains offering the name for sale. These are the easiest calls on the board, because you are not criticising anyone's work — <strong>you are telling them something they almost certainly do not know.</strong> "I typed your name into Google and the page that came up is selling your own domain back to you" gets a reaction every time. It is also the one finding you can verify together, out loud, in ten seconds.</p>` : ''}

<h3>The seven lamps are the only things you may say out loud</h3>
<p>Works on a phone · secure · load speed · tap-to-call · Google markup · title and description · shareable preview. Those seven can be demonstrated to an owner while they hold their own phone. The other five we track — hours, address, services, reviews, call-to-action — are recorded but <strong>never claimed</strong>, because a page scan cannot prove them. We once told a florist she had no hours while she was looking at her hours.</p>

<h3>${zero.length} score zero, ${nearlyFine.length} score five or better — treat them oppositely</h3>
<p>A <strong>0/7</strong> is the easy call: nothing works, and you can prove it in ten seconds while they hold the phone. A <strong>5/7 or better is not a rebuild.</strong> RT Roofing passes six of seven; the honest sale there was $450 to fix the load time, not $750 to replace a site that works. Quoting a rebuild to someone whose site is fine is how you become the guy who calls.</p>

${trades.length ? `<h3>Where the gaps actually are</h3>
<ul>${trades.map(([k, n, g]) => `<li><strong>${esc(k)}</strong> — ${n} callable, ${g} of 7 checks failing on average</li>`).join('')}</ul>
<p>Weight your day toward the top of that list. Businesses whose whole product is how things look — salons, florists, boutiques — usually already have someone doing their website, and the hit rate there has been poor.</p>` : ''}

${noNumber.length ? `<h3>${noNumber.length} are filtered out only for a missing number — they are not dead</h3>
<p>OpenStreetMap simply has no phone tag for them. Everything else about them stands, including the audit. One Google search recovers the number, and several of them score badly enough to be worth that search. Treat that group as a reserve list for a day when the main list runs dry, not as rejects.</p>` : ''}

${derived.length ? `<h3>${derived.length} states were read off the area code</h3>
<p>Those rows show the state with an asterisk. The listing did not say where they were, so it came from the first three digits of the number — reliable, but not the same as the listing telling us. Numbers do follow people who move, so if a call opens with confusion about the city, that is why.</p>` : ''}

<h3>Delaware is thin, and you should plan around that</h3>
<p>The Delaware sweep covered Wilmington, the Felton–Camden–Dover corridor and Milford, and returned barely a dozen usable businesses. That is not a bug in the search — <strong>Felton has about 1,300 people</strong>, and OpenStreetMap's coverage of small-town Delaware is far patchier than its coverage of San Diego. Two consequences: do not build a calling day around Delaware, and if you want real depth there, the listings have to come from Google Places rather than OSM, which costs a little and needs an API key.</p>

<h3>Call when they can actually talk</h3>
<p>Clinics answer <strong>9–11am</strong>, before the room fills. Trades answer <strong>7–8am and after 4pm</strong>, from the van. Restaurants are unreachable 11:30–2 and after 5. Three of the calls logged at 5pm last week went to voicemail, all of them to businesses that answer in the morning. The board does not know the time; you do.</p>

<h3>Four strikes and stop</h3>
<p>El Cajon has had six attempts. After four, a lead is not shy, it is a no — close it out or walk in. The pipeline is worth more when it is honest about what is dead.</p>`;
};
