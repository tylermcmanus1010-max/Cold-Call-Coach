// Turns a found contact form into something ready to send.
//
// The message has to survive being read by a receptionist in four seconds, so
// it says one checkable thing and makes one small ask. Every claim in it comes
// from the seven hard checks; the five soft ones never appear, because a page
// scan cannot prove them and this arrives in writing where a wrong claim sits
// on the record.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const ME = {
  name: 'Tyler McManus',
  business: 'McManus Web Co.',
  phone: '302-649-6600',
  email: 'tylermcmanus1010@gmail.com',
  home: 'San Diego',
};

// The opening line, per finding. Written so the reader can check it on the
// phone already in their hand — that is what makes it land rather than read
// as flattery or a threat.
function finding(row) {
  if (row.parked) {
    return `Your domain doesn't currently point at a website — it lands on a placeholder page offering the name for sale. Anyone typing your business name plus dot-com sees that instead of you.`;
  }
  const a = row.audit || {};
  if (a.mobile === false) {
    return `I opened ${short(row.site)} on a phone and the layout breaks — text runs off the side and you have to pinch to read it. Worth trying on your own phone.`;
  }
  if (a.https === false) {
    return `${short(row.site)} isn't on HTTPS, so Chrome and Safari show visitors a "Not secure" warning before they read a word of it.`;
  }
  if (a.speed === false) {
    return `${short(row.site)} took a long time to load on a phone on mobile data. Time it yourself — most people give a site a couple of seconds before going back to the search results.`;
  }
  if (a.phoneTap === false) {
    return `On a phone, your number on ${short(row.site)} is text rather than a button — someone has to memorise it and switch apps instead of just tapping it.`;
  }
  if (a.social === false) {
    return `When someone texts a link to ${short(row.site)}, it arrives as a plain grey box with no name or picture on it.`;
  }
  if (a.meta === false) {
    return `${short(row.site)} has no page title or description set, so Google is guessing what to print underneath your name in the results.`;
  }
  if (a.seo === false) {
    return `${short(row.site)} has no business markup on it, so Google has nothing structured to read about your hours or location.`;
  }
  return null;
}

// OSM category names are not what a person calls their own trade. "dry
// cleaning" plus an s is "dry cleanings", which reads as written by a machine
// in the first line of a cold message.
const TRADE = [
  [/dry.?clean|laundry/i, 'dry cleaners'],
  [/hairdress|hair salon|barber/i, 'barbers and salons'],
  [/beauty|nail|lash|cosmetic stud/i, 'salons'],
  [/massage|spa(?!ce)/i, 'spas'],
  [/car repair|car_repair|auto|transmission|body shop|smog|tyre|tire/i, 'auto shops'],
  [/car wash/i, 'car washes'],
  [/bakery|baker|patisserie/i, 'bakeries'],
  [/butcher/i, 'butchers'],
  [/florist/i, 'florists'],
  [/dentist|dental/i, 'dental practices'],
  [/doctor|medical|clinic/i, 'clinics'],
  [/veterin|vet\b/i, 'vets'],
  [/optician/i, 'opticians'],
  [/fitness|gym|yoga|dojo/i, 'gyms and studios'],
  [/lawyer|law|attorney/i, 'law firms'],
  [/account/i, 'accountants'],
  [/insurance/i, 'insurance offices'],
  [/estate agent|realtor|real estate/i, 'estate agents'],
  [/plumb/i, 'plumbers'],
  [/roof/i, 'roofers'],
  [/electric/i, 'electricians'],
  [/hvac|heating|air condition/i, 'HVAC companies'],
  [/upholster/i, 'upholsterers'],
  [/locksmith/i, 'locksmiths'],
  [/shoe repair|cobbler/i, 'cobblers'],
  [/pet groom|pet/i, 'pet groomers'],
  [/caterer|catering/i, 'caterers'],
  [/driving school/i, 'driving schools'],
  [/contractor|construct|carpenter|painter|floor|tiler|window|metal/i, 'trades'],
];
function tradeNoun(category) {
  const c = String(category || '');
  const hit = TRADE.find(([re]) => re.test(c));
  if (hit) return hit[1];
  const c2 = c.toLowerCase().trim();
  if (!c2) return 'local businesses';
  return /s$/.test(c2) ? c2 : `${c2}s`;
}

const short = (u) => String(u || '').replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');

function message(row) {
  const f = finding(row);
  if (!f) return null;

  const trade = tradeNoun(row.category);
  // "A local business" is true in San Diego and false in Milwaukee. Saying it
  // anyway is the kind of small lie that gets noticed and ends the call.
  const where = row.state === 'CA'
    ? `I build one-page websites for ${trade} here in ${ME.home}.`
    : `I build one-page websites for ${trade}. I'm in ${ME.home}, so this is a cold one — ${row.city || 'your town'} came up in a check I run.`;

  return [
    `Hi — I'm ${ME.name.split(' ')[0]}. ${where} If this isn't the right person, please pass it along.`,
    ``,
    f,
    ``,
    row.built
      ? `I build one sample page a week and I've already done yours — a single fast page with your services and a tap-to-call button. There's no charge for looking at it and nothing owed either way. Can I send it over so you can see it on your phone?`
      : `I build one sample page a week for a business I've looked at, free, and yours is on my list. A single fast page with your services and a tap-to-call button, nothing owed either way. Want me to do it and send it over?`,
    ``,
    `${ME.name}`,
    `${ME.business}`,
    `${ME.phone}`,
  ].join('\n');
}

