/* The question box (CHG-029).
 *
 * Two behaviours worth naming.
 *
 * It stays shut. Closing it writes a flag to sessionStorage, and every page
 * after that opens closed. A helper that pops back up on the next page has
 * stopped being help.
 *
 * It never invents. The reply and the links come from the server, which
 * searches the site's own published text; this file renders what it is given
 * and nothing else. If the request fails it says the request failed — it does
 * not fall back to a guess.
 */
(function () {
  "use strict";
  var root = document.getElementById("ask");
  if (!root) return;

  var panel = document.getElementById("askPanel");
  var openBtn = document.getElementById("askOpen");
  var closeBtn = document.getElementById("askClose");
  var form = document.getElementById("askForm");
  var input = document.getElementById("askInput");
  var log = document.getElementById("askLog");
  var KEY = "monti.ask.dismissed";

  function dismissed() {
    try { return sessionStorage.getItem(KEY) === "1"; } catch (e) { return false; }
  }
  function remember() {
    try { sessionStorage.setItem(KEY, "1"); } catch (e) { /* private window */ }
  }

  function setOpen(open) {
    panel.hidden = !open;
    openBtn.setAttribute("aria-expanded", String(open));
    openBtn.hidden = open;
    root.classList.toggle("open", open);
    if (open) input.focus();
  }

  setOpen(root.dataset.open === "1" && !dismissed());

  openBtn.addEventListener("click", function () { setOpen(true); });
  closeBtn.addEventListener("click", function () { setOpen(false); remember(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !panel.hidden) { setOpen(false); remember(); }
  });

  function say(text, mine) {
    var p = document.createElement("p");
    p.className = "ask-msg " + (mine ? "ask-me" : "ask-them");
    p.textContent = text;
    log.appendChild(p);
    log.scrollTop = log.scrollHeight;
    return p;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    say(q, true);
    input.value = "";
    var waiting = say("…", false);

    var body = new FormData(form);
    body.set("q", q);
    fetch(form.action, { method: "POST", body: body, headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(r.status)); })
      .then(function (data) {
        waiting.textContent = data.reply;
        if (data.links && data.links.length) {
          var nav = document.createElement("p");
          nav.className = "ask-links";
          data.links.forEach(function (l) {
            var a = document.createElement("a");
            a.href = l.url;
            a.textContent = l.title;
            a.title = l.where;
            nav.appendChild(a);
          });
          log.appendChild(nav);
        }
        log.scrollTop = log.scrollHeight;
      })
      .catch(function () {
        waiting.textContent =
          "That did not reach us — the request failed. Try again, or use the "
          + "contact page, which does not depend on this working.";
      });
  });
}());
