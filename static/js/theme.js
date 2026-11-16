window.app ??= {};
// Night or day. "auto" follows the phone's light or dark setting, so the look
// changes at sunset when the phone does. Loaded in <head> without defer, so the
// page paints in the right look from the first frame.
app.theme = (() => {
  const KEY = "philomena.theme";
  const COLORS = { night: "#000000", day: "#ffffff" };
  const media = window.matchMedia?.("(prefers-color-scheme: light)");
  const listeners = [];
  let mode = "auto";
  try {
    mode = localStorage.getItem(KEY) || "auto";
  } catch {}
  if (!["auto", "night", "day"].includes(mode)) mode = "auto";

  const resolved = () => (mode === "auto" ? (media?.matches ? "day" : "night") : mode);

  function apply() {
    const look = resolved();
    document.documentElement.dataset.theme = look;
    for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
      meta.content = COLORS[look];
    }
    for (const fn of listeners) fn(mode, look);
  }

  media?.addEventListener?.("change", () => mode === "auto" && apply());
  apply();

  return {
    get: resolved,
    set(next) {
      mode = ["auto", "night", "day"].includes(next) ? next : "auto";
      try {
        localStorage.setItem(KEY, mode);
      } catch {}
      apply();
    },
    // the page keeps its signals current: fn(mode, look)
    watch(fn) {
      listeners.push(fn);
      fn(mode, resolved());
    },
  };
})();
