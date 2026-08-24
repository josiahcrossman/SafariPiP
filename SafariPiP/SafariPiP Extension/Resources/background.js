// SafariPiP — background service worker.
//
// On toolbar-button click or the ⌘⇧P command, inject pip.js into every frame
// of the active tab. Each frame independently reports whether it toggled a
// video. If no frame found one, flash a "?" badge so the click isn't silent.

async function triggerPiP(tab) {
  if (!tab || tab.id == null) return;

  let results;
  try {
    results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      files: ["pip.js"],
    });
  } catch (err) {
    // Most commonly: activeTab not granted (e.g. command fired with no focus)
    // or a restricted page (Safari settings, empty tab).
    await flashBadge(tab.id, "!");
    return;
  }

  const toggled = results.some((r) => r && r.result && r.result.toggled);
  if (!toggled) {
    await flashBadge(tab.id, "?");
  }
}

async function flashBadge(tabId, text) {
  try {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: "#c0392b" });
    await chrome.action.setBadgeText({ tabId, text });
    setTimeout(() => {
      chrome.action.setBadgeText({ tabId, text: "" }).catch(() => {});
    }, 1500);
  } catch (_) {
    // Badge is best-effort; ignore if the tab is gone.
  }
}

chrome.action.onClicked.addListener((tab) => {
  triggerPiP(tab);
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "toggle-pip") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  triggerPiP(tab);
});
