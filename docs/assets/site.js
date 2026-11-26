// cronoaudit website: the copy buttons, and respect for "reduce motion". Nothing else:
// no tracking, no storage, no request.
(function () {
  "use strict";
  document.querySelectorAll("button.copy").forEach(function (b) {
    var label = b.textContent;
    b.addEventListener("click", function () {
      var text = document.getElementById(b.dataset.copy).textContent;
      var done = function () {
        b.textContent = b.dataset.done; b.classList.add("done");
        setTimeout(function () { b.textContent = label; b.classList.remove("done"); }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var r = document.createRange(); r.selectNodeContents(document.getElementById(b.dataset.copy));
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        try { if (document.execCommand("copy")) done(); } catch (e) {}
        s.removeAllRanges();
      }
    });
  });
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("video[autoplay]").forEach(function (v) { v.removeAttribute("autoplay"); v.pause(); });
  }
})();
