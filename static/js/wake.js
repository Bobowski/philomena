window.app ??= {};
app.wake = {
  lock: null,
  report: null,

  start(report) {
    this.report = report;
    this.ask();
  },

  async ask() {
    if (!("wakeLock" in navigator)) {
      this.report(false);
      return;
    }
    try {
      this.lock = await navigator.wakeLock.request("screen");
      this.report(this.lock.released === false);
      this.lock.addEventListener("release", () => this.report(false));
    } catch {
      this.report(false);
    }
  },

  visible() {
    if (
      document.visibilityState === "visible" &&
      (this.lock === null || this.lock.released)
    ) {
      this.ask();
    }
  },
};
