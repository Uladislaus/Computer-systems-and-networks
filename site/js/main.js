(() => {
  const canvas = document.getElementById("aurora");
  const ctx = canvas.getContext("2d", { alpha: false });
  const progress = document.getElementById("progress");
  const cursor = document.getElementById("cursor");
  const cursorRing = document.getElementById("cursor-ring");
  const soundBtn = document.getElementById("sound");
  const rail = document.getElementById("rail");
  const join = document.getElementById("join");
  const joinStatus = document.getElementById("join-status");
  const beats = [...document.querySelectorAll(".beat")];
  const magnetic = [...document.querySelectorAll("[data-magnetic]")];

  const isTouch = matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;
  if (isTouch) document.body.classList.add("is-touch");

  let width = 0;
  let height = 0;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  let mouse = { x: 0.5, y: 0.4, tx: 0.5, ty: 0.4 };
  let scrollIntensity = 0;
  let time = 0;
  let audioCtx = null;
  let masterGain = null;
  let oscillators = [];
  let soundOn = false;

  const ribbons = [
    { amp: 0.22, speed: 0.22, hue: 155, thick: 0.28, phase: 0.0 },
    { amp: 0.14, speed: 0.31, hue: 175, thick: 0.18, phase: 1.7 },
    { amp: 0.11, speed: 0.17, hue: 130, thick: 0.26, phase: 3.1 },
    { amp: 0.09, speed: 0.41, hue: 195, thick: 0.14, phase: 4.4 },
  ];

  const stars = Array.from({ length: 120 }, () => ({
    x: Math.random(),
    y: Math.random() * 0.7,
    r: Math.random() * 1.4 + 0.2,
    a: Math.random() * 0.6 + 0.15,
    tw: Math.random() * Math.PI * 2,
  }));

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawBackground() {
    const g = ctx.createLinearGradient(0, 0, 0, height);
    g.addColorStop(0, "#03080d");
    g.addColorStop(0.45, "#061018");
    g.addColorStop(1, "#0a1a16");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);

    for (const s of stars) {
      const twinkle = 0.55 + Math.sin(time * 1.4 + s.tw) * 0.45;
      ctx.beginPath();
      ctx.fillStyle = `rgba(230, 245, 255, ${s.a * twinkle})`;
      ctx.arc(s.x * width, s.y * height, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function ribbonY(xNorm, ribbon, t) {
    const wind = (mouse.x - 0.5) * 0.35;
    const lift = (0.5 - mouse.y) * 0.2;
    const scrollLift = scrollIntensity * 0.18;
    return (
      0.38 +
      lift +
      scrollLift +
      Math.sin(xNorm * 3.2 + t * ribbon.speed + ribbon.phase + wind) * ribbon.amp +
      Math.sin(xNorm * 7.5 - t * ribbon.speed * 1.4 + ribbon.phase) * ribbon.amp * 0.35
    );
  }

  function drawRibbons() {
    for (const ribbon of ribbons) {
      const band = height * ribbon.thick;
      for (let layer = 0; layer < 3; layer++) {
        ctx.beginPath();
        const steps = Math.ceil(width / 10);
        for (let i = 0; i <= steps; i++) {
          const x = (i / steps) * width;
          const n = i / steps;
          const y = ribbonY(n, ribbon, time + layer * 0.2) * height + layer * 8;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        for (let i = steps; i >= 0; i--) {
          const x = (i / steps) * width;
          const n = i / steps;
          const y = ribbonY(n, ribbon, time + layer * 0.2) * height + band * (0.55 - layer * 0.1);
          ctx.lineTo(x, y);
        }
        ctx.closePath();

        const alpha = (0.16 - layer * 0.03) * (0.85 + scrollIntensity * 0.7);
        ctx.fillStyle = `hsla(${ribbon.hue + mouse.x * 20}, 90%, ${58 - layer * 6}%, ${alpha})`;
        ctx.fill();
      }
    }

    const glow = ctx.createRadialGradient(
      mouse.x * width,
      mouse.y * height * 0.7,
      0,
      mouse.x * width,
      mouse.y * height * 0.7,
      width * 0.45
    );
    glow.addColorStop(0, "rgba(61, 255, 181, 0.22)");
    glow.addColorStop(0.45, "rgba(126, 200, 255, 0.1)");
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);
  }

  function frame(now) {
    time = now * 0.001;
    mouse.x += (mouse.tx - mouse.x) * 0.06;
    mouse.y += (mouse.ty - mouse.y) * 0.06;
    drawBackground();
    drawRibbons();
    requestAnimationFrame(frame);
  }

  function updateScroll() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? window.scrollY / max : 0;
    progress.style.width = `${ratio * 100}%`;
    scrollIntensity = Math.min(1, window.scrollY / (window.innerHeight * 1.2));

    beats.forEach((beat) => {
      const rect = beat.getBoundingClientRect();
      const mid = rect.top + rect.height * 0.5;
      const on = mid > window.innerHeight * 0.18 && mid < window.innerHeight * 0.78;
      beat.classList.toggle("is-on", on);
    });
  }

  function setupReveals() {
    const nodes = document.querySelectorAll(
      ".chapter__sticky, .places__head, .ritual__title, .ritual__item, .finale__inner, .place"
    );
    nodes.forEach((node) => node.classList.add("reveal"));
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    nodes.forEach((node) => io.observe(node));
  }

  function setupCursor() {
    if (isTouch) return;
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let rx = x;
    let ry = y;

    window.addEventListener(
      "pointermove",
      (e) => {
        x = e.clientX;
        y = e.clientY;
        mouse.tx = e.clientX / width;
        mouse.ty = e.clientY / height;
        cursor.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
      },
      { passive: true }
    );

    const tick = () => {
      rx += (x - rx) * 0.18;
      ry += (y - ry) * 0.18;
      cursorRing.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%)`;
      requestAnimationFrame(tick);
    };
    tick();

    document.querySelectorAll("a, button, input, .place").forEach((el) => {
      el.addEventListener("pointerenter", () => document.body.classList.add("is-hover"));
      el.addEventListener("pointerleave", () => document.body.classList.remove("is-hover"));
    });
  }

  function setupMagnetic() {
    if (isTouch) return;
    magnetic.forEach((el) => {
      el.addEventListener("pointermove", (e) => {
        const rect = el.getBoundingClientRect();
        const dx = e.clientX - (rect.left + rect.width / 2);
        const dy = e.clientY - (rect.top + rect.height / 2);
        el.style.transform = `translate(${dx * 0.2}px, ${dy * 0.25}px)`;
      });
      el.addEventListener("pointerleave", () => {
        el.style.transform = "";
      });
    });
  }

  function setupRail() {
    let down = false;
    let startX = 0;
    let scrollLeft = 0;

    rail.addEventListener("pointerdown", (e) => {
      down = true;
      rail.classList.add("is-dragging");
      startX = e.clientX;
      scrollLeft = rail.scrollLeft;
      rail.setPointerCapture(e.pointerId);
    });

    rail.addEventListener("pointermove", (e) => {
      if (!down) return;
      const walk = (e.clientX - startX) * 1.2;
      rail.scrollLeft = scrollLeft - walk;
    });

    const stop = () => {
      down = false;
      rail.classList.remove("is-dragging");
    };

    rail.addEventListener("pointerup", stop);
    rail.addEventListener("pointercancel", stop);
  }

  function ensureAudio() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    masterGain = audioCtx.createGain();
    masterGain.gain.value = 0.0001;
    masterGain.connect(audioCtx.destination);

    const freqs = [98, 146.8, 196, 246.9];
    oscillators = freqs.map((freq, i) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      const filter = audioCtx.createBiquadFilter();
      osc.type = i % 2 === 0 ? "sine" : "triangle";
      osc.frequency.value = freq;
      filter.type = "lowpass";
      filter.frequency.value = 600;
      gain.gain.value = 0.03 - i * 0.004;
      osc.connect(filter);
      filter.connect(gain);
      gain.connect(masterGain);
      osc.start();
      return { osc, gain, filter };
    });

    const lfo = audioCtx.createOscillator();
    const lfoGain = audioCtx.createGain();
    lfo.frequency.value = 0.05;
    lfoGain.gain.value = 40;
    lfo.connect(lfoGain);
    oscillators.forEach(({ filter }) => lfoGain.connect(filter.frequency));
    lfo.start();
  }

  async function toggleSound() {
    ensureAudio();
    if (audioCtx.state === "suspended") await audioCtx.resume();
    soundOn = !soundOn;
    soundBtn.setAttribute("aria-pressed", String(soundOn));
    const now = audioCtx.currentTime;
    masterGain.gain.cancelScheduledValues(now);
    masterGain.gain.linearRampToValueAtTime(soundOn ? 0.22 : 0.0001, now + 1.2);
  }

  soundBtn.addEventListener("click", () => {
    toggleSound().catch(() => {});
  });

  join.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = new FormData(join).get("email")?.toString().trim() || "";
    if (!email || !email.includes("@")) {
      joinStatus.textContent = "Нужен настоящий email.";
      return;
    }
    joinStatus.textContent = "Ты в листе. Когда небо откроется — напишем.";
    join.reset();
  });

  window.addEventListener("resize", resize, { passive: true });
  window.addEventListener("scroll", updateScroll, { passive: true });

  resize();
  updateScroll();
  setupReveals();
  setupCursor();
  setupMagnetic();
  setupRail();
  requestAnimationFrame(frame);
})();
