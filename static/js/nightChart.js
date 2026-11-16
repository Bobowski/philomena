window.app ??= {};
// Tonight: summary lines and the canvas chart over timeline buckets.
// Plain functions; the elements come from the server markup.
app.nightChart = {
  // a minute is restless with a crying/stirring event or enough noise+motion
  restless(b) {
    return (
      b.ev.includes("crying") ||
      b.ev.includes("stirring") ||
      (b.motion >= 20 && b.sound >= 10)
    );
  },

  time(m) {
    const d = new Date(m * 60000);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  },

  span(min) {
    const h = Math.floor(min / 60);
    const mm = min % 60;
    return h ? `${h} h ${mm} m` : `${mm} m`;
  },

  // items: buckets sorted by minute; returns {quiet, stirred, cried}
  summaries(items, nowMs) {
    const RESTLESS = "Restless in the last 20 minutes";
    if (!items.length) return { quiet: "", stirred: "", cried: "" };
    const nowM = Math.floor(nowMs / 60000);
    let calmSince = null;
    for (let m = nowM; ; m--) {
      const b = items.find((x) => x.m === m);
      if (b && this.restless(b)) break;
      calmSince = m;
      if (!b && items[0].m > m) break;
    }
    const quiet =
      calmSince !== null && nowM - calmSince >= 20
        ? `Quiet since ${this.time(calmSince)} · ${this.span(nowM - calmSince)}`
        : RESTLESS;
    const runs = [];
    let runStart = null;
    let prev = null;
    for (const b of items) {
      if (this.restless(b)) {
        if (runStart === null || b.m - prev > 1) runStart = b.m;
        else {
          runs.push(runStart);
          runStart = b.m;
        }
      }
      prev = b.m;
    }
    if (runStart !== null) runs.push(runStart);
    const stirred = runs.length
      ? `Stirred at ${runs.slice(-5).map(this.time, this).join(", ")}${runs.length > 5 ? ` +${runs.length - 5}` : ""}`
      : "";
    const crias = items.filter((b) => b.ev.includes("crying")).map((b) => b.m);
    const cried = crias.length
      ? `Cried at ${crias.slice(-5).map(this.time, this).join(", ")}${crias.length > 5 ? ` +${crias.length - 5}` : ""}`
      : "";
    return { quiet, stirred, cried };
  },

  // draw the last `hours` of buckets on the canvas, devicePixelRatio aware
  draw(canvas, items, hours) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const g = canvas.getContext("2d");
    g.scale(dpr, dpr);
    g.clearRect(0, 0, w, h);
    const css = getComputedStyle(canvas);
    // the page's look: night or day tokens from input.css
    const amber = css.getPropertyValue("--meter-sound").trim() || "#d0915f";
    const coral = css.getPropertyValue("--alarm").trim() || "#ff4a2e";
    const sand = css.getPropertyValue("--ink").trim() || "#df7e55";
    const nowM = Math.floor(Date.now() / 60000);
    const startM = nowM - hours * 60;
    const pxPerMin = w / (hours * 60);
    const barH = h - 34;
    const byMin = new Map(items.map((b) => [b.m, b]));
    for (let m = startM; m <= nowM; m++) {
      const b = byMin.get(m);
      const x = (m - startM) * pxPerMin;
      if (b) {
        const ph = Math.min(1, b.peak / 40) * barH;
        if (b.sound > 0) {
          g.fillStyle = amber;
          g.globalAlpha = 0.25 + Math.min(1, b.peak / 40) * 0.75;
          g.fillRect(x, barH - ph, Math.max(1, pxPerMin), ph);
          g.globalAlpha = 1;
        }
        g.fillStyle = sand;
        g.globalAlpha = 0.15 + Math.min(1, b.motion / 60) * 0.5;
        g.fillRect(x, barH + 4, Math.max(1, pxPerMin), 6);
        g.globalAlpha = 1;
        for (const kind of b.ev) {
          if (kind === "crying") {
            g.fillStyle = coral;
            g.beginPath();
            g.arc(x + pxPerMin / 2, 8, 4, 0, Math.PI * 2);
            g.fill();
          } else if (kind === "stirring") {
            g.fillStyle = amber;
            g.beginPath();
            g.arc(x + pxPerMin / 2, 8, 3, 0, Math.PI * 2);
            g.fill();
          } else if (kind === "lights_on" || kind === "lights_off") {
            g.fillStyle = sand;
            g.fillRect(x + pxPerMin / 2 - 1, 4, 2, 8);
          }
        }
      }
      // skip an hour label that would run into "now" at the right edge
      if (m % 120 === 0 && x + 10 < w - 44) {
        g.fillStyle = sand;
        g.globalAlpha = 0.7;
        g.font = "10px sans-serif";
        g.textAlign = "center";
        g.fillText(this.time(m), x + 10, h - 4);
        g.globalAlpha = 1;
      }
    }
    g.fillStyle = sand;
    g.font = "10px sans-serif";
    g.textAlign = "right";
    g.fillText("now", w - 4, h - 4);
  },

  // the data-channel payload lands here; the element remembers the items
  show(el, items, write) {
    el._titems = items;
    const s = this.summaries(items, Date.now());
    write(s);
    const canvas = el.querySelector("canvas[data-chart]");
    if (canvas) this.draw(canvas, items, 12);
  },
};
