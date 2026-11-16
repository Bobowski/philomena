window.app ??= {};
// send targets per motion level; "away" caps everything when nobody looks
// (a viewer that does not look gets no video track; see setViewerVideo)
const RATES = {
  active: { fps: 24, bps: 1200000 },
  calm: { fps: 6, bps: 350000 },
  still: { fps: 2, bps: 150000 },
  away: { fps: 1, bps: 100000 },
};

app.rtc = {
  role: null,
  code: null,
  tab: null,
  ice: [],
  el: null,
  out: null,
  pcs: {},
  dcs: {},
  media: null,
  facing: "environment",
  videoTrack: null,
  talkTrack: null,
  prevMuted: null,
  battery: null,
  battTimer: null,
  liveSince: 0,
  liveTimer: null,

  async start(el, out) {
    this.el = el;
    this.out = out;
    this.role = el.dataset.role;
    this.code = el.dataset.code;
    this.tab = el.dataset.tab;
    if (this.role === "cam") await this.startCam();
  },

  receive(msg) {
    // the stream delivers the message as a JSON string literal
    if (typeof msg === "string") msg = JSON.parse(msg);
    const type = msg.type;
    if (type === "ice") {
      this.ice = msg.data || [];
      return;
    }
    if (type === "replaced") {
      this.onReplaced();
      return;
    }
    if (type === "pending") {
      this.setState("pending");
      return;
    }
    if (type === "name") {
      this.out.name?.(msg.data || "");
      return;
    }
    if (type === "removed") {
      for (const pc of Object.values(this.pcs)) pc.close();
      this.pcs = {};
      this.setState("removed");
      return;
    }
    if (type === "knock") {
      // a viewer asks for approval: wake the screen out of lights-out
      this.el.night?.out();
      return;
    }
    if (type === "kick") {
      // unlike leave, a kick closes the connection even when it is healthy
      const pc = this.pcs[msg.from];
      if (pc) {
        pc.close();
        delete this.pcs[msg.from];
        this.updateViewers();
      }
      return;
    }
    if (type === "cam") {
      this.onCamPresent(msg.data === true);
      return;
    }
    const from = msg.from;
    if (!from) return;
    if (type === "join") this.onJoin(from);
    else if (type === "leave") this.onLeave(from);
    else if (type === "offer") this.onOffer(from, msg.data);
    else if (type === "answer") this.onAnswer(from, msg.data);
    else if (type === "candidate") this.onCandidate(from, msg.data);
  },

  send(to, kind, data) {
    fetch("/rooms/" + this.code + "/signal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tab: this.tab, to, kind, data }),
    });
  },

  // --- shared peer handling ---

  newPeer(from) {
    this.drop(from);
    const pc = new RTCPeerConnection({ iceServers: this.ice });
    const peer = { pc, queue: [], fails: 0 };
    pc.onicecandidate = (e) => {
      if (e.candidate) this.send(from, "candidate", e.candidate.toJSON());
    };
    pc.onconnectionstatechange = () => this.onPeerState(from);
    pc.ontrack = (e) => this.onTrack(e);
    this.pcs[from] = peer;
    if (this.media) {
      for (const track of this.media.getTracks()) {
        const sender = pc.addTrack(track, this.media);
        if (track.kind === "video") pc._vsender = sender;
      }
    }
    // the camera opens the control channel before the first offer
    if (this.role === "cam") this.attachChannel(from, pc.createDataChannel("ctl"));
    else pc.ondatachannel = (e) => this.attachChannel(from, e.channel);
    return peer;
  },

  attachChannel(from, dc) {
    dc.onopen = () => {
      if (this.battery && this.role === "cam") this.sendBattery(from);
      if (this.role === "cam") {
        this.sendCtl(from, { t: "facing", value: this.facing });
        this.sendCtl(from, {
          t: "motion",
          level: this.motionLevel || "active",
          fps: this.rateFor().fps,
        });
        this.sendCtl(from, { t: "move", amount: this._move || 0 });
        if (this.events?.length) this.sendCtl(from, { t: "events", items: this.events });
      } else {
        this.sendCtl(from, { t: "attention", looking: this.lookingFlag ?? true });
      }
    };
    dc.onmessage = (e) => {
      try {
        this.onCtl(from, JSON.parse(e.data));
      } catch {}
    };
    dc.onclose = () => {
      if (this.dcs[from] === dc) delete this.dcs[from];
    };
    this.dcs[from] = dc;
  },

  sendCtl(from, msg) {
    const dc = this.dcs[from];
    if (dc?.readyState === "open") dc.send(JSON.stringify(msg));
  },

  sendCtlAll(msg) {
    for (const from of Object.keys(this.dcs)) this.sendCtl(from, msg);
  },

  onCtl(from, msg) {
    if (this.role === "cam") {
      if (msg.t === "flip") this.flip();
      else if (msg.t === "video") this.setViewerVideo(from, msg.on);
      else if (msg.t === "exposure") this.applyExposure(!!msg.boost);
      else if (msg.t === "attention") {
        const peer = this.pcs[from];
        if (peer) {
          peer.looking = msg.looking;
          // nobody sees this viewer's picture: send it no video at all
          this.setViewerVideo(from, msg.looking !== false);
          this.applyRates();
        }
      } else if (msg.t === "timeline?") {
        const items = this.timeline?.buckets() || [];
        for (let i = 0; i < items.length; i += 240) {
          this.sendCtl(from, {
            t: "timeline",
            items: items.slice(i, i + 240),
            done: i + 240 >= items.length,
          });
        }
        if (!items.length) this.sendCtl(from, { t: "timeline", items: [], done: true });
      }
      return;
    }
    if (msg.t === "battery") {
      this.battery = msg;
      this.out.battery?.(msg);
    } else if (msg.t === "exposure") {
      this.out.exposure?.(!!msg.supported);
    } else if (msg.t === "motion") {
      this.out.motion?.(msg.level);
    } else if (msg.t === "move") {
      app.motion.show(msg.amount);
    } else if (msg.t === "event") {
      this.out.event?.(msg);
    } else if (msg.t === "events") {
      this.out.events?.(msg.items);
    } else if (msg.t === "timeline") {
      this._tl = (this._tl || []).concat(msg.items);
      if (msg.done) {
        const items = this._tl;
        this._tl = [];
        this.out.timeline?.(items);
      }
    }
  },

  // adaptive rate: the motion level, capped at "away" when nobody looks
  rateFor() {
    const connected = this.connected();
    if (connected.length && connected.every((p) => p.looking === false)) {
      return RATES.away;
    }
    return RATES[this.motionLevel || "active"];
  },

  applyRates() {
    if (this.role !== "cam") return;
    const { fps, bps } = this.rateFor();
    if (fps === this._fps && bps === this._bps) return;
    this._fps = fps;
    this._bps = bps;
    for (const peer of Object.values(this.pcs)) {
      const s = peer.pc._vsender;
      if (!s || !s.track) continue;
      this.applyRateTo(s);
    }
    try {
      this.videoTrack
        ?.applyConstraints({ frameRate: { max: fps } })
        .catch(() => {});
    } catch {}
  },

  onMotionLevel(level) {
    this.motionLevel = level;
    this.applyRates();
    this.sendCtlAll({ t: "motion", level, fps: this.rateFor().fps });
  },

  onMotionAmount(amount) {
    if (this._move != null && Math.abs(this._move - amount) < 0.03) return;
    this._move = amount;
    this.sendCtlAll({ t: "move", amount });
  },

  // viewer side: page visible && not Screen off && not Sound only
  setLooking(b) {
    if (b === this.lookingFlag) return;
    this.lookingFlag = b;
    this.sendCtlAll({ t: "attention", looking: b });
  },

  applyRateTo(sender) {
    const { fps, bps } = this.rateFor();
    const p = sender.getParameters();
    p.encodings = p.encodings?.length ? p.encodings : [{}];
    p.encodings[0].maxFramerate = fps;
    p.encodings[0].maxBitrate = bps;
    sender.setParameters(p).catch(() => {});
  },

  // audio only for this viewer: swap the video sender for null
  exposureSupport() {
    try {
      const caps = this.videoTrack?.getCapabilities?.();
      return !!(caps && (caps.exposureCompensation || caps.exposureMode));
    } catch {
      return false;
    }
  },

  applyExposure(boost) {
    try {
      const caps = this.videoTrack?.getCapabilities?.();
      const range = caps?.exposureCompensation;
      if (!range) return;
      this.videoTrack.applyConstraints({
        advanced: [
          {
            exposureMode: "continuous",
            exposureCompensation: boost ? range.max * 0.75 : 0,
          },
        ],
      });
    } catch {}
  },

  setViewerVideo(from, on) {
    const sender = this.pcs[from]?.pc._vsender;
    if (!sender) return;
    sender
      .replaceTrack(on ? this.videoTrack : null)
      .then(() => {
        // the sender sat at the away rate while null: re-apply on video back
        if (on) this.applyRateTo(sender);
      })
      .catch(() => {});
  },

  // the viewer asks the camera to flip
  askFlip() {
    this.sendCtlAll({ t: "flip" });
  },

  // the viewer asks for video (on) or sound only (off)
  setVideo(on) {
    this.sendCtlAll({ t: "video", on });
  },

  sendBattery(to) {
    const b = this.battery;
    if (!b) return;
    const msg = { t: "battery", level: b.level, charging: b.charging };
    if (to) this.sendCtl(to, msg);
    else this.sendCtlAll(msg);
  },

  watchBattery() {
    navigator.getBattery?.()
      .then((b) => {
        const update = () => {
          this.battery = b;
          this.sendBattery();
          this.out.battery?.({ level: b.level, charging: b.charging });
        };
        b.onlevelchange = update;
        b.onchargingchange = update;
        update();
      })
      .catch(() => {});
  },

  // --- talk-back: push to talk, half duplex ---
  async talkStart() {
    if (this._talking) return;
    if (!this.talkTrack) {
      try {
        const mic = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
        });
        this.talkTrack = mic.getAudioTracks()[0];
      } catch {
        this.out.toast?.("Allow the microphone to talk to your baby.");
        return;
      }
    }
    this.talkTrack.enabled = true;
    this._talking = true;
    for (const peer of Object.values(this.pcs)) {
      const t = peer.pc
        .getTransceivers()
        .find((t) => t.receiver.track?.kind === "audio");
      if (t) t.sender.replaceTrack(this.talkTrack).catch(() => {});
    }
    if (this.prevMuted === null) this.prevMuted = this.muted ?? true;
    // mute the element internally: the Talk state, not the muted state
    const video = this.el.querySelector("[data-rtc=remote]");
    if (video) video.muted = true;
    this.out.talking?.(true);
  },

  talkEnd() {
    if (!this._talking) return;
    this._talking = false;
    if (this.talkTrack) this.talkTrack.enabled = false;
    for (const peer of Object.values(this.pcs)) {
      const t = peer.pc
        .getTransceivers()
        .find((t) => t.receiver.track?.kind === "audio");
      if (t) t.sender.replaceTrack(null).catch(() => {});
    }
    if (this.prevMuted !== null) {
      const video = this.el.querySelector("[data-rtc=remote]");
      if (video) {
        video.muted = this.prevMuted;
        if (!this.prevMuted) video.play().catch(() => {});
      }
      this.prevMuted = null;
    }
    this.out.talking?.(false);
  },

  // the camera replays a muted talk-back stream after a tap
  playTalk() {
    const audio = this.el.querySelector("[data-rtc=talk]");
    audio?.play().then(
      () => this.out.talkBlocked?.(false),
      () => {}
    );
  },

  drop(from) {
    const peer = this.pcs[from];
    if (!peer) return;
    delete this.pcs[from];
    try {
      peer.pc.close();
    } catch {}
    this.reportViewers();
  },

  connected() {
    return Object.values(this.pcs).filter((p) => p.pc.connectionState === "connected");
  },

  reportViewers() {
    const n = this.connected().length;
    if (this.role === "cam") {
      this.out.viewers?.(n);
      if (
        n === 0 &&
        this.media &&
        this.state !== "denied" &&
        this.state !== "replaced"
      ) {
        this.setState("waiting");
      }
    }
  },

  setState(s) {
    this.state = s;
    this.out.state?.(s);
  },

  async reportRoute(pc) {
    try {
      const stats = await pc.getStats();
      for (const r of stats.values()) {
        if (r.type === "candidate-pair" && r.nominated && r.state === "succeeded") {
          const local = stats.get(r.localCandidateId);
          if (local) this.out.route?.(local.candidateType === "relay" ? "relay" : "direct");
          return;
        }
      }
    } catch {}
  },

  onPeerState(from) {
    const peer = this.pcs[from];
    if (!peer) return;
    const s = peer.pc.connectionState;
    if (s === "connected") {
      peer.fails = 0;
      this.setState("live");
      this.reportRoute(peer.pc);
      this.applyRates();
      if (!this.liveSince) {
        this.liveSince = Date.now();
        this.liveTimer = setInterval(() => this.tickLive(), 30000);
        this.tickLive();
      }
    } else if (s === "failed") {
      peer.fails += 1;
      if (peer.fails > 1) {
        this.drop(from);
      } else if (this.role === "cam") {
        peer.pc.restartIce();
        this.offerTo(from, true);
      }
    } else if (s === "closed") {
      this.drop(from);
    } else if (s === "disconnected") {
      if (this.connected().length === 0) this.setState("lost");
    }
    this.reportViewers();
  },

  async onCandidate(from, data) {
    const peer = this.pcs[from];
    if (!peer || !data) return;
    if (!peer.pc.remoteDescription) {
      peer.queue.push(data);
      return;
    }
    try {
      await peer.pc.addIceCandidate(data);
    } catch {}
  },

  async flushQueue(peer) {
    for (const candidate of peer.queue) {
      try {
        await peer.pc.addIceCandidate(candidate);
      } catch {}
    }
    peer.queue = [];
  },

  // --- camera side: always the offerer ---

  async startCam() {
    this.setState("connecting");
    try {
      this.media = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: this.facing },
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch {
      this.setState("denied");
      return;
    }
    this.videoTrack = this.media.getVideoTracks()[0];
    const preview = this.el.querySelector("[data-rtc=preview]");
    if (preview) preview.srcObject = this.media;
    this.setState("waiting");
    this.watchBattery();
    this.events = [];
    this.motion = app.motion(this.el, (level) => this.onMotionLevel(level));
    this.motion.onAmount = (amount) => this.onMotionAmount(amount);
    this.timeline = app.timeline(this.el.dataset.code || "room");
    // camera-side detection: feeds events to every viewer over the ctl channel
    this.detect = app.detect(
      this.el,
      (ev) => {
        this.events.push(ev);
        if (this.events.length > 20) this.events.shift();
        this.sendCtlAll({ t: "event", kind: ev.kind, at: ev.at, detail: ev.detail });
        fetch(`/cam/${this.el.dataset.code}/events`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ kind: ev.kind, at: ev.at }),
        }).catch(() => {});
      },
      { blocked: (v) => this.out.detectBlocked?.(v), timeline: this.timeline }
    );
    this.detect.attach(this.media, this.motion);
    // peers created by joins that beat getUserMedia have no tracks yet
    for (const peer of Object.values(this.pcs)) {
      for (const track of this.media.getTracks()) {
        if (!peer.pc.getSenders().some((s) => s.track === track)) {
          const sender = peer.pc.addTrack(track, this.media);
          if (track.kind === "video") peer.pc._vsender = sender;
        }
      }
    }
    for (const from of Object.keys(this.pcs)) await this.offerTo(from);
  },

  onJoin(from) {
    const peer = this.pcs[from];
    if (peer && peer.pc.connectionState === "connected") return;
    this.newPeer(from);
    this.offerTo(from);
  },

  onLeave(from) {
    const peer = this.pcs[from];
    if (peer && peer.pc.connectionState !== "connected") this.drop(from);
  },

  async offerTo(from, restart) {
    const peer = this.pcs[from];
    if (!peer || !this.media) return;
    try {
      const offer = await peer.pc.createOffer(restart ? { iceRestart: true } : {});
      await peer.pc.setLocalDescription(offer);
      this.send(from, "offer", peer.pc.localDescription.toJSON());
    } catch {}
  },

  async onAnswer(from, data) {
    const peer = this.pcs[from];
    if (!peer) return;
    try {
      await peer.pc.setRemoteDescription(data);
      await this.flushQueue(peer);
    } catch {}
  },

  async flip() {
    if (!this.media) return;
    this.facing = this.facing === "environment" ? "user" : "environment";
    let fresh;
    try {
      fresh = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: this.facing },
      });
    } catch {
      return;
    }
    const track = fresh.getVideoTracks()[0];
    this.videoTrack = track;
    try {
      if (this._fps) track.applyConstraints({ frameRate: { max: this._fps } }).catch(() => {});
    } catch {}
    for (const peer of Object.values(this.pcs)) {
      // a null sender (sound-only viewer) still gets the new track on video on
      if (peer.pc._vsender?.track) peer.pc._vsender.replaceTrack(track);
    }
    this.sendCtlAll({ t: "facing", value: this.facing });
    const old = this.media.getVideoTracks()[0];
    if (old) {
      this.media.removeTrack(old);
      old.stop();
    }
    this.media.addTrack(track);
    const preview = this.el.querySelector("[data-rtc=preview]");
    if (preview) preview.srcObject = this.media;
  },

  onReplaced() {
    this.stopAll();
    this.setState("replaced");
  },

  stopAll() {
    for (const track of this.media?.getTracks() || []) track.stop();
    this.media = null;
    for (const from of Object.keys(this.pcs)) this.drop(from);
  },

  // --- viewer side ---

  onCamPresent(present) {
    if (present) {
      if (this.connected().length === 0) this.setState("connecting");
    } else if (this.connected().length === 0) {
      this.setState("waiting");
    }
  },

  async onOffer(from, data) {
    for (const other of Object.keys(this.pcs)) if (other !== from) this.drop(other);
    // An ICE restart offer comes from the same cam pc (same DTLS fingerprint): keep our pc.
    const fingerprint = (sdp) => sdp?.match(/a=fingerprint:\S+ \S+/)?.[0];
    const current = this.pcs[from];
    const same =
      current &&
      current.pc.signalingState === "stable" &&
      fingerprint(current.pc.remoteDescription?.sdp) === fingerprint(data.sdp);
    const peer = same ? current : this.newPeer(from);
    try {
      await peer.pc.setRemoteDescription(data);
      await this.flushQueue(peer);
      // talk-back: accept audio both ways so replaceTrack needs no renegotiation
      for (const t of peer.pc.getTransceivers()) {
        if (t.receiver.track?.kind === "audio") t.direction = "sendrecv";
      }
      const answer = await peer.pc.createAnswer();
      await peer.pc.setLocalDescription(answer);
      this.send(from, "answer", peer.pc.localDescription.toJSON());
    } catch {}
  },

  tickLive() {
    const m = Math.floor((Date.now() - this.liveSince) / 60000);
    this.out.liveFor?.(m < 1 ? "" : m < 60 ? `${m} m` : `${Math.floor(m / 60)} h ${m % 60} m`);
  },

  onTrack(e) {
    if (this.role === "cam" && e.track.kind === "audio") {
      // a viewer's talk-back mic: play it and show a Talking pill
      const audio = this.el.querySelector("[data-rtc=talk]");
      if (audio && audio.srcObject !== e.streams[0]) {
        audio.srcObject = e.streams[0];
        audio.play().catch(() => this.out.talkBlocked?.(true));
      }
      e.track.onunmute = () => this.out.talking?.(true);
      e.track.onmute = () => this.out.talking?.(false);
      return;
    }
    const video = this.el.querySelector("[data-rtc=remote]");
    if (video && video.srcObject !== e.streams[0]) video.srcObject = e.streams[0];
    if (e.streams[0]) app.sound.attach?.(e.streams[0]);
    this.setState("live");
  },

  setMuted(muted) {
    this.muted = muted;
    const video = this.el.querySelector("[data-rtc=remote]");
    if (video) {
      video.muted = muted;
      if (!muted) video.play().catch(() => {});
    }
    this.out.muted?.(muted);
  },

  leave() {
    this.stopAll();
    location.assign("/");
  },
};
