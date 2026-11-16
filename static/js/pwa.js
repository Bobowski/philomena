window.app ??= {};
app.pwa = {
  register() {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
  },
};
