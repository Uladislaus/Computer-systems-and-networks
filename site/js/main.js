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
      float lift = (0.55 - u_mouse.y) * 0.22;
      float n = fbm(vec2(uv.x * 1.8 + u_time * speed + wind + seed, seed * 2.7));
      float wavy = y + lift + (n - 0.5) * 0.28;
      float d = abs(uv.y - wavy);
      float core = exp(-pow(d / max(thick * 0.35, 0.001), 2.0) * 4.0);
      float mid = exp(-pow(d / max(thick, 0.001), 2.0) * 2.2) * 0.55;
      float edge = exp(-pow(d / max(thick * 1.7, 0.001), 2.0)) * 0.22;
      float rays = smoothstep(0.4, 0.78, fbm(vec2(uv.x * 22.0 - u_time * speed * 2.0 + seed, uv.y * 1.2 + seed)));
      float drop = smoothstep(wavy + thick * 2.5, wavy - 0.02, uv.y) *
                   smoothstep(wavy - 0.55, wavy - 0.05, uv.y);
      return (core * 1.45 + mid + edge) * (0.4 + rays * 1.35) * (0.3 + drop * 1.05);
    }

    vec3 sampleAurora(vec2 uv, float aspect) {
      float a1 = auroraBand(uv, 0.38, 0.03, 0.06, 1.2);
      float a2 = auroraBand(uv, 0.48, 0.024, 0.10, 3.7);
      float a3 = auroraBand(uv, 0.30, 0.034, 0.045, 6.1);
      float a4 = auroraBand(uv, 0.56, 0.02, 0.13, 8.9);
      vec3 aurora =
        vec3(0.2, 1.0, 0.55) * a1 * 1.25 +
        vec3(0.15, 0.85, 1.0) * a2 * 1.05 +
        vec3(0.55, 1.0, 0.65) * a3 * 0.8 +
        vec3(0.85, 0.35, 1.0) * a4 * 0.65;
      vec2 p = vec2(uv.x * aspect, uv.y);
      vec2 m = vec2(u_mouse.x * aspect, u_mouse.y);
      aurora += vec3(0.25, 1.0, 0.75) * exp(-length((p - m) * vec2(1.6, 2.2)) * 5.0) * 0.2;
      return aurora;
    }

    float mountainHeight(float x, float seed) {
      float h = 0.0;
      h += 0.30 * sin(x * 2.2 + seed);
      h += 0.18 * sin(x * 4.8 + seed * 2.1);
      h += 0.10 * sin(x * 9.5 + seed * 0.7);
      h += 0.08 * fbm(vec2(x * 1.6 + seed, seed));
      return max(h, 0.0);
    }

    // One sharp "hero" distant peak — white summit far away
    float farPeak(float x) {
      float d = abs(x - 0.15);
      return exp(-d * d * 18.0) * 0.55 + exp(-abs(x + 0.55) * abs(x + 0.55) * 40.0) * 0.22;
    }

    // Perspective mountain ranges: near dark ridges → mid haze → far pale → white summit
    // groundY: where foothills meet (0 = bottom). rise: 0..1 how much ranges are visible.
    // Returns color over skyCol for fragments that hit rock; mixes haze between layers.
    vec3 paintMountains(vec2 uv, float aspect, float rise, vec3 skyCol, float groundY) {
      if (rise < 0.01) return skyCol;
      vec3 col = skyCol;
      float mousePar = (u_mouse.x - 0.5);

      // Draw far → near so near occludes
      // layer 0 = farthest (white peak), layer 5 = nearest foothills
      for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float farness = 1.0 - fi / 5.0;          // 1 = distant, 0 = near
        float t = fi / 5.0;                      // 0 = far, 1 = near

        float parallax = mousePar * mix(0.02, 0.1, t);
        float xScale = mix(1.05, 1.55, t);
        float x = (uv.x + parallax) * aspect * xScale + fi * 1.9 + 0.4;

        // Perspective: distant ridges sit higher (toward horizon), near ones fill lower frame
        float base = mix(0.52, 0.18, pow(t, 0.85)) + groundY * mix(0.0, 0.08, t);
        float amp = mix(0.1, 0.38, pow(t, 0.75));
        float ridge = base + mountainHeight(x, 1.3 + fi * 1.7) * amp;

        // Add the white distant peak mainly on farthest layers
        if (i <= 1) {
          float px = (uv.x + mousePar * 0.02) * 2.0 - 1.0;
          ridge += farPeak(px) * mix(0.22, 0.08, fi) * rise;
        }

        ridge = mix(groundY - 0.2, ridge, rise);

        if (uv.y < ridge) {
          // Atmospheric perspective colors
          vec3 nearRock = vec3(0.14, 0.12, 0.12);
          vec3 midRock = vec3(0.28, 0.27, 0.3);
          vec3 farRock = vec3(0.52, 0.56, 0.62);
          vec3 haze = vec3(0.7, 0.75, 0.82);
          vec3 rock = mix(haze, mix(farRock, mix(midRock, nearRock, smoothstep(0.35, 1.0, t)), smoothstep(0.0, 0.55, t)), 0.85);

          // Slope shading
          float nx = mountainHeight(x + 0.015, 1.3 + fi * 1.7) - mountainHeight(x - 0.015, 1.3 + fi * 1.7);
          rock *= 0.72 + 0.4 * clamp(0.55 - nx * 2.8, 0.0, 1.0);

          // Snow: stronger on far/high peaks, bright white on the hero summit
          float heightFrac = clamp((uv.y - (ridge - amp)) / max(amp, 0.001), 0.0, 1.0);
          float snow = smoothstep(0.45, 0.82, heightFrac) * mix(0.95, 0.25, t);
          // Extra white cap on distant peak silhouette
          if (i == 0) {
            float px = (uv.x + mousePar * 0.02) * 2.0 - 1.0;
            snow = max(snow, farPeak(px) * smoothstep(ridge - 0.08, ridge, uv.y) * 1.4);
          }
          rock = mix(rock, vec3(0.93, 0.96, 1.0), clamp(snow, 0.0, 1.0));

          // Soft layer edge
          float edge = smoothstep(ridge, ridge - 0.01, uv.y);
          col = mix(col, rock, edge);

          // Haze veil between ranges (stronger for farther gaps)
          float veil = exp(-(ridge - uv.y) * mix(8.0, 3.0, t)) * mix(0.35, 0.05, t);
          col = mix(col, haze, veil * 0.35);
        }
      }

      // Valley fog near ground
      float fog = exp(-(uv.y - groundY) * 4.0) * 0.4 * rise;
      col = mix(col, vec3(0.62, 0.66, 0.72), clamp(fog, 0.0, 0.5));
      return col;
    }

    // Perspective ocean: near (bottom) = big waves + foam, far = dense ripples, horizon = mountain ranges
    vec3 oceanScene(vec2 uv, float aspect, float waterLine, float mtAmt) {
      vec3 sky = mix(vec3(0.55, 0.7, 0.82), vec3(0.12, 0.22, 0.38), pow(clamp((uv.y - waterLine) / max(1.0 - waterLine, 0.001), 0.0, 1.0), 0.85));
      vec3 col = sky;

      // Mountain ranges beyond the water — same perspective system, seated on horizon
      if (uv.y >= waterLine) {
        col = paintMountains(uv, aspect, mtAmt, sky, waterLine);
        col = mix(col, vec3(0.45, 0.6, 0.7), exp(-abs(uv.y - waterLine) * 40.0) * 0.4);
        return col;
      }

      float depth = clamp((waterLine - uv.y) / max(waterLine, 0.001), 0.0, 1.0);
      float persp = pow(depth, 1.35);

      vec3 deep = vec3(0.01, 0.07, 0.12);
      vec3 mid = vec3(0.02, 0.2, 0.3);
      vec3 shallow = vec3(0.05, 0.32, 0.4);
      col = mix(mix(shallow, mid, persp), deep, pow(persp, 1.2));
      col += vec3(0.25, 0.4, 0.5) * exp(-depth * 14.0) * 0.35;

      float waves = 0.0;
      float foam = 0.0;
      for (int i = 0; i < 12; i++) {
        float fi = float(i);
        float t = (fi + 1.0) / 12.0;
        float rowDepth = pow(t, 1.55);
        float row = waterLine - rowDepth * waterLine * 0.98;
        float dens = mix(28.0, 3.5, rowDepth);
        float amp = mix(0.004, 0.028, rowDepth);
        float speed = mix(1.4, 0.55, rowDepth);
        float phase = uv.x * aspect * dens + u_time * speed + u_mouse.x * 1.8 + fi * 1.7;
        float y = row + sin(phase) * amp + sin(phase * 2.1 + fi) * amp * 0.35;
        float sharpness = mix(70.0, 18.0, rowDepth);
        float line = exp(-abs(uv.y - y) * sharpness);
        float crest = smoothstep(0.2, 0.95, sin(phase) * 0.5 + 0.5);
        waves += line * mix(0.25, 0.7, rowDepth);
        // Sea foam on crests — denser near camera
        foam += line * crest * mix(0.12, 0.85, rowDepth);
      }

      // Clumpy foam patches near the viewer (not spark rectangles)
      float foamPatch = fbm(vec2(uv.x * aspect * 3.5 - u_time * 0.15, uv.y * 6.0));
      foam += smoothstep(0.55, 0.8, foamPatch) * persp * 0.35;

      float chop = fbm(vec2(uv.x * aspect * mix(14.0, 4.0, persp) - u_time * 0.25, uv.y * mix(30.0, 8.0, persp)));
      col += vec3(0.12, 0.45, 0.55) * waves;
      col += vec3(0.04, 0.1, 0.12) * chop * persp * 0.35;
      col = mix(col, vec3(0.88, 0.95, 0.98), clamp(foam, 0.0, 0.85));

      col = mix(col, vec3(0.12, 0.14, 0.18), exp(-depth * 10.0) * 0.2 * mtAmt);
      return col;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float aspect = u_res.x / max(u_res.y, 1.0);
      float w = clamp(u_world, 0.0, 1.0);

      float mtRise = smoothstep(0.18, 0.52, w);
      float auroraAmt = 1.0 - smoothstep(0.28, 0.62, w);
      float dawnAmt = smoothstep(0.22, 0.58, w);
      float windAmt = smoothstep(0.25, 0.55, w) * (1.0 - smoothstep(0.7, 0.92, w));
      float waterAmt = smoothstep(0.52, 0.9, w);
      float waterLine = mix(-0.2, 0.58, waterAmt);

      // --- Sky base: night -> dawn ---
      vec3 night = mix(vec3(0.01, 0.025, 0.04), vec3(0.004, 0.01, 0.03), uv.y);
      vec3 dawn = mix(vec3(0.86, 0.62, 0.42), vec3(0.35, 0.48, 0.62), pow(uv.y, 0.85));
      dawn += vec3(1.0, 0.7, 0.35) * exp(-length(vec2((uv.x - 0.72) * aspect, uv.y - 0.4) * vec2(2.2, 3.5)) * 3.5) * 0.5;
      vec3 col = mix(night, dawn, dawnAmt);

      vec2 cell = floor(uv * vec2(u_res.x / 70.0, u_res.y / 70.0));
      float star = step(0.997, hash(cell)) * (1.0 - dawnAmt);
      col += vec3(0.9, 0.95, 1.0) * star * (0.65 + 0.35 * sin(u_time * 3.0 + hash(cell) * 50.0));

      col += sampleAurora(uv, aspect) * auroraAmt;

      float wind = fbm(vec2(uv.x * 2.2 - u_time * 0.45 + u_mouse.x * 0.8, uv.y * 22.0));
      col += vec3(1.0, 0.98, 0.94) * smoothstep(0.62, 0.85, wind) * smoothstep(0.35, 0.8, uv.y) * windAmt * 0.2;

      // --- Perspective mountain ranges (valley view before ocean takes over) ---
      if (mtRise > 0.01 && waterAmt < 0.75) {
        vec3 ranges = paintMountains(uv, aspect, mtRise, col, 0.0);
        float landBlend = 1.0 - smoothstep(0.45, 0.75, waterAmt);
        // Don't keep land rock under rising water
        if (uv.y >= waterLine || waterAmt < 0.15) {
          col = mix(col, ranges, landBlend);
        }
      }

      // --- Ocean seascape: foam waves toward multi-ridge white-peak horizon ---
      if (waterAmt > 0.05) {
        float seaBlend = smoothstep(0.05, 0.55, waterAmt);
        vec3 sea = oceanScene(uv, aspect, waterLine, clamp(mtRise * 0.5 + waterAmt, 0.0, 1.0));
        if (uv.y < waterLine) {
          col = mix(col, sea, seaBlend);
        } else {
          col = mix(col, sea, smoothstep(0.5, 0.85, waterAmt));
        }
      }

      float vig = smoothstep(1.4, 0.2, length(uv - 0.5));
      col *= 0.78 + 0.22 * vig;
      gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
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
      powerPreference: "default",
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
    // Cap DPR — high DPR full-screen shaders often cause Chrome checkerboard tiles on Windows
    const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    if (sky) sky.gl.viewport(0, 0, canvas.width, canvas.height);
  }

  function worldName(w) {
    if (w < 0.32) return { id: "sky", label: "слой · небо" };
    if (w < 0.52) return { id: "ridge", label: "небо + горы" };
    if (w < 0.72) return { id: "ridge", label: "слой · горы" };
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

  function remap(v, a, b, c, d) {
    const t = (v - a) / Math.max(b - a, 0.0001);
    return c + Math.min(Math.max(t, 0), 1) * (d - c);
  }

  function updateScroll() {
    const ridgeEl = document.getElementById("ridge");
    const seaEl = document.getElementById("sea");
    const y = window.scrollY + window.innerHeight * 0.4;
    const ridgeTop = ridgeEl ? ridgeEl.offsetTop : window.innerHeight;
    const seaTop = seaEl ? seaEl.offsetTop : ridgeTop * 2;
    const max = document.documentElement.scrollHeight - window.innerHeight;

    // Hold pure aurora longer at the top, then long blended phases
    if (y < ridgeTop) world = remap(y, 0, ridgeTop, 0, 0.38);
    else if (y < seaTop) world = remap(y, ridgeTop, seaTop, 0.38, 0.7);
    else world = remap(y, seaTop, max + window.innerHeight * 0.4, 0.7, 1);

    progress.style.width = `${(max > 0 ? window.scrollY / max : 0) * 100}%`;
    updateWorldUI(worldSmooth > 0.01 ? worldSmooth : world);

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
    window.addEventListener(
      "pointermove",
      (e) => {
        mouse.tx = e.clientX / Math.max(width, 1);
        mouse.ty = e.clientY / Math.max(height, 1);

        if (isTouch || !cursor) return;
        cursor.style.left = `${e.clientX}px`;
        cursor.style.top = `${e.clientY}px`;
        if (cursorRing) {
          cursorRing.dataset.tx = String(e.clientX);
          cursorRing.dataset.ty = String(e.clientY);
        }
        document.body.classList.add("is-cursor-ready");
      },
      { passive: true }
    );

    if (isTouch || !cursor) return;

    if (cursorRing) {
      let rx = window.innerWidth / 2;
      let ry = window.innerHeight / 2;
      const tickRing = () => {
        const tx = parseFloat(cursorRing.dataset.tx || rx);
        const ty = parseFloat(cursorRing.dataset.ty || ry);
        rx += (tx - rx) * 0.16;
        ry += (ty - ry) * 0.16;
        cursorRing.style.left = `${rx}px`;
        cursorRing.style.top = `${ry}px`;
        requestAnimationFrame(tickRing);
      };
      tickRing();
    }

    document.querySelectorAll("a, button, input, .place").forEach((el) => {
      el.addEventListener("pointerenter", () => document.body.classList.add("is-hover"));
      el.addEventListener("pointerleave", () => document.body.classList.remove("is-hover"));
    });
  }

  function setupMagnetic() {
    // Disabled: per-frame transform on DOM nodes promotes compositor layers
    // and can flash solid tiles under text on Windows Chrome.
    return;
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