// A text is the best channel a desk job allows: it takes ten seconds, nobody
// looks up, and most tradesmen would rather be texted than called. It has to
// be short enough to read in the notification, so it carries the finding and
// nothing else.
//
// This is a business-to-business message to a number the business publishes,
// sent once, identifying who is sending it — which is the line that separates
// it from the kind of texting that is illegal as well as rude. One message. If
// anyone asks not to be texted again, that is the end of it.
function sms(row) {
  const f = smsFinding(row);
  if (!f) return null;
  const body = `Hi, this is Tyler McManus — I build one-page websites (McManus Web Co, San Diego). ${f} I do one free sample a week and can do yours, nothing owed either way. Worth a look? Reply STOP and I won't message again.`;
  return body.length > 480 ? body.slice(0, 477) + '...' : body;
}

function smsFinding(row) {
  if (row.parked) return `Your domain lands on a for-sale placeholder rather than a website, so anyone Googling you sees that.`;
  const a = row.audit || {};
  if (a.mobile === false) return `Your site's layout breaks on a phone — worth pulling up on yours.`;
  if (a.https === false) return `Your site isn't on HTTPS, so phones show a "Not secure" warning first.`;
  if (a.speed === false) return `Your site is slow to load on mobile data — worth timing on your own phone.`;
  if (a.phoneTap === false) return `Your number on the site isn't tappable on a phone, so people have to memorise it.`;
  if (a.social === false) return `When someone texts your link it arrives as a blank grey box.`;
  if (a.meta === false) return `Your site has no title set, so Google is guessing what to show under your name.`;
  return null;
}

// Which of our details goes in which of their boxes.
function mapFields(form) {
  if (!form) return [];
  return form.fields.map((fld) => {
    const hay = `${fld.name} ${fld.label}`.toLowerCase();
    let value = null;
    if (/e-?mail/.test(hay)) value = ME.email;
    else if (/phone|tel|mobile|number/.test(hay)) value = ME.phone;
    else if (/first.?name|fname/.test(hay)) value = ME.name.split(' ')[0];
    else if (/last.?name|lname|surname/.test(hay)) value = ME.name.split(' ')[1];
    else if (/name|who/.test(hay)) value = ME.name;
    else if (/compan|business|organi/.test(hay)) value = ME.business;
    else if (/subject|regarding|topic/.test(hay)) value = 'Your website — one thing I noticed';
    else if (fld.tag === 'textarea' || /message|comment|detail|question|enquir|inquir|note/.test(hay)) value = '{{MESSAGE}}';
    else if (/zip|postal/.test(hay)) value = '92101';
    else if (/city|town/.test(hay)) value = ME.home;
    return { ...fld, value };
  });
}

function build(rows, forms) {
  const byName = new Map(forms.map((f) => [f.name, f]));
  const queue = [];
  const skipped = [];

  for (const r of rows) {
    const f = byName.get(r.name);
    if (!f) continue;

    // On the phone he can say "is that your site?" and correct it in the same
    // breath. In writing it is on the record — and this exact flag is the one
    // that caught House of Stemms pointing at a rival florist's page.
    if (r.checkUrl) { skipped.push({ name: r.name, why: 'the domain may not be theirs — confirm by phone first' }); continue; }
    if (f.noSolicit) { skipped.push({ name: r.name, why: 'their page asks for no soliciting' }); continue; }
    if (f.error) { skipped.push({ name: r.name, why: f.error }); continue; }
    const body = message(r);
    if (!body) { skipped.push({ name: r.name, why: 'nothing provable to say' }); continue; }

    const text = r.phone ? sms(r) : null;
    const published = f.published || [];
    const usableForm = Boolean(f.form && f.form.hasTextarea);

    if (!usableForm && !published.length && !text) {
      skipped.push({ name: r.name, why: 'no form, no published address and no number — nothing to send to' });
      continue;
    }

    // Best channel first, judged by what actually gets read. A text reaches
    // the owner; a published address reaches a real inbox; a form reaches
    // whoever checks the form, and 14 of the first 17 we found sat behind a
    // CAPTCHA, so it is the fallback rather than the plan.
    const channel = text ? 'text' : published.length ? 'email' : 'form';

    queue.push({
      name: r.name,
      phone: r.phone,
      where: [r.city, r.state].filter(Boolean).join(', '),
      category: r.category,
      site: r.site,
      formUrl: usableForm ? f.url : null,
      foundOn: f.foundOn,
      captcha: f.captcha,
      usableForm,
      channel,
      published,
      booker: f.booker || [],
      score: r.parked ? null : r.passed,
      flaw: r.flaw ? r.flaw.label : null,
      fields: usableForm ? mapFields(f.form) : [],
      submitText: usableForm ? f.form.submitText : '',
      message: body,
      sms: text,
    });
  }

  // A form that needs a CAPTCHA needs him present, so put the ones that do not
  // at the top — those are the ones that can be worked through in one sitting.
  const RANK = { text: 0, email: 1, form: 2 };
  queue.sort((a, b) => RANK[a.channel] - RANK[b.channel] || (a.score ?? -1) - (b.score ?? -1));
  return { queue, skipped };
}

module.exports = { build, message, sms, finding, mapFields, tradeNoun, ME };
