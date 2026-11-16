window.app ??= {};
// Web Push on the viewer: subscribe, resubscribe, kinds sync, off.
app.push = {
  _el: null,

  _key() {
    const raw = this._el.dataset.vapid;
    const pad = "=".repeat((4 - (raw.length % 4)) % 4);
    const bin = atob((raw + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(bin, (ch) => ch.charCodeAt(0));
  },

  _path(path) {
    return `/watch/${this._el.dataset.code}/push${path}`;
  },

  _post(path, body) {
    return fetch(this._path(path), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  async _sub() {
    const reg = await navigator.serviceWorker.getRegistration();
    return reg?.pushManager.getSubscription();
  },

  // called on init: turn the toggle's persisted state back on the server
  async boot(el) {
    this._el = el;
    if (!("Notification" in window) || Notification.permission === "denied") {
      return "denied";
    }
    if (localStorage.getItem(`philomena.push.${el.dataset.code}`) !== "1") return "";
    const sub = await this._sub();
    if (!sub) return "";
    await this._post("", {
      subscription: sub.toJSON(),
      kinds: this._kinds(),
    });
    return "on";
  },

  _kinds() {
    const raw = localStorage.getItem("philomena.alerts") || "{}";
    let kinds;
    try {
      kinds = JSON.parse(raw);
    } catch {
      kinds = {};
    }
    const on = ["crying", "stirring", "loud", "movement", "lights"]
      .filter((k) => kinds[k]);
    on.push("offline");
    return on;
  },

  // turn push on or off for this room; returns the label the row should show
  async setOn(on) {
    if (!on) {
      const sub = await this._sub();
      await sub?.unsubscribe();
      await this._post("/off", {});
      localStorage.setItem(`philomena.push.${this._el.dataset.code}`, "0");
      return "";
    }
    const perm = await Notification.requestPermission();
    if (perm !== "granted") return "denied";
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: this._key(),
    });
    localStorage.setItem(`philomena.push.${this._el.dataset.code}`, "1");
    await this._post("", { subscription: sub.toJSON(), kinds: this._kinds() });
    return "on";
  },

  // an Alerts toggle changed while push is on
  async syncKinds() {
    if (localStorage.getItem(`philomena.push.${this._el.dataset.code}`) !== "1") return;
    await this._post("/kinds", { kinds: this._kinds() });
  },
};
