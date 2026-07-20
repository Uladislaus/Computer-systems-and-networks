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

    vec3 sampleAurora(vec2 uv, float aspect, float yShift) {
      float a1 = auroraBand(uv, 0.42 + yShift, 0.032, 0.06, 1.2);
      float a2 = auroraBand(uv, 0.52 + yShift, 0.026, 0.10, 3.7);
      float a3 = auroraBand(uv, 0.34 + yShift, 0.036, 0.045, 6.1);
      float a4 = auroraBand(uv, 0.58 + yShift, 0.022, 0.13, 8.9);
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

    // Peak lobe: power > 1 = sharper alpine tip; lower = heavier shoulder
    float peakLobe(float x, float cx, float width, float h, float sharp) {
      float t = abs(x - cx) / max(width, 0.001);
      return h * pow(max(1.0 - t, 0.0), sharp);
    }

    // Layered ridge line inspired by real ranges: varied peaks, organic rumple
    float ridgeProfile(float x, float seed, float alpine) {
      float h = 0.0;
      // Broad shoulders
      h += peakLobe(x, 0.08 + seed * 0.03, 0.22, 0.45, mix(1.6, 2.2, alpine));
      h += peakLobe(x, 0.32 + seed * 0.02, 0.16, 0.7, mix(1.5, 2.6, alpine));
      h += peakLobe(x, 0.52 + seed * 0.04, 0.2, 0.95, mix(1.45, 2.8, alpine));
      h += peakLobe(x, 0.72 + seed * 0.02, 0.14, 0.62, mix(1.55, 2.5, alpine));
      h += peakLobe(x, 0.92 + seed * 0.03, 0.18, 0.78, mix(1.5, 2.4, alpine));
      h += peakLobe(x, 1.12 + seed * 0.01, 0.2, 0.5, mix(1.6, 2.2, alpine));
      // Secondary crags
      h += peakLobe(x, 0.42 + seed, 0.07, 0.28, mix(1.8, 3.2, alpine));
      h += peakLobe(x, 0.63 + seed * 0.5, 0.06, 0.22, mix(1.8, 3.0, alpine));
      h += fbm(vec2(x * 2.4 + seed, seed * 3.0)) * mix(0.1, 0.16, alpine);
      return clamp(h, 0.0, 1.25);
    }

    // Reference look: several haze-separated ridges, sky stays open above.
    // Far = pale / snow, mid = blue-grey, near = dark. Valley fog between layers.
    vec3 paintMountains(vec2 uv, float aspect, float rise, vec3 skyCol, float horizon, float pullBack, float dawn) {
      if (rise < 0.001) return skyCol;
      vec3 col = skyCol;
      float mousePar = u_mouse.x - 0.5;

      float approach = rise * (1.0 - pullBack * 0.88);
      float nearAmt = approach * (1.0 - smoothstep(0.1, 0.55, pullBack));
      float midAmt = approach * (1.0 - smoothstep(0.25, 0.75, pullBack));
      float farAmt = rise * mix(1.0, 0.4, pullBack);

      float xBase = uv.x + mousePar * 0.02;
      float xFar = xBase * aspect * 0.85;
      float xMid = xBase * aspect * 1.05 + 0.35;
      float xNear = xBase * aspect * 1.25 + 0.9;

      // Keep crest in the lower half — leave sky / aurora open (refs: ~30% sky)
      float hFar = (0.05 + ridgeProfile(xFar, 0.15, 0.85) * 0.22) * farAmt;
      float hMid = (0.03 + ridgeProfile(xMid, 1.4, 0.45) * 0.18) * midAmt;
      float hNear = (0.02 + ridgeProfile(xNear, 2.8, 0.25) * 0.16) * nearAmt;

      float yFar = horizon + hFar;
      float yMid = horizon + hMid;
      float yNear = horizon + hNear;

      // Valley / ground under the whole range
      if (uv.y < horizon) {
        float depth = clamp((horizon - uv.y) / max(horizon, 0.001), 0.0, 1.0);
        vec3 soil = mix(vec3(0.1, 0.11, 0.13), vec3(0.03, 0.035, 0.045), pow(depth, 0.85));
        col = mix(col, soil, rise);
      }

      // --- Far pale ridge (highest tips, snow, atmospheric wash) ---
      if (hFar > 0.001 && uv.y < yFar && uv.y >= horizon - 0.01) {
        float ht = clamp((uv.y - horizon) / max(hFar, 0.001), 0.0, 1.0);
        vec3 rock = mix(vec3(0.35, 0.4, 0.5), vec3(0.62, 0.68, 0.78), pow(ht, 1.1));
        rock = mix(rock, skyCol, 0.22 + pullBack * 0.25); // distance haze
        float snow = smoothstep(0.55, 0.92, ht) * (1.0 - pullBack * 0.4);
        rock = mix(rock, vec3(0.9, 0.93, 0.97), snow * 0.75);
        float edge = smoothstep(yFar + 0.02, yFar - 0.012, uv.y);
        col = mix(col, rock, edge);
        // Valley fog hugging this layer's base
        float fog = exp(-abs(uv.y - horizon) * 22.0) * (1.0 - ht) * rise;
        col = mix(col, mix(skyCol, vec3(0.45, 0.52, 0.62), 0.5), fog * 0.55);
      }

      // --- Mid indigo ridge ---
      if (hMid > 0.001 && uv.y < yMid && uv.y >= horizon - 0.01) {
        float ht = clamp((uv.y - horizon) / max(hMid, 0.001), 0.0, 1.0);
        vec3 rock = mix(vec3(0.12, 0.14, 0.2), vec3(0.28, 0.34, 0.45), pow(ht, 1.05));
        rock = mix(rock, skyCol, 0.08);
        float edge = smoothstep(yMid + 0.018, yMid - 0.01, uv.y);
        col = mix(col, rock, edge);
        float fog = exp(-abs(uv.y - horizon) * 18.0) * (1.0 - ht) * midAmt;
        col = mix(col, vec3(0.25, 0.3, 0.4), fog * 0.4);
      }

      // --- Near dark ridge (heavier, lower) ---
      if (hNear > 0.001 && uv.y < yNear && uv.y >= horizon - 0.01) {
        float ht = clamp((uv.y - horizon) / max(hNear, 0.001), 0.0, 1.0);
        vec3 rock = mix(vec3(0.02, 0.025, 0.04), vec3(0.1, 0.12, 0.16), pow(ht, 0.95));
        // Soft rim from aurora / dawn on the crest
        float rim = smoothstep(0.7, 1.0, ht) * (0.15 + dawn * 0.25);
        rock += vec3(0.15, 0.35, 0.4) * rim * (1.0 - pullBack);
        float edge = smoothstep(yNear + 0.016, yNear - 0.008, uv.y);
        col = mix(col, rock, edge);
        float fog = exp(-abs(uv.y - horizon) * 14.0) * (1.0 - ht) * nearAmt;
        col = mix(col, vec3(0.12, 0.16, 0.22), fog * 0.45);
      }

      // Horizon seam mist — grounds the whole stack
      float seam = exp(-abs(uv.y - horizon) * 12.0) * rise;
      col = mix(col, mix(vec3(0.3, 0.36, 0.45), skyCol, 0.35), seam * mix(0.35, 0.55, pullBack));
      return col;
    }

    vec3 oceanWater(vec2 uv, float aspect, float waterLine) {
      float depth = clamp((waterLine - uv.y) / max(waterLine, 0.001), 0.0, 1.0);
      float persp = pow(depth, 1.35);

      vec3 deep = vec3(0.01, 0.07, 0.12);
      vec3 mid = vec3(0.02, 0.2, 0.3);
      vec3 shallow = vec3(0.05, 0.32, 0.4);
      vec3 col = mix(mix(shallow, mid, persp), deep, pow(persp, 1.2));
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
        float line = exp(-abs(uv.y - y) * mix(70.0, 18.0, rowDepth));
        float crest = smoothstep(0.2, 0.95, sin(phase) * 0.5 + 0.5);
        waves += line * mix(0.25, 0.7, rowDepth);
        foam += line * crest * mix(0.12, 0.85, rowDepth);
      }

      float foamPatch = fbm(vec2(uv.x * aspect * 3.5 - u_time * 0.15, uv.y * 6.0));
      foam += smoothstep(0.55, 0.8, foamPatch) * persp * 0.35;

      float chop = fbm(vec2(uv.x * aspect * mix(14.0, 4.0, persp) - u_time * 0.25, uv.y * mix(30.0, 8.0, persp)));
      col += vec3(0.12, 0.45, 0.55) * waves;
      col += vec3(0.04, 0.1, 0.12) * chop * persp * 0.35;
      col = mix(col, vec3(0.88, 0.95, 0.98), clamp(foam, 0.0, 0.85));
      return col;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float aspect = u_res.x / max(u_res.y, 1.0);
      float w = clamp(u_world, 0.0, 1.0);

      // Descent: sky → approach ridge on horizon → peaks grow → sea floods below, peaks sink back
      float landAmt = smoothstep(0.08, 0.36, w);
      float auroraAmt = 1.0 - smoothstep(0.2, 0.52, w);
      float dawnAmt = smoothstep(0.14, 0.48, w);
      float windAmt = smoothstep(0.16, 0.44, w) * (1.0 - smoothstep(0.62, 0.88, w));
      float waterAmt = smoothstep(0.5, 0.96, w);
      // Pull ranges back as soon as the sea starts — avoids a dark slab sitting on the water
      float pullBack = max(smoothstep(0.48, 0.98, w), smoothstep(0.5, 0.78, waterAmt));

      // Horizon lower so ranges sit in the bottom half; sky stays open above
      float horizon = mix(0.22, 0.5, waterAmt);
      float horizonHint = smoothstep(0.04, 0.2, w);

      // --- Sky ---
      vec3 night = mix(vec3(0.01, 0.025, 0.04), vec3(0.004, 0.01, 0.03), uv.y);
      vec3 dawn = mix(vec3(0.86, 0.62, 0.42), vec3(0.35, 0.48, 0.62), pow(uv.y, 0.85));
      dawn += vec3(1.0, 0.7, 0.35) * exp(-length(vec2((uv.x - 0.72) * aspect, uv.y - 0.4) * vec2(2.2, 3.5)) * 3.5) * 0.5;
      vec3 col = mix(night, dawn, dawnAmt);

      // Soft dusk near horizon — sky above stays clear
      float dusk = exp(-abs(uv.y - horizon) * 5.5) * max(horizonHint, landAmt);
      col = mix(col, mix(vec3(0.1, 0.1, 0.12), vec3(0.35, 0.28, 0.22), dawnAmt), dusk * 0.4);

      vec2 cell = floor(uv * vec2(u_res.x / 70.0, u_res.y / 70.0));
      float star = step(0.997, hash(cell)) * (1.0 - dawnAmt) * smoothstep(horizon + 0.2, 0.7, uv.y);
      col += vec3(0.9, 0.95, 1.0) * star * (0.65 + 0.35 * sin(u_time * 3.0 + hash(cell) * 50.0));

      // Aurora stays in the upper sky — only a gentle nod toward the ridge
      float auroraShift = -landAmt * 0.06 - pullBack * 0.04;
      float auroraMask = smoothstep(horizon + 0.18, 0.45, uv.y) * auroraAmt;
      col += sampleAurora(uv, aspect, auroraShift) * auroraMask;

      // --- Layered ridge under an open sky ---
      float rise = max(landAmt, horizonHint * 0.4);
      float crestApprox = horizon + 0.28 * rise * (1.0 - pullBack * 0.65);
      if (rise > 0.001) {
        vec3 land = paintMountains(uv, aspect, rise, col, horizon, pullBack, dawnAmt);
        col = mix(col, land, smoothstep(0.0, 0.2, rise));
      }

      // Wind only above the crest
      float wind = fbm(vec2(uv.x * 2.2 - u_time * 0.45 + u_mouse.x * 0.8, uv.y * 22.0));
      float windZone = smoothstep(crestApprox, crestApprox + 0.1, uv.y);
      col += vec3(1.0, 0.98, 0.94) * smoothstep(0.62, 0.85, wind) * windZone * windAmt * 0.16;

      // --- Sea replaces ground below horizon; peaks stay above and shrink via pullBack ---
      if (waterAmt > 0.01 && uv.y < horizon + 0.03) {
        vec3 water = oceanWater(uv, aspect, max(horizon, 0.05));
        float cover = smoothstep(0.01, 0.48, waterAmt);
        float shore = smoothstep(horizon + 0.03, horizon - 0.1, uv.y);
        col = mix(col, water, cover * shore);
        // Soft sea mist on the seam so the ridge settles behind haze, not a hard cut
        float mist = exp(-abs(uv.y - horizon) * 12.0) * waterAmt;
        col = mix(col, vec3(0.45, 0.58, 0.64), mist * 0.45);
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

    gl.clearColor(0.024, 0.063, 0.094, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

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

    // Hold aurora, then long approach through ridge, then slow sink into sea
    if (y < ridgeTop) world = remap(y, 0, ridgeTop, 0, 0.34);
    else if (y < seaTop) world = remap(y, ridgeTop, seaTop, 0.34, 0.62);
    else world = remap(y, seaTop, max + window.innerHeight * 0.4, 0.62, 1);

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
