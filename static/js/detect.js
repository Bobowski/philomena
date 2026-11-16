window.app ??= {};
// Camera-side detection: crying, stirring, loud, movement, lights on/off.
// feed({level, f0, clarity, band, motion, luma, t?}) drives the state machine;
// the live path feeds it from the mic analyser and the motion sampler.
app.detect = (el, emit, cb = {}) => {
  const st = {
    cryWin: 4000,
    cryShare: 0.6,
    cryCool: 120000,
    stirWin: 30000,
    stirMotion: 6000,
    stirSound: 4000,
    stirCool: 300000,
    loudHold: 2000,
    loudCool: 60000,
    moveHold: 3000,
    moveCool: 60000,
    lumaDelta: 40,
    lumaHold: 2000,
    lumaCool: 60000,
    floorDb: -60,
    live: true,
    now: () => performance.now(),
    feed(sample) {
      tick(sample);
    },
    resume() {
      st.ctx?.resume().then(() => cb.blocked?.(false));
      app.rtc.playTalk?.();
    },
    // tests reset the buffers and cooldowns before feeding samples
    reset() {
      frames.length = 0;
      spans.length = 0;
      lumas.length = 0;
      for (const k in lastEmit) delete lastEmit[k];
      loudStart = null;
      moveStart = null;
      lumaStart = null;
      lumaSign = 0;
      floors.length = 0;
      lastFloorT = -Infinity;
    },
  };

  const frames = []; // {t, sound, loud, cry}
  const spans = []; // {t, motion, sound}
  const lumas = []; // {t, luma}
  const floors = []; // up to 300 levels, one per second
  let lastFloorT = -Infinity;
  const lastEmit = {};
  let loudStart = null;
  let moveStart = null;
  let lumaStart = null;
  let lumaSign = 0;

  const mean = (list, key) => list.reduce((s, l) => s + l[key], 0) / list.length;

  function tick(sample) {
    const t = sample.t ?? st.now();
    const sound = sample.level > st.floorDb + 10;
    const loud = sample.level > st.floorDb + 20;
    const cry =
      sound &&
      sample.f0 >= 250 &&
      sample.f0 <= 700 &&
      sample.clarity > 0.5 &&
      sample.band > 0.6;
    frames.push({ t, sound, loud, cry });
    spans.push({ t, motion: !!sample.motion, sound });
    cb.timeline?.record({
      t,
      level: sample.level,
      floor: st.floorDb,
      sound,
      motion: !!sample.motion,
    });
    // the floor adapts once a second and freezes while a cry or a loud
    // sound would chase it up
    if (!cry && !loud && t - lastFloorT >= 1000) {
      lastFloorT = t;
      floors.push(sample.level);
      if (floors.length > 300) floors.shift();
      const sorted = [...floors].sort((a, b) => a - b);
      st.floorDb = sorted[Math.floor(sorted.length * 0.1)] ?? st.floorDb;
    }
    if (sample.luma !== undefined) lumas.push({ t, luma: sample.luma });
    const cut = t - st.stirWin;
    while (frames.length && frames[0].t < cut) frames.shift();
    while (spans.length && spans[0].t < cut) spans.shift();
    while (lumas.length && lumas[0].t < t - 30000) lumas.shift();

    const fire = (kind, cool, detail) => {
      if (t - (lastEmit[kind] ?? -Infinity) < cool) return;
      lastEmit[kind] = t;
      cb.timeline?.event(kind, Date.now());
      emit({ kind, at: Date.now(), detail });
    };

    const recent = frames.filter((f) => f.t > t - st.cryWin);
    if (
      recent.length >= 4 &&
      recent.filter((f) => f.cry).length / recent.length >= st.cryShare
    ) {
      fire("crying", st.cryCool, {});
    }

    let motionMs = 0;
    let soundMs = 0;
    for (let i = 1; i < spans.length; i++) {
      const dt = Math.min(spans[i].t - spans[i - 1].t, 1000);
      if (spans[i].motion) motionMs += dt;
      if (spans[i].sound) soundMs += dt;
    }
    if (motionMs >= st.stirMotion && soundMs >= st.stirSound) {
      fire("stirring", st.stirCool, {});
    }

    if (loud) {
      loudStart ??= t;
      if (t - loudStart >= st.loudHold) fire("loud", st.loudCool, { level: sample.level });
    } else {
      loudStart = null;
    }

    if (sample.motion) {
      moveStart ??= t;
      if (t - moveStart >= st.moveHold) fire("movement", st.moveCool, {});
    } else {
      moveStart = null;
    }

    const older = lumas.filter((l) => l.t <= t - 10000);
    const newer = lumas.filter((l) => l.t > t - st.lumaHold);
    if (older.length && newer.length) {
      const d = mean(newer, "luma") - mean(older, "luma");
      if (Math.abs(d) > st.lumaDelta) {
        if (!lumaStart || Math.sign(d) !== lumaSign) {
          lumaStart = t;
          lumaSign = Math.sign(d);
        } else if (t - lumaStart >= st.lumaHold) {
          fire(d > 0 ? "lights_on" : "lights_off", st.lumaCool, {
            delta: Math.round(d),
          });
        }
      } else {
        lumaStart = null;
        lumaSign = 0;
      }
    }
  }

  // pitch by autocorrelation, searched in 150-900 Hz
  function pitch(buf, sr) {
    let e0 = 0;
    for (const v of buf) e0 += v * v;
    if (e0 < 1e-6) return { f0: 0, clarity: 0 };
    const minLag = Math.floor(sr / 900);
    const maxLag = Math.ceil(sr / 150);
    let best = 0;
    let bestC = 0;
    for (let lag = minLag; lag <= maxLag; lag++) {
      let s = 0;
      for (let i = 0; i + lag < buf.length; i++) s += buf[i] * buf[i + lag];
      const c = s / e0;
      if (c > bestC) {
        bestC = c;
        best = lag;
      }
    }
    return { f0: best ? sr / best : 0, clarity: bestC };
  }

  st.attach = (stream, motion) => {
    const ctx = new AudioContext();
    st.ctx = ctx;
    if (ctx.state === "suspended") cb.blocked?.(true);
    ctx.onstatechange = () => cb.blocked?.(ctx.state !== "running");
    const src = ctx.createMediaStreamSource(stream);
    const an = ctx.createAnalyser();
    an.fftSize = 2048;
    src.connect(an);
    const td = new Float32Array(an.fftSize);
    const fd = new Float32Array(an.frequencyBinCount);
    setInterval(() => {
      if (!st.live || ctx.state !== "running") return;
      an.getFloatTimeDomainData(td);
      an.getFloatFrequencyData(fd);
      let sum = 0;
      for (const v of td) sum += v * v;
      const db = 20 * Math.log10(Math.sqrt(sum / td.length) + 1e-10);
      const { f0, clarity } = pitch(td, ctx.sampleRate);
      const nyq = ctx.sampleRate / 2;
      const lo = Math.floor((300 / nyq) * fd.length);
      const hi = Math.ceil((3000 / nyq) * fd.length);
      let bandE = 0;
      let totE = 0;
      for (let i = 0; i < fd.length; i++) {
        const e = Math.pow(10, fd[i] / 10);
        totE += e;
        if (i >= lo && i <= hi) bandE += e;
      }
      const s = motion?.lastSample ?? {};
      st.feed({
        level: db,
        f0,
        clarity,
        band: totE ? bandE / totE : 0,
        motion: s.motion,
        luma: s.luma,
      });
    }, 100);
  };

  return st;
};
