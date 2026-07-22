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

    float constellStar(vec2 p, vec2 pos, float r, float phase, float speed) {
      float d = length(p - pos);
      float core = smoothstep(r, 0.0, d);
      float glow = smoothstep(r * 3.2, 0.0, d) * 0.22;
      float tw = 0.72 + 0.28 * sin(u_time * speed + phase);
      return (core + glow) * tw;
    }

    float constellLine(vec2 p, vec2 a, vec2 b) {
      vec2 pa = p - a;
      vec2 ba = b - a;
      float h = clamp(dot(pa, ba) / max(dot(ba, ba), 0.0001), 0.0, 1.0);
      float d = length(pa - ba * h);
      return smoothstep(0.0028, 0.0, d);
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
      float far2Amt = rise * mix(0.85, 0.3, pullBack);

      float xBase = uv.x + mousePar * 0.02;
      float xFar2 = xBase * aspect * 0.7 - 0.1;
      float xFar = xBase * aspect * 0.9 + 0.05;
      float xMid = xBase * aspect * 1.1 + 0.4;
      float xNear = xBase * aspect * 1.3 + 0.95;

      // Shorter crests — leave the upper frame to sky/aurora; ridge owns the lower band
      float hFar2 = (0.03 + ridgeProfile(xFar2, 0.05, 0.7) * 0.14) * far2Amt;
      float hFar = (0.025 + ridgeProfile(xFar, 0.2, 0.55) * 0.13) * farAmt;
      float hMid = (0.018 + ridgeProfile(xMid, 1.4, 0.35) * 0.11) * midAmt;
      float hNear = (0.012 + ridgeProfile(xNear, 2.8, 0.2) * 0.10) * nearAmt;

      float yFar2 = horizon + hFar2;
      float yFar = horizon + hFar;
      float yMid = horizon + hMid;
      float yNear = horizon + hNear;

      if (uv.y < horizon) {
        float depth = clamp((horizon - uv.y) / max(horizon, 0.001), 0.0, 1.0);
        vec3 soil = mix(vec3(0.1, 0.11, 0.13), vec3(0.03, 0.035, 0.045), pow(depth, 0.85));
        col = mix(col, soil, rise);
      }

      // --- Farthest washed ridge (lavender / snow, strong aerial perspective) ---
      if (hFar2 > 0.001 && uv.y < yFar2 && uv.y >= horizon - 0.01) {
        float ht = clamp((uv.y - horizon) / max(hFar2, 0.001), 0.0, 1.0);
        vec3 rock = mix(vec3(0.42, 0.48, 0.58), vec3(0.7, 0.74, 0.82), pow(ht, 1.05));
        rock = mix(rock, skyCol, 0.35 + pullBack * 0.2);
        rock = mix(rock, vec3(0.92, 0.94, 0.97), smoothstep(0.5, 0.9, ht) * 0.7);
        float edge = smoothstep(yFar2 + 0.022, yFar2 - 0.014, uv.y);
        col = mix(col, rock, edge);
        float fog = exp(-abs(uv.y - horizon) * 20.0) * (1.0 - ht) * rise;
        col = mix(col, mix(skyCol, vec3(0.5, 0.55, 0.65), 0.45), fog * 0.6);
      }

      // --- Far ridge ---
      if (hFar > 0.001 && uv.y < yFar && uv.y >= horizon - 0.01) {
        float ht = clamp((uv.y - horizon) / max(hFar, 0.001), 0.0, 1.0);
        vec3 rock = mix(vec3(0.28, 0.34, 0.45), vec3(0.55, 0.6, 0.7), pow(ht, 1.1));
        rock = mix(rock, skyCol, 0.18 + pullBack * 0.2);
        rock = mix(rock, vec3(0.88, 0.9, 0.94), smoothstep(0.58, 0.93, ht) * 0.55 * (1.0 - pullBack * 0.35));
        float edge = smoothstep(yFar + 0.018, yFar - 0.01, uv.y);
        col = mix(col, rock, edge);
        float fog = exp(-abs(uv.y - horizon) * 18.0) * (1.0 - ht) * rise;
        col = mix(col, mix(skyCol, vec3(0.4, 0.48, 0.58), 0.5), fog * 0.5);
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

    // surfaceAmt: 0 = waves fully folded, 1 = full surface (opens with ocean, closes when diving)
    vec3 oceanWater(vec2 uv, float aspect, float waterLine, float surfaceAmt) {
      float depth = clamp((waterLine - uv.y) / max(waterLine, 0.001), 0.0, 1.0);
      float persp = pow(depth, 1.35);
      float surf = clamp(surfaceAmt, 0.0, 1.0);

      vec3 deep = vec3(0.01, 0.07, 0.12);
      vec3 mid = vec3(0.02, 0.2, 0.3);
      vec3 shallow = vec3(0.05, 0.32, 0.4);
      vec3 col = mix(mix(shallow, mid, persp), deep, pow(persp, 1.2));
      col += vec3(0.25, 0.4, 0.5) * exp(-depth * 14.0) * 0.35;

      float waves = 0.0;
      float foam = 0.0;
      // Same 12-row breath as before — amp/foam scale with surfaceAmt (unfold / fold)
      for (int i = 0; i < 12; i++) {
        float fi = float(i);
        float t = (fi + 1.0) / 12.0;
        float rowDepth = pow(t, 1.55);
        float row = waterLine - rowDepth * waterLine * 0.98;
        float dens = mix(28.0, 3.5, rowDepth);
        float amp = mix(0.004, 0.028, rowDepth) * surf;
        float speed = mix(1.4, 0.55, rowDepth);
        float phase = uv.x * aspect * dens + u_time * speed + u_mouse.x * 1.8 + fi * 1.7;
        float y = row + sin(phase) * amp + sin(phase * 2.1 + fi) * amp * 0.35;
        float line = exp(-abs(uv.y - y) * mix(70.0, 18.0, rowDepth)) * surf;
        float crest = smoothstep(0.2, 0.95, sin(phase) * 0.5 + 0.5);
        waves += line * mix(0.25, 0.7, rowDepth);
        foam += line * crest * mix(0.12, 0.85, rowDepth);
      }

      float foamPatch = fbm(vec2(uv.x * aspect * 3.5 - u_time * 0.15, uv.y * 6.0));
      foam += smoothstep(0.55, 0.8, foamPatch) * persp * 0.35 * surf;

      float chop = fbm(vec2(uv.x * aspect * mix(14.0, 4.0, persp) - u_time * 0.25, uv.y * mix(30.0, 8.0, persp)));
      col += vec3(0.12, 0.45, 0.55) * waves;
      col += vec3(0.04, 0.1, 0.12) * chop * persp * 0.35 * mix(0.35, 1.0, surf);
      col = mix(col, vec3(0.88, 0.95, 0.98), clamp(foam, 0.0, 0.85));
      return col;
    }

    // Abyss: its own world — pressure, caustics, kelp, jellies, vents, trench. Not a recycled sky.
    vec3 paintAbyss(vec2 uv, float aspect, float dive) {
      float d = clamp(dive, 0.0, 1.0);
      float y = uv.y;
      float x = uv.x * aspect;

      // Thick murk — colder and blacker the deeper you go
      float pressure = pow(mix(0.25, 1.0, 1.0 - y) * mix(0.55, 1.0, d), 1.15);
      vec3 shallowBlue = vec3(0.02, 0.12, 0.18);
      vec3 trenchInk = vec3(0.0, 0.01, 0.025);
      vec3 col = mix(shallowBlue, trenchInk, pressure);

      // Distant trench floor relief
      float floorH = 0.08 + 0.04 * noise(vec2(x * 1.4, 2.2)) + 0.025 * noise(vec2(x * 3.5, 5.1));
      if (y < floorH) {
        float ft = clamp(y / max(floorH, 0.001), 0.0, 1.0);
        vec3 silt = mix(vec3(0.02, 0.04, 0.05), vec3(0.05, 0.09, 0.1), ft);
        silt += vec3(0.04, 0.1, 0.12) * noise(vec2(x * 8.0, y * 14.0)) * 0.25;
        col = mix(col, silt, smoothstep(floorH + 0.02, floorH - 0.01, y));
      }

      // Moving caustics — warped lattice of light, dies with depth (not aurora ribbons)
      float cax = x * 6.0 + u_time * 0.35 + fbm(vec2(x * 1.2, y * 2.0 + u_time * 0.1)) * 1.8;
      float cay = y * 9.0 - u_time * 0.2;
      float caust = pow(0.5 + 0.5 * sin(cax) * sin(cay * 1.3 + sin(cax * 0.7)), 3.0);
      caust *= exp(-pressure * 3.2) * smoothstep(0.0, 0.55, y) * d;
      col += vec3(0.12, 0.55, 0.62) * caust * 0.55;

      // Soft shafts of filtered surface light (angled volumes, not sky curtains)
      float shaft = 0.0;
      for (int i = 0; i < 4; i++) {
        float fi = float(i);
        float sx = aspect * mix(0.15, 0.85, (fi + 0.5) / 4.0) + sin(u_time * 0.15 + fi) * 0.04;
        float ang = (x - sx) * 2.2 + (1.0 - y) * 0.35;
        shaft += exp(-ang * ang * mix(18.0, 40.0, fi / 3.0)) * exp(-(1.0 - y) * 1.8);
      }
      col += vec3(0.08, 0.28, 0.34) * shaft * 0.4 * (1.0 - pressure * 0.7) * d;

      // Kelp forest — tall swaying ribbons from the floor
      for (int i = 0; i < 7; i++) {
        float fi = float(i);
        float kx = aspect * (0.08 + fi * 0.13) + sin(u_time * 0.4 + fi * 1.7) * 0.03;
        float sway = sin(y * 9.0 - u_time * 1.1 + fi) * 0.018 * y;
        float kd = abs(x - (kx + sway));
        float height = mix(0.35, 0.72, hash(vec2(fi, 9.1)));
        float blade = smoothstep(0.018, 0.0, kd) * smoothstep(0.0, 0.05, y) * smoothstep(height, height - 0.12, y);
        blade *= 0.55 + 0.45 * noise(vec2(fi * 3.0, y * 12.0 - u_time));
        col = mix(col, vec3(0.02, 0.12, 0.08), blade * 0.85 * d);
        // thinner secondary frond
        float kd2 = abs(x - (kx + sway * 1.4 + 0.012));
        float frond = smoothstep(0.008, 0.0, kd2) * smoothstep(0.05, 0.1, y) * smoothstep(height * 0.85, height * 0.85 - 0.1, y);
        col = mix(col, vec3(0.03, 0.16, 0.1), frond * 0.55 * d);
      }

      // Jellyfish — translucent bells + trailing tentacles
      for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float jx = aspect * mix(0.25, 0.8, hash(vec2(fi, 1.3))) + sin(u_time * 0.22 + fi * 2.0) * 0.06;
        float jy = mix(0.35, 0.7, hash(vec2(fi, 2.4))) + sin(u_time * 0.35 + fi) * 0.03;
        vec2 jp = vec2(x - jx, (y - jy) * 1.35);
        float bell = smoothstep(0.07, 0.0, length(jp * vec2(1.0, 1.35)));
        float rim = smoothstep(0.07, 0.045, length(jp * vec2(1.0, 1.35))) - smoothstep(0.045, 0.02, length(jp * vec2(1.0, 1.35)));
        col += vec3(0.35, 0.85, 0.9) * bell * 0.18 * d;
        col += vec3(0.7, 0.95, 1.0) * max(rim, 0.0) * 0.35 * d;
        // tentacles
        for (int t = 0; t < 4; t++) {
          float ft = float(t);
          float tx = jx + (ft - 1.5) * 0.012 + sin(y * 25.0 - u_time * 1.4 + ft + fi) * 0.008;
          float ty0 = jy - 0.02;
          float ty1 = jy - mix(0.14, 0.22, hash(vec2(fi, ft)));
          float along = smoothstep(ty0, ty0 - 0.01, y) * smoothstep(ty1 - 0.02, ty1, y);
          float td = abs(x - tx);
          col += vec3(0.45, 0.8, 0.85) * smoothstep(0.004, 0.0, td) * along * 0.22 * d;
        }
      }

      // Hydrothermal vent — warm column against the cold
      float vx = aspect * 0.78 + sin(u_time * 0.05) * 0.02;
      float ventCore = exp(-pow((x - vx) * 14.0, 2.0)) * smoothstep(0.0, 0.12, y) * smoothstep(0.55, 0.15, y);
      float boil = fbm(vec2((x - vx) * 20.0, y * 14.0 - u_time * 0.9));
      col += vec3(1.0, 0.45, 0.15) * ventCore * (0.35 + boil * 0.55) * d * 0.65;
      col += vec3(0.9, 0.7, 0.35) * ventCore * boil * 0.35 * d;
      // ember particles rising from the vent
      for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float py = fract(hash(vec2(fi, 4.4)) + u_time * mix(0.12, 0.22, hash(vec2(fi, 0.7))));
        float px = vx + (hash(vec2(fi, 8.1)) - 0.5) * 0.08 + sin(py * 10.0 + fi) * 0.01;
        float pr = mix(0.003, 0.008, hash(vec2(fi, 3.3)));
        float ember = smoothstep(pr, 0.0, length(vec2(x - px, y - py)));
        col += vec3(1.0, 0.55, 0.2) * ember * 0.8 * d * smoothstep(0.55, 0.1, py);
      }

      // School of fish — elongated bodies, not dots/lines
      float school = 0.0;
      for (int i = 0; i < 8; i++) {
        float fi = float(i);
        float phase = u_time * 0.55 + fi * 0.7;
        float fx = aspect * 0.2 + fract(fi * 0.11 + u_time * 0.03) * aspect * 0.55 + sin(phase) * 0.04;
        float fy = 0.48 + sin(phase * 1.3 + fi) * 0.06 + (hash(vec2(fi, 1.0)) - 0.5) * 0.08;
        vec2 fp = vec2((x - fx) * 3.2, (y - fy) * 7.0);
        float body = exp(-dot(fp, fp));
        // tiny tail flick
        float tail = exp(-pow((x - fx + 0.018) * 8.0, 2.0) - pow((y - fy) * 14.0, 2.0));
        school += body * 0.9 + tail * 0.35;
      }
      col = mix(col, col * 0.35 + vec3(0.04, 0.1, 0.12), clamp(school * 0.55, 0.0, 0.7) * d);

      // Marine snow — soft flakes drifting (not twinkling stars)
      float snow = 0.0;
      for (int i = 0; i < 5; i++) {
        float fi = float(i);
        float sy = fract(hash(vec2(fi, 2.2)) - u_time * mix(0.03, 0.07, hash(vec2(fi, 1.1))));
        float sx = fract(hash(vec2(fi, 6.6)) + sin(u_time * 0.2 + fi) * 0.02) * aspect;
        float sr = mix(0.0025, 0.006, hash(vec2(fi, 9.9)));
        snow += smoothstep(sr, 0.0, length(vec2(x - sx, y - sy))) * 0.35;
      }
      col += vec3(0.55, 0.7, 0.75) * snow * 0.25 * d;

      // Dive lamp around cursor — reveals local murk color
      vec2 p = vec2(x, y);
      vec2 m = vec2(u_mouse.x * aspect, u_mouse.y);
      float lamp = exp(-length((p - m) * vec2(1.3, 1.6)) * 3.8);
      col += vec3(0.25, 0.55, 0.6) * lamp * 0.28 * d;
      col += vec3(0.9, 0.95, 0.85) * pow(lamp, 3.0) * 0.15 * d;

      return col;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float aspect = u_res.x / max(u_res.y, 1.0);
      float w = clamp(u_world, 0.0, 1.0);

      // Descent: pure sky → pure ridge → ocean surface → dive (waves fold) → abyss
      // Each biome keeps a clean frame before the next peeks in
      float landAmt = smoothstep(0.28, 0.46, w);
      float auroraAmt = 1.0 - smoothstep(0.26, 0.52, w);
      float dawnAmt = smoothstep(0.28, 0.50, w);
      float windAmt = smoothstep(0.30, 0.48, w) * (1.0 - smoothstep(0.56, 0.70, w));
      // Ocean opens only after ridge owns the frame
      float waterAmt = smoothstep(0.58, 0.74, w);
      // Dive after surface has fully opened — reverse of the unfold
      float diveAmt = smoothstep(0.76, 0.92, w);
      float abyssAmt = smoothstep(0.82, 1.0, w);
      float surfaceAmt = clamp(waterAmt * (1.0 - diveAmt), 0.0, 1.0);
      // Pull ranges back as soon as the sea starts — avoids a dark slab sitting on the water
      float pullBack = max(smoothstep(0.56, 0.82, w), smoothstep(0.5, 0.78, waterAmt));

      // Horizon off-screen in pure sky; ridge band; then sea lifts the waterline; dive pushes it off the top
      float landGate = smoothstep(0.26, 0.44, w);
      float horizon = mix(-0.06, 0.16, landGate);
      horizon = mix(horizon, 0.52, waterAmt);
      horizon = mix(horizon, 1.18, diveAmt); // surface exits upward while diving
      float horizonHint = landGate;

      // --- Sky ---
      vec3 night = mix(vec3(0.01, 0.025, 0.04), vec3(0.004, 0.01, 0.03), uv.y);
      vec3 dawn = mix(vec3(0.86, 0.62, 0.42), vec3(0.35, 0.48, 0.62), pow(uv.y, 0.85));
      dawn += vec3(1.0, 0.7, 0.35) * exp(-length(vec2((uv.x - 0.72) * aspect, uv.y - 0.4) * vec2(2.2, 3.5)) * 3.5) * 0.5;
      vec3 col = mix(night, dawn, dawnAmt);

      float rise = landAmt; // no early "hint" peaks in the night-sky frame
      float crestApprox = max(horizon, 0.0) + 0.22 * rise * (1.0 - pullBack * 0.65);

      // Dusk only once the ridge is actually arriving — not a fake bottom belt in sky
      float dusk = exp(-abs(uv.y - horizon) * 11.0) * landAmt;
      col = mix(col, mix(vec3(0.1, 0.1, 0.12), vec3(0.35, 0.28, 0.22), dawnAmt), dusk * 0.28);

      // Sky visibility dies before ocean/abyss — prevents star flicker when horizon lifts on dive
      float skyVis = (1.0 - dawnAmt) * (1.0 - waterAmt) * (1.0 - diveAmt);

      // Point stars: unique size, brightness, tint, and twinkle per cell
      vec2 starGrid = uv * vec2(u_res.x / 3.0, u_res.y / 3.0);
      vec2 starCell = floor(starGrid);
      vec2 starLocal = fract(starGrid) - 0.5;
      float starOn = step(0.992, hash(starCell));
      float sizeSeed = hash(starCell + vec2(2.3, 5.8));
      float brightSeed = hash(starCell + vec2(4.6, 1.1));
      float tintSeed = hash(starCell + vec2(8.4, 3.3));
      float starRadius = mix(0.028, 0.07, sizeSeed); // tiny … a bit larger
      float starDot = starOn * smoothstep(starRadius, 0.0, length(starLocal));
      starDot *= skyVis * smoothstep(crestApprox + 0.06, 0.7, uv.y);
      float twSeed = hash(starCell + vec2(3.1, 7.7));
      float twPhase = hash(starCell + vec2(9.2, 1.4)) * 6.2831853;
      float twSpeed = 0.25 + twSeed * 1.1;
      float twinkle = 0.55 + 0.45 * sin(u_time * twSpeed + twPhase);
      twinkle *= 0.75 + 0.25 * sin(u_time * (twSpeed * 0.41 + 0.12) + twPhase * 1.7);
      // Cool white → soft ice → faint warm tip
      vec3 starCol = mix(vec3(0.82, 0.9, 1.0), vec3(1.0, 0.96, 0.88), smoothstep(0.35, 0.9, tintSeed));
      starCol = mix(starCol, vec3(0.75, 0.95, 1.0), step(0.82, tintSeed) * 0.55);
      float starBright = mix(0.35, 1.15, brightSeed);
      col += starCol * starDot * twinkle * starBright;

      // Constellations: Big Dipper (Ursa Major) + Scorpius — sky biome only
      float skyStars = skyVis * smoothstep(crestApprox + 0.1, 0.75, uv.y);
      if (skyStars > 0.01) {
        vec2 p = vec2(uv.x * aspect, uv.y);

        // --- Большая Медведица (ковш): handle → bowl ---
        vec2 um0 = vec2(0.18, 0.82);
        vec2 um1 = vec2(0.28, 0.85);
        vec2 um2 = vec2(0.38, 0.84);
        vec2 um3 = vec2(0.46, 0.80); // Megrez
        vec2 um4 = vec2(0.45, 0.72); // Phecda
        vec2 um5 = vec2(0.56, 0.70); // Merak
        vec2 um6 = vec2(0.58, 0.78); // Dubhe
        float um =
          constellStar(p, um0, 0.0045, 0.4, 1.1) +
          constellStar(p, um1, 0.0050, 0.9, 1.3) +
          constellStar(p, um2, 0.0055, 1.5, 1.0) +
          constellStar(p, um3, 0.0040, 2.2, 1.4) +
          constellStar(p, um4, 0.0050, 2.8, 1.2) +
          constellStar(p, um5, 0.0052, 3.4, 0.9) +
          constellStar(p, um6, 0.0060, 4.0, 1.5);
        float umLines =
          constellLine(p, um0, um1) + constellLine(p, um1, um2) +
          constellLine(p, um2, um3) + constellLine(p, um3, um4) +
          constellLine(p, um4, um5) + constellLine(p, um5, um6) +
          constellLine(p, um6, um3);
        col += vec3(0.85, 0.92, 1.0) * um * 1.35 * skyStars;
        col += vec3(0.55, 0.7, 0.9) * umLines * 0.22 * skyStars;

        // --- Скорпион: curve + Antares (warmer/brighter) ---
        vec2 sc0 = vec2(aspect * 0.72, 0.78);
        vec2 sc1 = vec2(aspect * 0.78, 0.74);
        vec2 sc2 = vec2(aspect * 0.84, 0.70); // Antares
        vec2 sc3 = vec2(aspect * 0.88, 0.64);
        vec2 sc4 = vec2(aspect * 0.90, 0.56);
        vec2 sc5 = vec2(aspect * 0.86, 0.50);
        vec2 sc6 = vec2(aspect * 0.80, 0.48);
        vec2 sc7 = vec2(aspect * 0.76, 0.52); // stinger tip curl
        float sc =
          constellStar(p, sc0, 0.0042, 0.6, 1.0) +
          constellStar(p, sc1, 0.0048, 1.2, 1.2) +
          constellStar(p, sc2, 0.0075, 1.8, 0.7) + // Antares
          constellStar(p, sc3, 0.0045, 2.4, 1.1) +
          constellStar(p, sc4, 0.0040, 3.0, 1.3) +
          constellStar(p, sc5, 0.0038, 3.6, 0.95) +
          constellStar(p, sc6, 0.0036, 4.2, 1.15) +
          constellStar(p, sc7, 0.0034, 4.8, 1.05);
        float scLines =
          constellLine(p, sc0, sc1) + constellLine(p, sc1, sc2) +
          constellLine(p, sc2, sc3) + constellLine(p, sc3, sc4) +
          constellLine(p, sc4, sc5) + constellLine(p, sc5, sc6) +
          constellLine(p, sc6, sc7);
        col += vec3(1.0, 0.88, 0.82) * constellStar(p, sc2, 0.0075, 1.8, 0.7) * 0.55 * skyStars;
        col += vec3(0.9, 0.93, 1.0) * sc * 1.15 * skyStars;
        col += vec3(0.6, 0.55, 0.7) * scLines * 0.18 * skyStars;
      }

      // Aurora reaches down to just above the ridge — gap ~half of the old black strip
      float auroraShift = -landAmt * 0.04 - pullBack * 0.03;
      float auroraMask = smoothstep(crestApprox + 0.03, crestApprox + 0.12, uv.y) * auroraAmt * (1.0 - waterAmt) * (1.0 - diveAmt);
      if (auroraMask > 0.001) {
        col += sampleAurora(uv, aspect, auroraShift) * auroraMask;
      }

      // --- Layered ridge under an open sky ---
      if (rise > 0.001) {
        vec3 land = paintMountains(uv, aspect, rise, col, horizon, pullBack, dawnAmt);
        col = mix(col, land, smoothstep(0.0, 0.2, rise));
      }

      // Wind only above the crest
      float wind = fbm(vec2(uv.x * 2.2 - u_time * 0.45 + u_mouse.x * 0.8, uv.y * 22.0));
      float windZone = smoothstep(crestApprox, crestApprox + 0.1, uv.y);
      col += vec3(1.0, 0.98, 0.94) * smoothstep(0.62, 0.85, wind) * windZone * windAmt * 0.16;

      // --- Sea surface (waves unfold with waterAmt, fold again with diveAmt) ---
      if (waterAmt > 0.01) {
        float waterLine = max(mix(0.16, 0.52, waterAmt) * (1.0 - diveAmt * 0.15) + diveAmt * 1.18, 0.05);
        // While diving, still paint water under the rising line until abyss takes over
        if (uv.y < waterLine + 0.04 || diveAmt > 0.2) {
          vec3 water = oceanWater(uv, aspect, waterLine, surfaceAmt);
          float cover = smoothstep(0.01, 0.45, waterAmt);
          float shore = diveAmt > 0.35 ? 1.0 : smoothstep(waterLine + 0.03, waterLine - 0.12, uv.y);
          col = mix(col, water, cover * shore * (1.0 - abyssAmt * 0.85));
          float mist = exp(-abs(uv.y - waterLine) * 12.0) * surfaceAmt;
          col = mix(col, vec3(0.45, 0.58, 0.64), mist * 0.45);
        }
      }

      // --- Abyss: full-frame underwater after the surface folds away ---
      if (diveAmt > 0.01) {
        vec3 deep = paintAbyss(uv, aspect, max(abyssAmt, diveAmt));
        float plunge = smoothstep(0.02, 0.55, diveAmt);
        col = mix(col, deep, plunge);
      }

      // Cursor presence: glow in dark biomes, soft shadow in light ones
      vec2 cPos = vec2(uv.x * aspect, uv.y);
      vec2 cMouse = vec2(u_mouse.x * aspect, u_mouse.y);
      float cDist = length((cPos - cMouse) * vec2(1.35, 1.55));
      float cCore = exp(-cDist * 4.2);
      float cSoft = exp(-cDist * 2.15);
      // Light: dawn ridge + bright ocean surface (not abyss)
      float lightBiome = clamp(max(dawnAmt * landAmt, surfaceAmt * 0.95) * (1.0 - diveAmt), 0.0, 1.0);
      // Dark: night sky leftover + deep dive (abyss already has a lamp; keep a light kiss on sky)
      float darkBiome = clamp(max(auroraAmt * (1.0 - dawnAmt), diveAmt * 0.35), 0.0, 1.0);
      // Shadow pool behind the cursor on bright frames
      col *= 1.0 - cSoft * lightBiome * 0.28;
      col = mix(col, col * vec3(0.42, 0.4, 0.38), cCore * lightBiome * 0.55);
      // Extra glow kiss on dark sky (aurora sample already glows; this grounds the cursor)
      col += vec3(0.35, 0.8, 0.95) * cSoft * darkBiome * (1.0 - diveAmt) * 0.12;

      float vig = smoothstep(1.4, 0.2, length(uv - 0.5));
      // Deeper vignette in the abyss — pressure at the edges
      vig = mix(vig, smoothstep(1.55, 0.15, length(uv - 0.5)), abyssAmt);
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
      premultipliedAlpha: false,
      preserveDrawingBuffer: false,
      powerPreference: "default",
      failIfMajorPerformanceCaveat: false,
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

  // Full visual fidelity on the visible canvas. White square was a star-cell bug, not WebGL.
  // Pro perf model: run at full quality while the tab is visible; hard-stop when hidden
  // (background / minimized tabs must not keep burning the GPU — that was the 7-tab heat).
  const sky = initWebGL(canvas);
  const modeBadge = document.getElementById("render-mode");
  if (modeBadge) modeBadge.textContent = sky ? "WebGL мир" : "fallback";

  let rafId = 0;
  let ringRafId = 0;
  let pageVisible = document.visibilityState !== "hidden";
  let startRingLoop = () => {};
  let stopRingLoop = () => {};

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    const w = Math.max(1, width | 0);
    const h = Math.max(1, height | 0);
    canvas.width = w;
    canvas.height = h;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    if (sky) {
      sky.gl.viewport(0, 0, w, h);
      sky.gl.clearColor(0.024, 0.063, 0.094, 1.0);
      sky.gl.clear(sky.gl.COLOR_BUFFER_BIT);
    }
  }

  function worldName(w) {
    if (w < 0.28) return { id: "sky", label: "слой · небо" };
    if (w < 0.46) return { id: "ridge", label: "небо + горы" };
    if (w < 0.58) return { id: "ridge", label: "слой · горы" };
    if (w < 0.76) return { id: "sea", label: "слой · океан" };
    if (w < 0.88) return { id: "depth", label: "океан → бездна" };
    return { id: "depth", label: "слой · бездна" };
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
    rafId = requestAnimationFrame(frame);
    if (!pageVisible) return;

    const t = now * 0.001;
    mouse.x += (mouse.tx - mouse.x) * 0.05;
    mouse.y += (mouse.ty - mouse.y) * 0.05;
    worldSmooth += (world - worldSmooth) * 0.06;
    morphSound(worldSmooth);

    if (sky) {
      const { gl, program, aPos, uniforms, buffer } = sky;
      const w = canvas.width;
      const h = canvas.height;
      gl.viewport(0, 0, w, h);
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(uniforms.res, w, h);
      gl.uniform1f(uniforms.time, t);
      gl.uniform2f(uniforms.mouse, mouse.x, 1.0 - mouse.y);
      gl.uniform1f(uniforms.world, worldSmooth);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }
  }

  function startLoop() {
    if (!rafId && pageVisible) rafId = requestAnimationFrame(frame);
  }

  function stopLoop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function setPageVisible(visible) {
    pageVisible = visible;
    if (pageVisible) {
      startLoop();
      startRingLoop();
    } else {
      stopLoop();
      stopRingLoop();
    }
  }

  document.addEventListener("visibilitychange", () => {
    setPageVisible(document.visibilityState !== "hidden");
  });
  // Extra coverage for minimized / bfcache cases some Chromium builds mishandle
  window.addEventListener("pagehide", () => setPageVisible(false));
  window.addEventListener("pageshow", () => setPageVisible(document.visibilityState !== "hidden"));
  window.addEventListener("freeze", () => setPageVisible(false));
  window.addEventListener("resume", () => setPageVisible(document.visibilityState !== "hidden"));

  function remap(v, a, b, c, d) {
    const t = (v - a) / Math.max(b - a, 0.0001);
    return c + Math.min(Math.max(t, 0), 1) * (d - c);
  }

  function updateScroll() {
    const ridgeEl = document.getElementById("ridge");
    const seaEl = document.getElementById("sea");
    const depthEl = document.getElementById("depth");
    const y = window.scrollY + window.innerHeight * 0.4;
    const ridgeTop = ridgeEl ? ridgeEl.offsetTop : window.innerHeight;
    const seaTop = seaEl ? seaEl.offsetTop : ridgeTop * 2;
    const depthTop = depthEl ? depthEl.offsetTop : seaTop + window.innerHeight;
    const max = document.documentElement.scrollHeight - window.innerHeight;

    // Hold each biome's own frame before the next arrives
    const skyHold = window.innerHeight * 0.72;
    const ridgeHold = ridgeTop + window.innerHeight * 0.45;
    const seaHold = seaTop + window.innerHeight * 0.55;
    if (y < skyHold) world = 0;
    else if (y < ridgeTop) world = remap(y, skyHold, ridgeTop, 0, 0.34);
    else if (y < ridgeHold) world = remap(y, ridgeTop, ridgeHold, 0.34, 0.56); // pure ridge
    else if (y < seaTop) world = remap(y, ridgeHold, seaTop, 0.56, 0.62); // approach shore
    else if (y < seaHold) world = remap(y, seaTop, seaHold, 0.62, 0.76); // ocean surface
    else if (y < depthTop) world = remap(y, seaHold, depthTop, 0.76, 0.86); // start dive
    else world = remap(y, depthTop, max + window.innerHeight * 0.4, 0.86, 1);

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
        ringRafId = requestAnimationFrame(tickRing);
        if (!pageVisible) return;
        const tx = parseFloat(cursorRing.dataset.tx || rx);
        const ty = parseFloat(cursorRing.dataset.ty || ry);
        rx += (tx - rx) * 0.16;
        ry += (ty - ry) * 0.16;
        cursorRing.style.left = `${rx}px`;
        cursorRing.style.top = `${ry}px`;
      };
      startRingLoop = () => {
        if (!ringRafId && pageVisible) ringRafId = requestAnimationFrame(tickRing);
      };
      stopRingLoop = () => {
        if (ringRafId) cancelAnimationFrame(ringRafId);
        ringRafId = 0;
      };
      startRingLoop();
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

  let audioVoice = null;

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
      return { osc, gain, filter };
    });

    const lfo = audioCtx.createOscillator();
    const lfoGain = audioCtx.createGain();
    lfo.frequency.value = 0.05;
    lfoGain.gain.value = 40;
    lfo.connect(lfoGain);
    oscillators.forEach(({ filter }) => lfoGain.connect(filter.frequency));
    lfo.start();

    audioVoice = { oscillators, lfo, lfoGain };
  }

  function morphSound(w) {
    if (!audioCtx || !audioVoice || !soundOn) return;
    const now = audioCtx.currentTime;
    const sky = w < 0.3 ? 1 : w < 0.45 ? 1 - (w - 0.3) / 0.15 : 0;
    const ridge = w < 0.3 ? 0 : w < 0.45 ? (w - 0.3) / 0.15 : w < 0.58 ? 1 : w < 0.7 ? 1 - (w - 0.58) / 0.12 : 0;
    const sea = w < 0.58 ? 0 : w < 0.7 ? (w - 0.58) / 0.12 : w < 0.78 ? 1 : w < 0.9 ? 1 - (w - 0.78) / 0.12 : 0;
    const depth = w < 0.78 ? 0 : w < 0.9 ? (w - 0.78) / 0.12 : 1;

    const base = [
      98 * sky + 82 * ridge + 55 * sea + 36 * depth,
      146.8 * sky + 123 * ridge + 82 * sea + 49 * depth,
      196 * sky + 164 * ridge + 110 * sea + 73 * depth,
      246.9 * sky + 196 * ridge + 147 * sea + 98 * depth,
    ];
    const cutoff = 1400 * sky + 700 * ridge + 420 * sea + 180 * depth;
    const lfoRate = 0.07 * sky + 0.12 * ridge + 0.04 * sea + 0.025 * depth;
    const lfoDepth = 55 * sky + 90 * ridge + 30 * sea + 12 * depth;

    audioVoice.oscillators.forEach((v, i) => {
      v.osc.frequency.setTargetAtTime(base[i], now, 0.35);
      v.filter.frequency.setTargetAtTime(cutoff, now, 0.4);
      const g = (0.03 - i * 0.004) * (0.85 + 0.35 * depth);
      v.gain.gain.setTargetAtTime(g, now, 0.4);
      v.osc.type = depth > 0.55 ? "sine" : i % 2 === 0 ? "sine" : "triangle";
    });
    audioVoice.lfo.frequency.setTargetAtTime(lfoRate, now, 0.5);
    audioVoice.lfoGain.gain.setTargetAtTime(lfoDepth, now, 0.5);
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
  startLoop();
})();
