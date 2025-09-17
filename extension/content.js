// Content script injected on the Workspace dashboard (localhost dev)
// Listens for CustomEvents from the page and forwards them to the extension background

(function () {
  try {
    window.addEventListener('focusguard:lock-url', (e) => {
      const url = e?.detail?.url;
      if (!url) return;
      try {
        chrome.runtime?.sendMessage({ type: 'lock-url', url });
      } catch (_) {}
    });

    window.addEventListener('focusguard:unlock', () => {
      try {
        chrome.runtime?.sendMessage({ type: 'unlock-domain' });
      } catch (_) {}
    });

    // Enable/disable enforcement from dashboard
    window.addEventListener('focusguard:enable', () => {
      try {
        chrome.storage.sync.set({ enabled: true });
        chrome.runtime?.sendMessage({ type: 'update-rules', enabled: true });
      } catch (_) {}
    });

    window.addEventListener('focusguard:disable', () => {
      try {
        chrome.storage.sync.set({ enabled: false });
        chrome.runtime?.sendMessage({ type: 'update-rules', enabled: false });
      } catch (_) {}
    });
  } catch (_) {
    // ignore
  }
})();
