window.app ??= {};
app.share = {
  // The code in what a person pasted: a watch link, "482 913", or "482-913".
  code(text) {
    const link = /\/(?:watch|cam)\/(\d{6})(?!\d)/.exec(text);
    return link ? link[1] : text.replace(/\D/g, "").slice(0, 6);
  },

  // A phone opens the system share sheet. A desktop browser copies the link
  // in the same click, then opens the sheet when the browser has one.
  send(url, done) {
    const href = new URL(url, location.origin).href;
    const mark = (state) => {
      done(state);
      setTimeout(() => done(false), 1600);
    };
    const phone = window.matchMedia("(pointer: coarse)").matches;
    if (phone && this.can(href)) {
      this.sheet(href, mark);
      return;
    }
    if (this.can(href)) this.sheet(href, mark);
    this.copy(href, mark);
  },

  can(href) {
    if (typeof navigator.share !== "function") return false;
    if (typeof navigator.canShare !== "function") return true;
    try {
      return navigator.canShare({ title: "Philomena", url: href });
    } catch {
      return false;
    }
  },

  sheet(href, mark) {
    let task;
    try {
      task = navigator.share({ title: "Philomena", url: href });
    } catch {
      this.copy(href, mark);
      return;
    }
    Promise.resolve(task).then(
      () => mark("shared"),
      (err) => {
        if (err && err.name === "AbortError") return;
        this.copy(href, mark);
      },
    );
  },

  copyLink(url, done) {
    const href = new URL(url, location.origin).href;
    const mark = (state) => {
      done(state);
      setTimeout(() => done(false), 1600);
    };
    this.copy(href, mark);
  },

  copy(href, mark) {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(href).then(
        () => mark("copied"),
        () => {
          if (this.copySync(href)) mark("copied");
        },
      );
      return;
    }
    if (this.copySync(href)) mark("copied");
  },

  copySync(href) {
    const input = document.createElement("textarea");
    input.value = href;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.top = "0";
    input.style.left = "0";
    input.style.width = "1px";
    input.style.height = "1px";
    input.style.padding = "0";
    input.style.border = "none";
    input.style.outline = "none";
    input.style.boxShadow = "none";
    input.style.background = "transparent";
    document.body.appendChild(input);
    input.focus();
    input.select();
    input.setSelectionRange(0, href.length);
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    input.remove();
    return ok;
  },
};
