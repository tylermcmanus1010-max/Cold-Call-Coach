/* CHG-030 — pass the site to someone else.
 *
 * Copies the page's own address and nothing else. No member id, no session
 * token, no referral code identifying the sender: a shared link is a link, and
 * a link that quietly says who sent it is a tracker.
 *
 * Uses the platform share sheet where there is one — on a phone that is what
 * people expect — and falls back to the clipboard, and to a selectable input
 * where neither is available. */
(function () {
  function tell(btn, text) {
    var was = btn.textContent;
    btn.textContent = text;
    setTimeout(function () { btn.textContent = was; }, 2200);
  }
  document.querySelectorAll("[data-share]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var url = location.origin + location.pathname;   // no query, no fragment
      var title = btn.getAttribute("data-share-title") || document.title;
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () {});
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(
          function () { tell(btn, "Link copied"); },
          function () { tell(btn, url); });
        return;
      }
      window.prompt("Copy this link", url);
    });
  });
})();
