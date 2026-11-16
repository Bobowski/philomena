// Philomena service worker: install fast, take over, cache nothing.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

const LABELS = {
  crying: "Crying",
  stirring: "Stirring",
  loud: "Loud sound",
  movement: "Movement",
  lights_on: "Lights on",
  lights_off: "Lights off",
  lights: "Lights",
  offline: "Offline",
};

self.addEventListener("push", (e) => {
  let d = {};
  try {
    d = e.data ? e.data.json() : {};
  } catch {}
  const t = new Date(d.at || Date.now());
  const hhmm =
    String(t.getHours()).padStart(2, "0") + ":" + String(t.getMinutes()).padStart(2, "0");
  const body = d.body || `${LABELS[d.kind] || "Philomena"} · ${hhmm}`;
  e.waitUntil(
    self.registration.showNotification(d.title || "Philomena", {
      body,
      tag: d.kind || "philomena",
      renotify: true,
      data: { url: d.url || "/" },
      icon: "/static/icons/icon-192.png",
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = e.notification.data?.url || "/";
  e.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((list) =>
        list.length
          ? list[0].focus().then(() => list[0].navigate?.(url))
          : self.clients.openWindow(url)
      )
  );
});
