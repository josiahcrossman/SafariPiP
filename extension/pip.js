// SafariPiP — injected per-frame by background.js via chrome.scripting.
//
// Finds the best <video> in this frame, strips any disablePictureInPicture
// block, and toggles Picture-in-Picture. Returns { toggled: bool } as the
// injection result so the background can flash a "?" badge when no frame
// managed to act.
//
// Written as a self-invoking expression: chrome.scripting.executeScript with
// `files` uses the value of the file's final expression as the result.

(() => {
  const isVisible = (v) => {
    const r = v.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) return false;
    const style = getComputedStyle(v);
    return style.visibility !== "hidden" && style.display !== "none" && style.opacity !== "0";
  };

  const area = (v) => {
    const r = v.getBoundingClientRect();
    return r.width * r.height;
  };

  const inPiP = (v) =>
    document.pictureInPictureElement === v ||
    (typeof v.webkitPresentationMode === "string" &&
      v.webkitPresentationMode === "picture-in-picture");

  const videos = Array.from(document.querySelectorAll("video"));
  if (videos.length === 0) return { toggled: false };

  // If something is already in PiP, toggling means exiting it.
  const active = videos.find(inPiP);
  if (active) {
    exitPiP(active);
    return { toggled: true };
  }

  // Otherwise pick the best candidate: visible, prefer playing, then largest.
  const candidates = videos.filter(isVisible);
  const pool = candidates.length ? candidates : videos;

  pool.sort((a, b) => {
    const aPlaying = !a.paused && !a.ended ? 1 : 0;
    const bPlaying = !b.paused && !b.ended ? 1 : 0;
    if (aPlaying !== bPlaying) return bPlaying - aPlaying;
    return area(b) - area(a);
  });

  const video = pool[0];
  if (!video) return { toggled: false };

  enterPiP(video);
  return { toggled: true };

  function enterPiP(v) {
    // Some sites (Disney+, etc.) set this to hide/deny PiP. Clear it first.
    try {
      v.disablePictureInPicture = false;
      v.removeAttribute("disablePictureInPicture");
      v.removeAttribute("disablepictureinpicture");
    } catch (_) {}

    // Safari's native API is the most reliable inside an extension.
    if (typeof v.webkitSetPresentationMode === "function") {
      try {
        v.webkitSetPresentationMode("picture-in-picture");
        return;
      } catch (_) {}
    }
    if (typeof v.requestPictureInPicture === "function") {
      v.requestPictureInPicture().catch(() => {});
    }
  }

  function exitPiP(v) {
    if (typeof v.webkitSetPresentationMode === "function") {
      try {
        v.webkitSetPresentationMode("inline");
        return;
      } catch (_) {}
    }
    if (document.exitPictureInPicture) {
      document.exitPictureInPicture().catch(() => {});
    }
  }
})();
