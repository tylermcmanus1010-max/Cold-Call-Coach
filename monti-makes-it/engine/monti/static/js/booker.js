/* The consultation picker (CHG-021).
 *
 * The server sends every bookable slot as a UTC timestamp. It does NOT send a
 * pre-built calendar, because which day a slot falls on depends on the viewer's
 * timezone: 2026-09-02 01:30 UTC is Tuesday night in London and Tuesday
 * afternoon in Los Angeles. Grouping into days server-side would put slots on
 * the wrong date for anyone far from the host, and it is the kind of wrong that
 * looks right until someone misses a call.
 *
 * So the grouping happens here, in the zone the visitor picked, and re-runs when
 * they change it. The server still re-checks the chosen slot on submit — this
 * file only decides what is easy to click, never what is allowed.
 */
(function () {
  "use strict";
  var data = document.getElementById("bkData");
  if (!data) return;                       // nothing published; the fallback field stands

  var SLOTS = JSON.parse(data.textContent);          // [{t: "...Z", m: 30}, ...]
  var grid = document.getElementById("bkGrid");
  var times = document.getElementById("bkTimes");
  var monthLabel = document.getElementById("bkMonth");
  var chosenLine = document.getElementById("bkChosen");
  var hidden = document.getElementById("bkSlot");
  var tzSelect = document.getElementById("bkTz");
  var tzName = document.getElementById("tzName");
  var channel = document.getElementById("bkChannel");
  var phoneField = document.getElementById("bkPhoneField");
  var phone = document.getElementById("bkPhone");

  var tz = tzSelect.value;
  var cursor = null;        // {y, m} of the month on screen
  var pickedDay = null;     // "YYYY-MM-DD" in tz
  var picked = null;        // the raw UTC string

  // The browser knows where it is. Offer that first rather than making someone
  // find their own city in a list of forty.
  try {
    var detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (detected) {
      if (!Array.prototype.some.call(tzSelect.options, function (o) { return o.value === detected; })) {
        var opt = document.createElement("option");
        opt.value = detected; opt.textContent = detected.replace(/_/g, " ");
        tzSelect.insertBefore(opt, tzSelect.firstChild);
      }
      tzSelect.value = detected; tz = detected;
    }
  } catch (e) { /* keep the server's default */ }

  function parts(iso, zone) {
    var d = new Date(iso);
    var f = new Intl.DateTimeFormat("en-CA", {
      timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false });
    var out = {};
    f.formatToParts(d).forEach(function (p) { out[p.type] = p.value; });
    return { date: out.year + "-" + out.month + "-" + out.day,
             time: out.hour + ":" + out.minute, d: d };
  }

  function group() {
    var days = {};
    SLOTS.forEach(function (s) {
      var p = parts(s.t, tz);
      (days[p.date] = days[p.date] || []).push({ t: s.t, m: s.m, label: p.time, d: p.d });
    });
    Object.keys(days).forEach(function (k) {
      days[k].sort(function (a, b) { return a.d - b.d; }); });
    return days;
  }

  function humanTime(iso) {
    return new Date(iso).toLocaleString(undefined, {
      timeZone: tz, weekday: "long", day: "numeric", month: "long",
      hour: "numeric", minute: "2-digit" });
  }

  function render() {
    var days = group();
    var keys = Object.keys(days).sort();
    if (!keys.length) { grid.textContent = ""; return; }
    if (!cursor) {
      var first = keys[0].split("-");
      cursor = { y: +first[0], m: +first[1] - 1 };
    }

    var shown = new Date(Date.UTC(cursor.y, cursor.m, 1));
    monthLabel.textContent = shown.toLocaleString(undefined, {
      timeZone: "UTC", month: "long", year: "numeric" });

    // Monday-first, matching the day header.
    var lead = (new Date(Date.UTC(cursor.y, cursor.m, 1)).getUTCDay() + 6) % 7;
    var count = new Date(Date.UTC(cursor.y, cursor.m + 1, 0)).getUTCDate();

    grid.textContent = "";
    for (var i = 0; i < lead; i++) {
      var pad = document.createElement("span");
      pad.className = "bk-day bk-pad"; pad.setAttribute("aria-hidden", "true");
      grid.appendChild(pad);
    }
    for (var d = 1; d <= count; d++) {
      var key = cursor.y + "-" + pad2(cursor.m + 1) + "-" + pad2(d);
      var open = days[key];
      var cell = document.createElement("button");
      cell.type = "button";
      cell.className = "bk-day" + (open ? " has" : "") + (key === pickedDay ? " on" : "");
      cell.textContent = d;
      if (open) {
        cell.setAttribute("aria-label", d + " — " + open.length +
          (open.length === 1 ? " time" : " times") + " free");
        cell.dataset.day = key;
        cell.addEventListener("click", function () { pickDay(this.dataset.day); });
      } else {
        cell.disabled = true;
      }
      grid.appendChild(cell);
    }

    var earliest = keys[0], latest = keys[keys.length - 1];
    document.getElementById("bkPrev").disabled =
      monthKey(cursor) <= earliest.slice(0, 7);
    document.getElementById("bkNext").disabled =
      monthKey(cursor) >= latest.slice(0, 7);

    if (pickedDay && days[pickedDay]) { showTimes(days[pickedDay]); }
    else { times.textContent = ""; }
  }

  function monthKey(c) { return c.y + "-" + pad2(c.m + 1); }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function pickDay(key) {
    pickedDay = key;
    picked = null; hidden.value = "";
    chosenLine.textContent = "No time picked yet.";
    chosenLine.classList.remove("on");
    render();
  }

  function showTimes(list) {
    times.textContent = "";
    var head = document.createElement("span");
    head.className = "bk-times-head";
    head.textContent = new Date(list[0].t).toLocaleDateString(undefined, {
      timeZone: tz, weekday: "long", day: "numeric", month: "long" });
    times.appendChild(head);
    list.forEach(function (s) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "bk-time" + (s.t === picked ? " on" : "");
      b.textContent = s.label;
      b.appendChild(Object.assign(document.createElement("em"), {
        textContent: s.m + " min" }));
      b.addEventListener("click", function () {
        picked = s.t; hidden.value = s.t;
        chosenLine.textContent = humanTime(s.t) + " · " + s.m + " minutes · " +
          tz.replace(/_/g, " ");
        chosenLine.classList.add("on");
        showTimes(list);
      });
      times.appendChild(b);
    });
  }

  document.getElementById("bkPrev").addEventListener("click", function () {
    cursor = { y: cursor.m === 0 ? cursor.y - 1 : cursor.y,
               m: cursor.m === 0 ? 11 : cursor.m - 1 };
    render();
  });
  document.getElementById("bkNext").addEventListener("click", function () {
    cursor = { y: cursor.m === 11 ? cursor.y + 1 : cursor.y,
               m: cursor.m === 11 ? 0 : cursor.m + 1 };
    render();
  });

  tzSelect.addEventListener("change", function () {
    tz = tzSelect.value;
    if (tzName) tzName.textContent = tz;
    // A slot keeps its UTC identity across a zone change; only its label moves.
    // Clearing the picked DAY is still right, because the same slot can land on
    // a different date once the zone changes.
    if (picked) {
      pickedDay = parts(picked, tz).date;
      var first = pickedDay.split("-");
      cursor = { y: +first[0], m: +first[1] - 1 };
      chosenLine.textContent = humanTime(picked) + " · " + tz.replace(/_/g, " ");
    }
    render();
  });

  function syncChannel() {
    var isPhone = channel.value === "phone";
    phoneField.hidden = !isPhone;
    if (phone) phone.required = isPhone;
  }
  channel.addEventListener("change", syncChannel);
  syncChannel();
  if (tzName) tzName.textContent = tz;
  render();
}());
