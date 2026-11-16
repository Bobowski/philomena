window.app ??= {};
// The night timeline lives on the camera phone: one bucket per minute,
// flushed to localStorage once a minute and on pagehide, 24 h kept.
app.timeline = (code) => {
  const KEY = `philomena.timeline.${code}`;
  const KEEP = 1440;
  let buckets = [];
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "[]");
    const cutoff = Math.floor(Date.now() / 60000) - KEEP;
    buckets = raw.filter((b) => b.m >= cutoff);
  } catch {
    buckets = [];
  }

  const minute = (t) => Math.floor(t / 60000);
  const current = (t) => {
    const m = minute(t);
    let b = buckets[buckets.length - 1];
    if (!b || b.m !== m) {
      b = { m, peak: 0, sound: 0, motion: 0, ev: [] };
      buckets.push(b);
    }
    return b;
  };

  const st = {
    buckets: () => buckets,
    add(items) {
      for (const item of items) {
        const b = {
          m: item.m,
          peak: item.peak || 0,
          sound: item.sound || 0,
          motion: item.motion || 0,
          ev: item.ev || [],
        };
        if (!buckets.length || b.m > buckets[buckets.length - 1].m) buckets.push(b);
        else {
          const at = buckets.findIndex((x) => x.m >= b.m);
          if (at >= 0 && buckets[at].m === b.m) buckets[at] = b;
          else buckets.splice(at < 0 ? buckets.length : at, 0, b);
        }
      }
      if (buckets.length > KEEP) buckets = buckets.slice(-KEEP);
    },
    // detect.js feeds one frame every 100 ms; buckets are wall-clock minutes
    record(frame) {
      const b = current(Date.now());
      const above = (frame.level ?? -120) - (frame.floor ?? -60);
      if (above > b.peak) b.peak = Math.min(40, Math.max(0, above));
      if (frame.sound) b.sound += 0.1;
      if (frame.motion) b.motion += 0.1;
    },
    event(kind) {
      const b = current(Date.now());
      if (!b.ev.includes(kind)) b.ev.push(kind);
    },
    flush() {
      if (buckets.length > KEEP) buckets = buckets.slice(-KEEP);
      localStorage.setItem(KEY, JSON.stringify(buckets));
    },
    clear() {
      buckets = [];
      localStorage.removeItem(KEY);
    },
  };

  setInterval(() => st.flush(), 60000);
  return st;
};
