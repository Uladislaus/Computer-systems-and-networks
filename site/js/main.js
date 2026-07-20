(() => {
  const canvas = document.getElementById("aurora");
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
  let mouse = { x: 0.5, y: 0.42, tx: 0.5, ty: 0.42 };
  let scrollIntensity = 0;
  let audioCtx = null;
  let masterGain = null;
  let soundOn = false;

  /* ---------- WebGL sky ---------- */
  const vertSrc = `
    attribute vec2 a_pos;
    void main() {
      gl_Position = vec4(a_pos, 0.0, 1.0);
    }
  `;

  const fragSrc = `
    precision highp float;

    uniform vec2 u_res;
    uniform float u_time;
    uniform vec2 u_mouse;
    uniform float u_scroll;

    float hash(vec2 p) {
      p = fract(p * vec2(123.34, 456.21));
      p += dot(p, p + 45.32);
      return fract(p.x * p.y);
    }

    float noise(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      float a = hash(i);
      float b = hash(i + vec2(1.0, 0.0));
      float c = hash(i + vec2(0.0, 1.0));
      float d = hash(i + vec2(1.0, 1.0));
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
    }

    float fbm(vec2 p) {
      float v = 0.0;
      float a = 0.5;
      mat2 m = mat2(0.8, -0.6, 0.6, 0.8);
      for (int i = 0; i < 5; i++) {
        v += a * noise(p);
        p = m * p * 2.0;
        a *= 0.5;
      }
      return v;
    }

    float auroraBand(vec2 uv, float y, float thick, float speed, float seed) {
      float wind = (u_mouse.x - 0.5) * 1.8;
      float lift = (0.55 - u_mouse.y) * 0.35 + u_scroll * 0.2;
      float n = fbm(vec2(uv.x * 2.4 + u_time * speed + wind + seed, seed * 3.1 + u_time * 0.05));
      float wavy = y + lift + (n - 0.5) * 0.55;
      float d = abs(uv.y - wavy);
      float core = smoothstep(thick, 0.0, d);
      float veil = smoothstep(thick * 2.8, 0.0, d) * 0.45;
      float curtains = pow(max(0.0, fbm(vec2(uv.x * 8.0 - u_time * speed * 1.4, uv.y * 3.0 + seed)) - 0.28), 1.6);
      return (core + veil) * (0.55 + curtains * 1.4);
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float aspect = u_res.x / max(u_res.y, 1.0);
      vec2 p = uv;
      p.x *= aspect;

      // Deep arctic night
      vec3 skyTop = vec3(0.01, 0.03, 0.07);
      vec3 skyMid = vec3(0.02, 0.07, 0.1);
      vec3 skyBot = vec3(0.015, 0.05, 0.045);
      vec3 col = mix(skyBot, skyMid, smoothstep(0.0, 0.45, uv.y));
      col = mix(col, skyTop, smoothstep(0.4, 1.0, uv.y));

      // Soft horizon glow
      float horizon = exp(-abs(uv.y - 0.18) * 8.0) * 0.12;
      col += vec3(0.05, 0.12, 0.14) * horizon;

      // Stars
      vec2 starUv = uv * vec2(u_res.x / 90.0, u_res.y / 90.0);
      float star = step(0.995, hash(floor(starUv)));
      float twinkle = 0.55 + 0.45 * sin(u_time * 2.0 + hash(floor(starUv)) * 40.0);
      float starMask = smoothstep(0.15, 0.75, uv.y);
      col += vec3(0.85, 0.92, 1.0) * star * twinkle * starMask * 0.9;

      // Distant milky dust
      float dust = fbm(uv * vec2(3.0, 6.0) + u_time * 0.01) * 0.08 * starMask;
      col += vec3(0.25, 0.35, 0.5) * dust;

      // Aurora curtains
      float a1 = auroraBand(uv, 0.52, 0.05, 0.07, 1.2);
      float a2 = auroraBand(uv, 0.62, 0.04, 0.11, 3.7);
      float a3 = auroraBand(uv, 0.44, 0.06, 0.05, 6.1);
      float a4 = auroraBand(uv, 0.70, 0.035, 0.14, 8.9);

      vec3 c1 = vec3(0.15, 0.95, 0.55);
      vec3 c2 = vec3(0.25, 0.75, 1.0);
      vec3 c3 = vec3(0.45, 1.0, 0.7);
      vec3 c4 = vec3(0.7, 0.45, 1.0);

      vec3 aurora =
        c1 * a1 * 0.85 +
        c2 * a2 * 0.7 +
        c3 * a3 * 0.55 +
        c4 * a4 * 0.35;

      // Vertical shafts
      float shafts = pow(max(0.0, fbm(vec2(uv.x * 14.0 + u_time * 0.08, uv.y * 0.8)) - 0.4), 2.0);
      aurora *= 0.75 + shafts * 1.1;

      // Mouse glow
      vec2 m = u_mouse;
      m.x *= aspect;
      float glow = exp(-length((p - m) * vec2(1.0, 1.4)) * 2.2) * 0.35;
      aurora += vec3(0.2, 0.9, 0.7) * glow;

      col += aurora * (0.85 + u_scroll * 0.35);

      // Vignette
      float vig = smoothstep(1.25, 0.35, length(uv - 0.5));
      col *= 0.72 + 0.28 * vig;

      // Mild grade
      col = pow(max(col, 0.0), vec3(0.95));
      gl_FragColor = vec4(col, 1.0);
    }
  `;

  function createShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error(gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  function initWebGL(canvasEl) {
    const gl = canvasEl.getContext("webgl", {
      antialias: false,
      alpha: false,
      powerPreference: "high-performance",
    });
    if (!gl) return null;

    const vs = createShader(gl, gl.VERTEX_SHADER, vertSrc);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, fragSrc);
    if (!vs || !fs) return null;

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(program));
      return null;
    }

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1, 1, -1, -1, 1,
      -1, 1, 1, -1, 1, 1,
    ]), gl.STATIC_DRAW);

    const aPos = gl.getAttribLocation(program, "a_pos");
    const uniforms = {
      res: gl.getUniformLocation(program, "u_res"),
      time: gl.getUniformLocation(program, "u_time"),
      mouse: gl.getUniformLocation(program, "u_mouse"),
      scroll: gl.getUniformLocation(program, "u_scroll"),
    };

    return { gl, program, aPos, uniforms, buffer };
  }

  const sky = initWebGL(canvas);
  const modeBadge = document.getElementById("render-mode");
  if (modeBadge) modeBadge.textContent = sky ? "WebGL небо" : "Canvas fallback";

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    if (sky) {
      sky.gl.viewport(0, 0, canvas.width, canvas.height);
    }
  }

  function frame(now) {
    const t = now * 0.001;
    mouse.x += (mouse.tx - mouse.x) * 0.05;
    mouse.y += (mouse.ty - mouse.y) * 0.05;

    if (sky) {
      const { gl, program, aPos, uniforms, buffer } = sky;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(uniforms.res, canvas.width, canvas.height);
      gl.uniform1f(uniforms.time, t);
      gl.uniform2f(uniforms.mouse, mouse.x, 1.0 - mouse.y);
      gl.uniform1f(uniforms.scroll, scrollIntensity);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }

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
        mouse.tx = e.clientX / Math.max(width, 1);
        mouse.ty = e.clientY / Math.max(height, 1);
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
    const oscillators = freqs.map((freq, i) => {
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
      return { filter };
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
