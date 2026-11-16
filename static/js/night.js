window.app ??= {};
// Auto lights-out for the camera: once someone watches, the screen dims;
// a tap wakes it and re-arms the dim. "Keep on" cancels for the session.
app.night = (el, dim, dimIn) => {
  const delay = Number(el.dataset.lightsOut || 15) * 1000;
  const idle = Number(el.dataset.redim || 30) * 1000;
  let keep = false;
  let viewers = 0;
  let count = null;
  let idleTimer = null;
  const out = () => {
    clearInterval(count);
    count = null;
    dim(false);
    dimIn(0);
    clearTimeout(idleTimer);
    if (!keep && viewers >= 1) {
      idleTimer = setTimeout(() => dim(true), idle);
    }
  };
  return {
    viewers(n) {
      if (n >= 1 && viewers === 0 && !keep && !count) {
        let left = Math.round(delay / 1000);
        dimIn(left);
        count = setInterval(() => {
          left -= 1;
          dimIn(left);
          if (left <= 0) {
            clearInterval(count);
            count = null;
            dim(true);
          }
        }, 1000);
      }
      viewers = n;
    },
    keep() {
      keep = true;
      clearInterval(count);
      count = null;
      dimIn(0);
    },
    out,
    dim() {
      dim(true);
    },
  };
};
