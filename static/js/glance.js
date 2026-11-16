window.app ??= {};
// The glance view's word, from the camera's events: Crying, Stirring, or Calm.
// A crying event holds "Crying" for 150 s: the camera repeats it every 2 min
// while the cry goes on. Stirring, a loud sound, or movement holds "Stirring"
// for 60 s. write(state, line) gets the word's key and the line under it.
app.glance = (write) => {
  const HOLD = { crying: 150000, stirring: 60000, loud: 60000, movement: 60000 };
  const SAID = { stirring: "Stirred", loud: "Loud sound", movement: "Moved" };
  const last = {};
  let cryStart = 0;
  let lastAny = 0;
  const hm = (t) => new Date(t).toTimeString().slice(0, 5);

  function paint() {
    const now = Date.now();
    if (last.crying && now - last.crying < HOLD.crying) {
      write("crying", `Since ${hm(cryStart)}`);
      return;
    }
    const stir = ["stirring", "loud", "movement"]
      .filter((k) => last[k] && now - last[k] < HOLD[k])
      .sort((a, b) => last[b] - last[a])[0];
    if (stir) {
      write("stirring", `${SAID[stir]} at ${hm(last[stir])}`);
      return;
    }
    write("calm", lastAny ? `Quiet since ${hm(lastAny)}` : "Nothing heard yet");
  }

  function add(ev) {
    if (!(ev.kind in HOLD) || !ev.at) return;
    if (ev.kind === "crying" && !(last.crying && ev.at - last.crying < HOLD.crying)) {
      cryStart = ev.at;
    }
    last[ev.kind] = Math.max(last[ev.kind] || 0, ev.at);
    lastAny = Math.max(lastAny, ev.at);
  }

  setInterval(paint, 5000);
  paint();
  return {
    // one live event from the camera
    event(ev) {
      add(ev);
      paint();
    },
    // the backlog a reconnecting viewer gets
    events(items) {
      for (const ev of items || []) add(ev);
      paint();
    },
  };
};
