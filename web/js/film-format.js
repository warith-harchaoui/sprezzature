/* Swap one film between its three canvases.
 *
 * Each film is cut wide, tall and square off a single composition, so the
 * three are the same minute with a different layout: the same sentence lands
 * on the same second in all of them. Switching therefore keeps the playhead
 * where it was, which is the whole reason the three are frame-synced.
 *
 * Landscape is the unsuffixed file (`maps.en.mp4`) because the home page, the
 * Open Graph tags, the sitemap and the feed all name it that way. The other
 * two carry their canvas: `maps.en.portrait.mp4`.
 *
 * No framework, per the house rule, and nothing runs until a button is
 * pressed: the players are `preload="none"` and a visitor who never touches
 * this control never fetches a byte of video.
 */
(function () {
  "use strict";

  var SUFFIX = { landscape: "", portrait: ".portrait", square: ".square" };
  var SIZE = {
    landscape: [3840, 2160],
    portrait: [2160, 3840],
    square: [2160, 2160]
  };

  function swap(group, format) {
    var player = group.parentNode.querySelector("[data-film-player]");
    if (!player || !Object.prototype.hasOwnProperty.call(SUFFIX, format)) return;

    var stem =
      group.getAttribute("data-dir") + "/" +
      group.getAttribute("data-film") + "." +
      group.getAttribute("data-lang");
    var src = stem + SUFFIX[format] + ".mp4";
    var source = player.querySelector("source");
    if (source.getAttribute("src") === src) return;

    // Keep the second the viewer was on. `load()` resets currentTime, so the
    // position is read before and written back once the new file knows its
    // own duration.
    var at = player.currentTime;
    var playing = !player.paused && !player.ended;

    source.setAttribute("src", src);
    player.setAttribute("poster", stem + SUFFIX[format] + ".jpg");
    player.setAttribute("width", SIZE[format][0]);
    player.setAttribute("height", SIZE[format][1]);
    // The download link in the fallback paragraph points at the same cut.
    var dl = player.querySelector("a[href]");
    if (dl) dl.setAttribute("href", src);

    player.load();
    if (at > 0) {
      player.addEventListener("loadedmetadata", function once() {
        player.removeEventListener("loadedmetadata", once);
        try { player.currentTime = at; } catch (e) { /* out of range */ }
        if (playing) { var p = player.play(); if (p && p.catch) p.catch(function () {}); }
      });
    }

    var buttons = group.querySelectorAll("button[data-format]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute(
        "aria-pressed",
        buttons[i].getAttribute("data-format") === format ? "true" : "false"
      );
    }
  }

  var groups = document.querySelectorAll("[data-film-formats]");
  for (var g = 0; g < groups.length; g++) {
    (function (group) {
      group.addEventListener("click", function (event) {
        var button = event.target.closest
          ? event.target.closest("button[data-format]")
          : null;
        if (button && group.contains(button)) {
          swap(group, button.getAttribute("data-format"));
        }
      });
    })(groups[g]);
  }
})();
