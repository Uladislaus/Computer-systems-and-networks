(() => {
  const canvas = document.getElementById("aurora");
  const progress = document.getElementById("progress");
  const cursor = document.getElementById("cursor");
  const cursorRing = document.getElementById("cursor-ring");
  const soundBtn = document.getElementById("sound");
  const rail = document.getElementById("rail");
  const join = document.getElementById("join");
  const joinStatus = document.getElementById("join-status");
  const worldLabel = document.getElementById("world-label");
  const layerDots = [...document.querySelectorAll(".altimeter__track i")];
  const beats = [...document.querySelectorAll(".beat")];
  const magnetic = [...document.querySelectorAll("[data-magnetic]")];

  const isTouch = matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;
  if (isTouch) document.body.classList.add("is-touch");

  let width = 0;
  let height = 0;
  let mouse = { x: 0.5, y: 0.42, tx: 0.5, ty: 0.42 };
  let world = 0;
  let worldSmooth = 0;
  let audioCtx = null;
  let masterGain = null;
  let soundOn = false;

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
    uniform float u_world;

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
        p = m * p * 2.02;
        a *= 0.5;
      }
      return v;
    }

    float auroraBand(vec2 uv, float y, float thick, float speed, float seed) {
      float wind = (u_mouse.x - 0.5) * 1.4;
      float lift = (0.55 - u_mouse.y) * 0.28;
      float n = fbm(vec2(uv.x * 1.8 + u_time * speed + wind + seed, seed * 2.7));
      float wavy = y + lift + (n - 0.5) * 0.32;
      float d = abs(uv.y - wavy);
      float core = exp(-pow(d / max(thick * 0.35, 0.001), 2.0) * 4.0);
      float mid = exp(-pow(d / max(thick, 0.001), 2.0) * 2.2) * 0.55;
      float edge = exp(-pow(d / max(thick * 1.7, 0.001), 2.0)) * 0.2;
      float rays = smoothstep(0.42, 0.78, fbm(vec2(uv.x * 22.0 - u_time * speed * 2.0 + seed, uv.y * 1.2 + seed)));
      float drop = smoothstep(wavy + thick * 2.5, wavy - 0.02, uv.y) *
                   smoothstep(wavy - 0.55, wavy - 0.05, uv.y);
      return (core * 1.35 + mid + edge) * (0.35 + rays * 1.4) * (0.25 + drop * 1.1);
    }

    vec3 skyBiome(vec2 uv, float aspect) {
      vec3 col = mix(vec3(0.01, 0.025, 0.04), vec3(0.004, 0.01, 0.03), uv.y);

      vec2 starUv = uv * vec2(u_res.x / 70.0, u_res.y / 70.0);
      vec2 cell = floor(starUv);
      float star = step(0.997, hash(cell));
      float twinkle = 0.65 + 0.35 * sin(u_time * 3.0 + hash(cell) * 50.0);
      col += vec3(0.9, 0.95, 1.0) * star * twinkle * smoothstep(0.2, 0.8, uv.y);

      float a1 = auroraBand(uv, 0.50, 0.028, 0.06, 1.2);
      float a2 = auroraBand(uv, 0.58, 0.022, 0.10, 3.7);
      float a3 = auroraBand(uv, 0.42, 0.032, 0.045, 6.1);
      float a4 = auroraBand(uv, 0.66, 0.018, 0.13, 8.9);

      vec3 aurora =
        vec3(0.2, 1.0, 0.55) * a1 * 1.15 +
        vec3(0.15, 0.85, 1.0) * a2 * 0.95 +
        vec3(0.55, 1.0, 0.65) * a3 * 0.7 +
        vec3(0.75, 0.4, 1.0) * a4 * 0.45;

      vec2 p = vec2(uv.x * aspect, uv.y);
      vec2 m = vec2(u_mouse.x * aspect, u_mouse.y);
      aurora += vec3(0.25, 1.0, 0.75) * exp(-length((p - m) * vec2(1.6, 2.2)) * 5.0) * 0.22;
      col += aurora;
      return col;
    }

    float mountainHeight(float x) {
      float h = 0.0;
      h += 0.22 * sin(x * 3.1 + 0.4);
      h += 0.14 * sin(x * 6.7 + 1.7);
      h += 0.08 * sin(x * 13.0 + 0.2);
      h += 0.05 * fbm(vec2(x * 2.4, 2.0));
      return 0.18 + h * 0.55;
    }

    vec3 ridgeBiome(vec2 uv, float aspect) {
      // Cold dawn above ridges
      vec3 zenith = vec3(0.18, 0.28, 0.42);
      vec3 horizon = vec3(0.72, 0.48, 0.32);
      vec3 snow = vec3(0.82, 0.88, 0.92);
      vec3 col = mix(horizon, zenith, smoothstep(0.15, 0.85, uv.y));
      col = mix(col, snow * 0.55, exp(-abs(uv.y - 0.28) * 10.0) * 0.35);

      // Wind streaks
      float wind = fbm(vec2(uv.x * 3.0 - u_time * 0.35 + u_mouse.x, uv.y * 18.0));
      float streaks = smoothstep(0.55, 0.8, wind) * smoothstep(0.2, 0.7, uv.y) * (1.0 - smoothstep(0.75, 1.0, uv.y));
      col += vec3(0.95, 0.97, 1.0) * streaks * 0.18;

      // Layered mountain silhouettes
      for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float parallax = u_mouse.x * (0.02 + fi * 0.015);
        float x = uv.x * aspect * (1.0 + fi * 0.15) + parallax + fi * 1.7;
        float ridge = mountainHeight(x) * (0.85 - fi * 0.18) + fi * 0.04;
        float mask = smoothstep(ridge, ridge - 0.01, uv.y);
        vec3 rock = mix(vec3(0.08, 0.1, 0.14), vec3(0.22, 0.2, 0.2), fi / 2.0);
        rock = mix(rock, vec3(0.55, 0.6, 0.65), smoothstep(ridge - 0.08, ridge, uv.y) * 0.45);
        col = mix(col, rock, mask * (0.95 - fi * 0.12));
      }

      // Valley fog
      float fog = exp(-uv.y * 4.5) * 0.35;
      col = mix(col, vec3(0.55, 0.6, 0.68), fog);
      return col;
    }

    vec3 seaBiome(vec2 uv, float aspect) {
      float mouseLift = (0.5 - u_mouse.y) * 0.04;
      vec3 deep = vec3(0.01, 0.05, 0.1);
      vec3 mid = vec3(0.02, 0.18, 0.28);
      vec3 foamCol = vec3(0.75, 0.9, 0.95);
      vec3 col = mix(deep, mid, smoothstep(0.0, 0.7, uv.y));

      // Far ocean horizon band
      float horizon = exp(-abs(uv.y - 0.62) * 18.0);
      col += vec3(0.15, 0.35, 0.45) * horizon * 0.5;

      // Animated wave field
      float waves = 0.0;
      float foam = 0.0;
      for (int i = 0; i < 4; i++) {
        float fi = float(i);
        float freq = 4.0 + fi * 3.5;
        float amp = 0.035 / (1.0 + fi * 0.55);
        float speed = 0.55 + fi * 0.25;
        float phase = u_time * speed + uv.x * aspect * freq + fi * 2.1 + u_mouse.x * 1.5;
        float y = 0.22 + fi * 0.09 + mouseLift + sin(phase) * amp + sin(phase * 1.7 + uv.x * 2.0) * amp * 0.45;
        float d = uv.y - y;
        float crest = exp(-pow(d * (28.0 + fi * 10.0), 2.0));
        waves += crest * (0.55 - fi * 0.08);
        foam += smoothstep(0.02, 0.0, abs(d)) * smoothstep(0.3, 0.8, sin(phase * 2.0) * 0.5 + 0.5) * (0.35 - fi * 0.05);
      }

      // Choppy surface noise
      float chop = fbm(vec2(uv.x * aspect * 8.0 - u_time * 0.4, uv.y * 14.0 + u_time * 0.15));
      waves += chop * 0.08 * smoothstep(0.55, 0.05, uv.y);

      col += vec3(0.1, 0.45, 0.55) * waves;
      col = mix(col, foamCol, clamp(foam, 0.0, 1.0));

      // Depth darkening toward bottom
      col *= 0.55 + 0.45 * smoothstep(0.0, 0.45, uv.y);
      return col;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float aspect = u_res.x / max(u_res.y, 1.0);

      vec3 sky = skyBiome(uv, aspect);
      vec3 ridge = ridgeBiome(uv, aspect);
      vec3 sea = seaBiome(uv, aspect);

      // Continuous descent: sky -> ridge -> sea
      float w = clamp(u_world, 0.0, 1.0);
      float toRidge = smoothstep(0.12, 0.42, w);
      float toSea = smoothstep(0.48, 0.78, w);

      vec3 col = mix(sky, ridge, toRidge);
      col = mix(col, sea, toSea);

      float vig = smoothstep(1.35, 0.25, length(uv - 0.5));
      col *= 0.9 + 0.1 * vig;
      col = (col - 0.5) * 1.08 + 0.5;
      col = clamp(col, 0.0, 1.0);
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
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW
    );

    return {
      gl,
      program,
      aPos: gl.getAttribLocation(program, "a_pos"),
      uniforms: {
        res: gl.getUniformLocation(program, "u_res"),
        time: gl.getUniformLocation(program, "u_time"),
        mouse: gl.getUniformLocation(program, "u_mouse"),
        world: gl.getUniformLocation(program, "u_world"),
      },
      buffer,
    };
  }

  const sky = initWebGL(canvas);
  const modeBadge = document.getElementById("render-mode");
  if (modeBadge) modeBadge.textContent = sky ? "WebGL мир" : "fallback";

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    if (sky) sky.gl.viewport(0, 0, canvas.width, canvas.height);
  }

  function worldName(w) {
    if (w < 0.35) return { id: "sky", label: "слой · небо" };
    if (w < 0.68) return { id: "ridge", label: "слой · горы" };
    return { id: "sea", label: "слой · океан" };
  }

  function updateWorldUI(w) {
    const info = worldName(w);
    document.body.dataset.world = info.id;
    if (worldLabel) worldLabel.textContent = info.label;
    layerDots.forEach((dot) => {
      dot.classList.toggle("is-on", dot.dataset.layer === info.id);
    });
  }

  function frame(now) {
    const t = now * 0.001;
    mouse.x += (mouse.tx - mouse.x) * 0.05;
    mouse.y += (mouse.ty - mouse.y) * 0.05;
    worldSmooth += (world - worldSmooth) * 0.06;

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
      gl.uniform1f(uniforms.world, worldSmooth);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }

    requestAnimationFrame(frame);
  }

  function updateScroll() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    world = max > 0 ? window.scrollY / max : 0;
    progress.style.width = `${world * 100}%`;
    updateWorldUI(world);

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
    if (!rail) return;
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
      rail.scrollLeft = scrollLeft - (e.clientX - startX) * 1.2;
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
    joinStatus.textContent = "След оставлен. Мир тебя помнит.";
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
