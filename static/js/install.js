window.app ??= {};
// The install hint: captures beforeinstallprompt, detects iOS Safari.
app.install = (() => {
  let evt = null;
  const dismissed = () => localStorage.getItem("philomena.install.dismissed") === "1";
  return {
    capture(e, write) {
      e.preventDefault();
      evt = e;
      write(true);
    },
    // reports installability and the iOS hint through the callbacks
    wire(writeInstallable, writeIos) {
      if (dismissed()) return;
      writeInstallable(!!evt);
      const ios =
        /iPhone|iPad/.test(navigator.userAgent) && navigator.standalone !== true;
      writeIos(ios);
    },
    async prompt(write) {
      if (!evt) return;
      const e = evt;
      evt = null;
      try {
        await e.prompt();
      } catch {}
      write(false);
    },
    dismiss() {
      localStorage.setItem("philomena.install.dismissed", "1");
    },
  };
})();
