/* The item image viewer (§10.3).
 *
 * One behaviour for every surface that shows an item. Written without a
 * framework and without a build step because the rest of the engine is server
 * rendered, and a viewer that needs a bundler to open a photograph is a
 * liability on the day someone has to change it.
 *
 * Mobile is the first case, not the fallback: a member opens this in a
 * warehouse, on a phone, one-handed. So swipe moves between images, double-tap
 * zooms, and every control is at least 44px. Pointer and keyboard get the same
 * capability through the toolbar and arrow keys — §12.2 requires the viewer to
 * be captured working on touch *and* pointer, which only holds if neither is
 * the afterthought.
 */
(function () {
  "use strict";

  var ZOOM_STEPS = [1, 1.75, 3];

  function setup(root) {
    var dialog = root.querySelector(".iv-dialog");
    if (!dialog) { return; }                       // an empty state — nothing to wire

    var slides = Array.prototype.slice.call(root.querySelectorAll(".iv-slide"));
    var nowEl = root.querySelector(".iv-now");
    var diagramBtn = root.querySelector(".iv-diagram");
    var index = 0;
    var zoom = 0;
    var opener = null;                              // focus goes back here on close

    function render() {
      slides.forEach(function (slide, i) { slide.hidden = i !== index; });
      if (nowEl) { nowEl.textContent = String(index + 1); }
      applyZoom();
      drawCallouts();
      // A diagram layer is only offered on images that actually carry callouts,
      // so the control never promises something the image cannot do.
      if (diagramBtn) { diagramBtn.hidden = !slides[index].dataset.annotations; }
    }

    function applyZoom() {
      var media = slides[index].querySelector(".iv-media");
      if (!media) { return; }
      media.style.transform = "scale(" + ZOOM_STEPS[zoom] + ")";
      media.style.cursor = zoom < ZOOM_STEPS.length - 1 ? "zoom-in" : "zoom-out";
    }

    function move(delta) {
      index = (index + delta + slides.length) % slides.length;
      zoom = 0;                                     // a new image starts unzoomed
      render();
    }

    function zoomBy(delta) {
      zoom = Math.max(0, Math.min(ZOOM_STEPS.length - 1, zoom + delta));
      applyZoom();
    }

    /* The annotated diagram layer (§10.5).
     *
     * Callouts are drawn *outside* the subject with a leader line pointing at
     * it, rather than as a label on top of it. A callout that covers the thing
     * it names is worse than no callout, and at 320px a label placed over a
     * print area covers most of the print area.
     */
    function drawCallouts() {
      var slide = slides[index];
      var svg = slide.querySelector(".iv-callouts");
      if (!svg) { return; }
      var raw = slide.dataset.annotations;
      var on = diagramBtn && diagramBtn.getAttribute("aria-pressed") === "true";
      if (!raw || !on) { svg.hidden = true; svg.innerHTML = ""; return; }

      var notes;
      try { notes = JSON.parse(raw); } catch (e) { svg.hidden = true; return; }
      if (!Array.isArray(notes) || !notes.length) { svg.hidden = true; return; }

      var parts = notes.map(function (note) {
        // x/y are percentages of the image box: the point being named.
        var x = Number(note.x) || 50, y = Number(note.y) || 50;
        // Push the label to whichever side has more room, so it lands on the
        // canvas rather than off the edge at a narrow viewport.
        var toLeft = x > 50;
        var lx = toLeft ? Math.max(2, x - 26) : Math.min(98, x + 26);
        var anchor = toLeft ? "end" : "start";
        return (
          '<line x1="' + x + '" y1="' + y + '" x2="' + lx + '" y2="' + y + '" />' +
          '<circle cx="' + x + '" cy="' + y + '" r="1.1" />' +
          '<text x="' + lx + '" y="' + (y - 1.6) + '" text-anchor="' + anchor + '">' +
          String(note.label || "").replace(/[<&>]/g, "") + "</text>"
        );
      });
      svg.innerHTML = parts.join("");
      svg.hidden = false;
    }

    function open(i, from) {
      index = i;
      zoom = 0;
      opener = from || null;
      dialog.hidden = false;
      document.body.classList.add("iv-open");
      render();
      var close = dialog.querySelector(".iv-close");
      if (close) { close.focus(); }
    }

    function close() {
      dialog.hidden = true;
      document.body.classList.remove("iv-open");
      // Focus returns to the thumbnail that opened the dialog. Dropping focus
      // on the body sends a keyboard user back to the top of the document,
      // which on a long catalogue page loses their place entirely.
      if (opener) { opener.focus(); }
    }

    root.querySelectorAll(".iv-thumb").forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        open(Number(thumb.dataset.index) || 0, thumb);
      });
    });

    dialog.querySelector(".iv-close").addEventListener("click", close);
    dialog.querySelector(".iv-prev").addEventListener("click", function () { move(-1); });
    dialog.querySelector(".iv-next").addEventListener("click", function () { move(1); });
    dialog.querySelector(".iv-in").addEventListener("click", function () { zoomBy(1); });
    dialog.querySelector(".iv-out").addEventListener("click", function () { zoomBy(-1); });
    if (diagramBtn) {
      diagramBtn.addEventListener("click", function () {
        var on = diagramBtn.getAttribute("aria-pressed") === "true";
        diagramBtn.setAttribute("aria-pressed", on ? "false" : "true");
        drawCallouts();
      });
    }

    dialog.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { close(); }
      else if (e.key === "ArrowRight") { move(1); }
      else if (e.key === "ArrowLeft") { move(-1); }
      else if (e.key === "+" || e.key === "=") { zoomBy(1); }
      else if (e.key === "-") { zoomBy(-1); }
      else if (e.key === "0") { zoom = 0; applyZoom(); }
      else { return; }
      e.preventDefault();
    });

    // Keep Tab inside the dialog while it is open, but never without an exit:
    // Escape always closes, so this is a loop rather than a trap.
    dialog.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") { return; }
      var focusable = dialog.querySelectorAll("button:not([hidden])");
      if (!focusable.length) { return; }
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
    });

    // --- touch: swipe between images, double-tap to zoom --------------------
    var startX = 0, startY = 0, startT = 0, lastTap = 0;
    var stage = dialog.querySelector(".iv-stage");

    stage.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 1) { return; }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      startT = Date.now();
    }, { passive: true });

    stage.addEventListener("touchend", function (e) {
      var t = e.changedTouches[0];
      var dx = t.clientX - startX, dy = t.clientY - startY;
      var elapsed = Date.now() - startT;

      // A horizontal flick, not a vertical scroll and not a slow drag.
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5 && elapsed < 600) {
        move(dx < 0 ? 1 : -1);
        return;
      }
      if (Math.abs(dx) < 12 && Math.abs(dy) < 12) {
        var now = Date.now();
        if (now - lastTap < 320) {                  // double tap cycles the zoom
          zoom = (zoom + 1) % ZOOM_STEPS.length;
          applyZoom();
          lastTap = 0;
        } else {
          lastTap = now;
        }
      }
    }, { passive: true });

    render();
  }

  function init() {
    document.querySelectorAll("[data-iv]").forEach(setup);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
