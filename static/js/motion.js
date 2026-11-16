window.app ??= {};
// Frame-diff motion on the camera preview, in a 64x48 canvas every 500 ms.
// Grain in a dark room and an exposure change are not motion: a pixel counts
// only when it changes more than the brightness shift of the whole frame,
// and more than noiseK times the noise floor of the room.
// The returned object carries the tunables so tests can change them.
app.motion = (el, report) => {
  const cv = document.createElement("canvas");
  cv.width = 64;
  cv.height = 48;
  const ctx = cv.getContext("2d", { willReadFrequently: true });
  const state = {
    threshold: 18,
    fraction: 0.02,
    noiseK: 4,
    noise: null,
    calmAfter: 10,
    stillAfter: 60,
    level: "active",
  };
  let prev = null;
  let prevLuma = 0;
  const diffs = new Float32Array(64 * 48);
  let lastMotion = performance.now();
  let level = "active";
  const setLevel = (next) => {
    if (next === level) return;
    level = next;
    state.level = next;
    report(next);
  };
  const tick = () => {
    const video = el.querySelector("[data-rtc=preview]");
    if (!video || !video.videoWidth) return;
    ctx.drawImage(video, 0, 0, 64, 48);
    const img = ctx.getImageData(0, 0, 64, 48).data;
    let changed = 0;
    let luma = 0;
    for (let i = 0; i < img.length; i += 4) {
      luma += (img[i] + img[i + 1] + img[i + 2]) / 3;
    }
    luma /= 64 * 48;
    if (prev) {
      const shift = luma - prevLuma;
      let sum = 0;
      for (let i = 0, j = 0; i < img.length; i += 4, j++) {
        const g = (img[i] + img[i + 1] + img[i + 2]) / 3;
        const pg = (prev[i] + prev[i + 1] + prev[i + 2]) / 3;
        diffs[j] = Math.abs(g - pg - shift);
        sum += diffs[j];
      }
      // the floor falls fast and rises slowly, so a movement does not teach
      // the floor that movement is noise; a repeated frame (mean 0) says nothing
      const mean = sum / diffs.length;
      if (state.noise === null) state.noise = mean;
      else if (mean > 0) {
        state.noise += (mean - state.noise) * (mean < state.noise ? 0.3 : 0.02);
      }
      const cut = Math.max(state.threshold, state.noise * state.noiseK);
      for (const d of diffs) if (d > cut) changed++;
    }
    const amount = changed / (64 * 48);
    if (amount > state.fraction) lastMotion = performance.now();
    // 0.12 of the frame fills the meter. The recognition line is state.fraction.
    state.amount = amount;
    state.lastSample = { motion: amount > state.fraction, luma, t: performance.now() };
    state.onAmount?.(Math.min(1, amount / 0.12));
    prev = img;
    prevLuma = luma;
    const idle = (performance.now() - lastMotion) / 1000;
    setLevel(
      idle < state.calmAfter ? "active" : idle < state.stillAfter ? "calm" : "still"
    );
  };
  const timer = setInterval(tick, 500);
  state.stop = () => clearInterval(timer);
  return state;
};

// The viewer paints this. amount is 0..1.
app.motion.show = (amount) => {
  const level = Math.max(0, Math.min(1, Number(amount) || 0)).toFixed(3);
  for (const meter of document.querySelectorAll("[data-motion-meter]")) {
    meter.style.setProperty("--level", level);
  }
};
