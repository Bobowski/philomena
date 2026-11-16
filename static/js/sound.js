window.app ??= {};
// The sound engine: one AudioContext, a level meter on the remote audio,
// the lost-connection alarm, and the loud alert. State in file scope.
app.sound = (() => {
  let ctx = null;
  let analyser = null;
  let rafOn = false;
  let level = 0;
  let meters = [];
  let cb = {};
  // alarm
  let wasLive = false;
  let lastState = "waiting";
  let alarmTimer = null;
  let chimeTimer = null;
  let silenced = false;
  // camera events drive the alerts now
  const LABELS = {
    crying: "Crying",
    stirring: "Stirring",
    loud: "Loud sound",
    movement: "Movement",
    lights_on: "Lights on",
    lights_off: "Lights off",
  };
  let alertKinds = {};
  let bannerTimer = 0;
  let alertUntil = 0;
  let el = null;
  let hiddenAt = 0;

  function context() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    return ctx;
  }

  function chime() {
    const c = context();
    if (c) {
      const t = c.currentTime;
      for (const [freq, at] of [[660, 0], [880, 0.18]]) {
        const o = c.createOscillator();
        const g = c.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.setValueAtTime(0, t + at);
        g.gain.linearRampToValueAtTime(0.25, t + at + 0.02);
        g.gain.exponentialRampToValueAtTime(0.001, t + at + 0.18);
        o.connect(g);
        g.connect(c.destination);
        o.start(t + at);
        o.stop(t + at + 0.2);
      }
    }
    navigator.vibrate?.([300, 200, 300]);
  }

  const buf = new Float32Array(1024);
  function frame() {
    if (analyser) {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < analyser.fftSize; i++) sum += buf[i] * buf[i];
      const db = 20 * Math.log10(Math.sqrt(sum / analyser.fftSize) || 1e-8);
      const target = Math.min(1, Math.max(0, (db + 60) / 50));
      // fast attack, slow ~300 ms release
      level = target > level ? target : level + (target - level) * 0.07;
      for (const m of meters) m.style.setProperty("--level", level.toFixed(3));
    }
    requestAnimationFrame(frame);
  }

  function stopAlarm() {
    clearInterval(chimeTimer);
    chimeTimer = null;
    cb.alarm?.(false);
  }

  return {
    unlock() {
      const c = context();
      c?.resume().catch(() => {});
      if (!rafOn) {
        rafOn = true;
        requestAnimationFrame(frame);
      }
    },
    attach(stream) {
      const c = context();
      if (!c || analyser) return;
      try {
        const src = c.createMediaStreamSource(stream);
        analyser = c.createAnalyser();
        analyser.fftSize = 1024;
        src.connect(analyser);
      } catch {}
    },
    // the page wires signals: alarm, wake, toast, muted, dim
    wire(element, callbacks) {
      el = element;
      cb = callbacks;
      meters = [...el.querySelectorAll("[data-meter]")];
      return this;
    },
    state(s) {
      lastState = s;
      if (s === "live") {
        wasLive = true;
        silenced = false;
        clearTimeout(alarmTimer);
        alarmTimer = null;
        stopAlarm();
      } else if (wasLive && !alarmTimer && !chimeTimer) {
        alarmTimer = setTimeout(() => {
          alarmTimer = null;
          if (lastState !== "live" && !silenced) {
            cb.alarm?.(true);
            chime();
            chimeTimer = setInterval(chime, 5000);
          }
        }, 10000);
      }
    },
    silence() {
      silenced = true;
      clearTimeout(alarmTimer);
      alarmTimer = null;
      stopAlarm();
    },
    // the Alerts toggles: a map of kind -> on
    alerts(map) {
      alertKinds = map || {};
    },
    // one camera event: banner always, chime only when the parent is not watching
    event(ev) {
      const label = LABELS[ev.kind] ?? ev.kind;
      const time = new Date(ev.at).toTimeString().slice(0, 5);
      cb.event?.(`${label} · ${time}`);
      clearTimeout(bannerTimer);
      bannerTimer = setTimeout(() => cb.event?.(""), 20000);
      cb.lastEvent?.(`${label} · ${time}`);
      if (!alertKinds[ev.kind]) return;
      const gated =
        cb.muted?.() || cb.dim?.() || document.visibilityState !== "visible";
      if (!gated || performance.now() < alertUntil) return;
      alertUntil = performance.now() + 30000;
      el.dataset.alerted = "1";
      chime();
      cb.wake?.();
    },
    // a reconnecting viewer gets the backlog; show only the most recent one
    events(items) {
      const fresh = (items || []).filter((i) => Date.now() - i.at < 3600000);
      if (!fresh.length) return;
      const last = fresh[fresh.length - 1];
      const label = LABELS[last.kind] ?? last.kind;
      cb.lastEvent?.(`${label} · ${new Date(last.at).toTimeString().slice(0, 5)}`);
    },
    visible() {
      const c = context();
      c?.resume().catch(() => {});
      const video = el?.querySelector("[data-rtc=remote]");
      if (video?.paused) video.play().catch(() => {});
      if (hiddenAt && performance.now() - hiddenAt > 5000 && lastState === "live") {
        cb.toast?.("Philomena was in the background. Keep it open to hear your baby.");
      }
      hiddenAt = 0;
    },
    hidden() {
      hiddenAt = performance.now();
    },
  };
})();
