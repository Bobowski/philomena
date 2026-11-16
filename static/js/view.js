window.app ??= {};
// Rotate and fit for the video box, persisted per code in localStorage.
app.view = (el, writeFit) => {
  const key = `philomena.view.${el.dataset.code || ""}`;
  let deg = 0;
  let fit = "contain";
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (saved) {
      deg = saved.deg || 0;
      fit = saved.fit || "contain";
    }
  } catch {}
  let zoom = 1;
  let panX = 0;
  let panY = 0;
  const pointers = new Map();
  let lastTap = { t: 0, x: 0, y: 0 };

  const clampPan = () => {
    const mx = (el.clientWidth * (zoom - 1)) / (2 * zoom);
    const my = (el.clientHeight * (zoom - 1)) / (2 * zoom);
    panX = Math.max(-mx, Math.min(mx, panX));
    panY = Math.max(-my, Math.min(my, panY));
  };

  const apply = () => {
    el.style.transform = `rotate(${deg}deg) scale(${zoom}) translate(${panX}px, ${panY}px)`;
    el.style.touchAction = zoom > 1 ? "none" : "";
    if (deg === 90 || deg === 270) {
      el.style.width = "100dvh";
      el.style.height = "100dvw";
      el.style.left = "50%";
      el.style.top = "50%";
      el.style.translate = "-50% -50%";
    } else {
      el.style.width = "100%";
      el.style.height = "100%";
      el.style.left = "0";
      el.style.top = "0";
      el.style.translate = "0 0";
    }
    el.dataset.fit = fit;
    writeFit?.(fit);
    try {
      localStorage.setItem(key, JSON.stringify({ deg, fit }));
    } catch {}
  };
  const setZoom = (z, cx, cy) => {
    zoom = Math.max(1, Math.min(4, z));
    if (cx !== undefined) {
      panX = (el.clientWidth / 2 - cx) / zoom;
      panY = (el.clientHeight / 2 - cy) / zoom;
    }
    if (zoom === 1) {
      panX = 0;
      panY = 0;
    }
    clampPan();
    apply();
  };

  const point = (e) => {
    const r = el.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  let pinch = null;
  let drag = null;
  el.addEventListener("pointerdown", (e) => {
    pointers.set(e.pointerId, point(e));
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), z: zoom };
      drag = null;
    } else {
      const now = performance.now();
      if (now - lastTap.t < 320 && pointers.size === 1) {
        const pt = point(e);
        setZoom(zoom > 1 ? 1 : 2.5, pt.x, pt.y);
        lastTap.t = 0;
        return;
      }
      lastTap = { t: now, x: e.clientX, y: e.clientY };
      if (zoom > 1) {
        drag = { x: e.clientX, y: e.clientY, px: panX, py: panY };
        el.setPointerCapture(e.pointerId);
      }
    }
  });
  el.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, point(e));
    if (pinch && pointers.size >= 2) {
      const [a, b] = [...pointers.values()];
      setZoom(pinch.z * (Math.hypot(a.x - b.x, a.y - b.y) / pinch.d));
    } else if (drag && zoom > 1) {
      panX = drag.px + (e.clientX - drag.x) / zoom;
      panY = drag.py + (e.clientY - drag.y) / zoom;
      clampPan();
      apply();
    }
  });
  const drop = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) drag = null;
  };
  el.addEventListener("pointerup", drop);
  el.addEventListener("pointercancel", drop);

  apply();
  return {
    zoom: setZoom,
    rotate() {
      zoom = 1;
      panX = 0;
      panY = 0;
      deg = (deg + 90) % 360;
      apply();
    },
    fit() {
      fit = fit === "contain" ? "cover" : "contain";
      apply();
    },
  };
};
