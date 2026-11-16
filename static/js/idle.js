window.app ??= {};
// Idle chrome: report visible again on every poke, hidden after the delay.
app.idle = (el, write) => {
  const delay = Number(el.dataset.idle || 4000);
  let timer = null;
  return {
    poke() {
      write(true);
      clearTimeout(timer);
      timer = setTimeout(() => write(false), delay);
    },
  };
};
