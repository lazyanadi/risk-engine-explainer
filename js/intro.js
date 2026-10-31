/* Intro: one full-screen fragment shader driven by scroll progress p (0..1).
   p 0.00-0.22  glowing orange ribbon on charcoal: strands at different depths (depth-of-field blur),
                drifting sparks and bokeh, light streaks running along the wave, a slight chromatic fringe
   p 0.14-0.36  the ribbon blooms into a soft blurred orange field
   p 0.34-0.48  cells fade one by one into black/white blocks (glitch)
   p 0.44-0.72  blocks settle into a checkerboard that refines smoothly (cells split at random times)
   p 0.68-0.93  a diagonal wipe: each dark square shrinks to nothing = the white main page
   Text: a three-line manifesto reveals word by word with a letter scramble; then the question decodes.
   Screen readers get the plain sentences (.sr-only); the animated copies are aria-hidden. */

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

const VERT = `attribute vec2 a; void main(){ gl_Position = vec4(a, 0.0, 1.0); }`;
const FRAG = `
precision highp float;
uniform vec2 uRes; uniform float uTime; uniform float uP; uniform float uFoot;
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ v += a * noise(p); p = p * 2.03 + 11.7; a *= 0.5; } return v; }

const vec3 CHAR = vec3(0.133);
float waveY(float x, float t, float fi){
  return 0.075 * sin(x * 1.35 + t * 1.2 + fi * 0.55) + 0.045 * sin(x * 2.9 - t * 1.6 + fi * 1.7)
       + 0.018 * sin(x * 6.1 + t * 2.4 + fi * 0.9) + (fi - 3.0) * 0.016 * (0.7 + 0.6 * sin(x * 0.9 - t + fi)) - 0.03 * x;
}
vec3 ribbon(vec2 uv, float bloom){
  float t = uTime * 0.11;
  vec3 col = vec3(0.0); float dark = 0.0;
  float focus = 3.0 + 1.6 * sin(uTime * 0.23);           // the focal plane drifts through the strands
  for (int i = 0; i < 7; i++){
    float fi = float(i);
    float y = waveY(uv.x, t, fi);
    float dof = 1.0 + 0.55 * abs(fi - focus);              // out-of-focus strands are wider and dimmer
    float w = (0.004 + 0.03 * pow(0.5 + 0.5 * sin(uv.x * 1.1 + fi * 1.3 - t * 0.8), 2.0)) * mix(1.0, 9.0, bloom) * dof;
    float d = (uv.y - y) / w;
    float core = exp(-d * d) / sqrt(dof);
    float edge = smoothstep(-1.6, 0.4, d) * exp(-d * d * 0.35) / dof;
    vec3 hot = mix(vec3(1.0, 0.24, 0.07), vec3(1.0, 0.72, 0.22), 0.5 + 0.5 * sin(uv.x * 1.7 + fi * 0.8 + t));
    col += hot * (core * 0.34 + edge * 0.12);
    dark += exp(-pow((uv.y - y + w * 1.4) / (w * 1.2), 2.0)) * 0.05;
  }
  float fade = smoothstep(1.25, 0.2, abs(uv.x * 0.6));
  return col * mix(0.75, 1.0, fade) - dark * 0.4;
}
// sparks riding the wave: three depth layers (near = big soft bokeh, far = tiny sharp points)
vec3 sparks(vec2 uv){
  vec3 c = vec3(0.0);
  float t = uTime * 0.11;
  for (int l = 0; l < 3; l++){
    float fl = float(l);
    float sc = 7.0 + fl * 9.0;
    vec2 g = vec2(uv.x * sc + uTime * (0.25 + 0.2 * fl), uv.y * sc * 1.4);
    vec2 id = floor(g), f = fract(g) - 0.5;
    float r = hash(id + fl * 17.0);
    if (r > 0.3 + 0.2 * fl) continue;
    vec2 o = vec2(hash(id + 3.1), hash(id + 7.7)) - 0.5;
    float rad = l == 0 ? 0.3 : (l == 1 ? 0.07 : 0.035);
    vec2 pp = o * (1.0 - 2.0 * rad - 0.04);                     // stays inside its cell: no clipped discs
    // sparks gather near the wave: fade those far from it
    float x = (id.x + 0.5 - uTime * (0.25 + 0.2 * fl)) / sc;
    float near = exp(-pow((uv.y - waveY(x, t, 3.0)) / (0.22 + 0.1 * fl), 2.0));
    if (near < 0.05) continue;
    float d = length(f - pp);
    float a = l == 0 ? smoothstep(rad, rad * 0.55, d) * 0.07 : smoothstep(rad, 0.0, d) * (0.8 - 0.25 * fl);
    float tw = 0.6 + 0.4 * sin(uTime * (1.5 + r * 3.0) + r * 40.0);
    c += mix(vec3(1.0, 0.55, 0.2), vec3(1.0, 0.85, 0.6), r) * a * tw * near;
  }
  return c;
}
// light streaks that run along the ribbon
vec3 streaks(vec2 uv){
  vec3 c = vec3(0.0); float t = uTime * 0.11;
  for (int i = 0; i < 4; i++){
    float fi = float(i);
    float xc = fract(uTime * (0.045 + 0.02 * fi) + fi * 0.37) * 4.4 - 2.2;
    float y = waveY(uv.x, t, 1.0 + fi * 1.4);
    float dy = uv.y - y;
    float along = exp(-pow((uv.x - xc) / (0.18 + 0.1 * fi), 2.0));
    c += vec3(1.0, 0.8, 0.55) * along * (exp(-dy * dy / 0.0000045) * 0.9 + exp(-dy * dy / 0.0006) * 0.12);
  }
  return c;
}
vec3 wave(vec2 uv, float bloom){
  float ca = 0.012 * length(uv) * (1.0 - bloom);                  // chromatic fringe toward the edges
  vec2 s = uv * mix(1.0, 0.55, bloom);
  vec3 c;
  c.r = ribbon(s * (1.0 + ca), bloom).r;
  c.g = ribbon(s, bloom).g;
  c.b = ribbon(s * (1.0 - ca), bloom).b;
  float calm = 1.0 - bloom;
  c += (sparks(s) + streaks(s)) * calm;
  return c;
}
vec3 scene(vec2 frag){
  vec2 uv = (frag - 0.5 * uRes) / uRes.y;
  uv.x *= max(1.0, 0.85 * uRes.y / uRes.x); // portrait screens: show more of the wave
  float bloom = smoothstep(0.12, 0.36, uP);
  vec3 c = CHAR + wave(uv, bloom);
  float f = fbm(uv * 1.6 + vec2(uTime * 0.03, -uTime * 0.02));
  vec3 field = mix(vec3(0.22, 0.13, 0.09), vec3(1.0, 0.55, 0.27), smoothstep(0.25, 0.8, f));
  c = mix(c, field, smoothstep(0.18, 0.38, uP));
  c *= 1.0 - 0.35 * dot(uv * 0.7, uv * 0.7);                      // vignette
  return c;
}
float cellRand(vec2 c){ return hash(c * 0.731 + 3.1); }
void main(){
  vec2 frag = gl_FragCoord.xy;
  if (uFoot > 0.5){ // footer: the plain ribbon, a bit lower and calmer, with a few sparks
    vec2 uv = (frag - vec2(0.5 * uRes.x, 0.5 * uRes.y)) / uRes.y;
    vec2 s = uv * vec2(0.8, 0.55);
    gl_FragColor = vec4(CHAR + ribbon(s, 0.0) + sparks(s) * 0.6, 1.0); return;
  }
  float grain = (hash(frag + fract(uTime) * 100.0) - 0.5) * 0.025;
  float pix = smoothstep(0.34, 0.48, uP);
  if (pix <= 0.0){ gl_FragColor = vec4(scene(frag) + grain, 1.0); return; }
  float chk = smoothstep(0.44, 0.72, uP);
  float wipe = smoothstep(0.68, 0.93, uP);
  // two grid levels; each coarse cell splits into the finer grid at its own random moment
  float lv = chk * 4.0, l0 = floor(lv), lf = fract(lv);
  float n0 = floor(9.0 * pow(1.65, l0)), n1 = floor(9.0 * pow(1.65, l0 + 1.0));
  float cs0 = uRes.y / n0, cs1 = uRes.y / n1;
  vec2 c0 = floor(frag / cs0), c1 = floor(frag / cs1);
  bool fine = cellRand(c0 + l0 * 13.0) < lf;
  vec2 cell = fine ? c1 : c0; float cs = fine ? cs1 : cs0;
  vec2 cc = (cell + 0.5) * cs;
  float r = cellRand(cell + (fine ? l0 + 1.0 : l0) * 13.0);
  float flick = hash(cell + floor(uTime * 9.0));
  vec3 src = scene(cc);
  float lum = dot(src, vec3(0.3, 0.5, 0.2));
  vec3 bw = lum > 0.42 + 0.25 * (flick - 0.5) * (1.0 - chk) ? vec3(1.0) : CHAR;
  vec3 checker = mod(cell.x + cell.y, 2.0) < 1.0 ? vec3(1.0) : CHAR;
  float toChecker = smoothstep(r - 0.12, r + 0.12, chk * 1.25);
  vec3 col = mix(bw, checker, toChecker);
  // each cell fades from the live image to its block colour at its own time
  float cellPix = smoothstep(r * 0.7, r * 0.7 + 0.3, pix);
  col = mix(scene(frag), col, cellPix);
  // diagonal wipe: dark squares shrink to their centres
  float diag = 0.5 * (cc.x / uRes.x + 1.0 - cc.y / uRes.y);
  float local = clamp((wipe * 1.35 - diag - r * 0.12) / 0.22, 0.0, 1.0);
  vec2 q = abs(frag - cc) / (0.5 * cs);
  float inside = step(max(q.x, q.y), 1.0 - local);
  col = mix(vec3(1.0), col, inside);
  if (local >= 1.0) col = vec3(1.0);
  gl_FragColor = vec4(col + grain * (1.0 - wipe), 1.0);
}`;

export function createWave(canvas, { foot = false, maxDpr = 1.5 } = {}) {
  const gl = canvas.getContext("webgl", { antialias: false, alpha: false, powerPreference: "high-performance" });
  if (!gl) return null;
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG));
  gl.linkProgram(prog); gl.useProgram(prog);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const U = n => gl.getUniformLocation(prog, n);
  const uRes = U("uRes"), uTime = U("uTime"), uP = U("uP"), uFoot = U("uFoot");
  let scale = 1;
  function resize() {
    const dpr = Math.min(maxDpr, devicePixelRatio || 1) * scale, r = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(r.width * dpr)); canvas.height = Math.max(1, Math.round(r.height * dpr));
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  return {
    resize,
    lower() { if (scale > 0.6) { scale = 0.6; resize(); } }, // used if the GPU is too slow
    draw(time, p) {
      gl.uniform2f(uRes, canvas.width, canvas.height); gl.uniform1f(uTime, time); gl.uniform1f(uP, p); gl.uniform1f(uFoot, foot ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
  };
}

/* ---------------- intro choreography ---------------- */
const intro = document.getElementById("intro");
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const GLYPHS = "01%$#<>/+=-*~";

if (intro && !reduce) {
  const canvas = document.getElementById("waveCanvas");
  let wave = null;
  try { wave = createWave(canvas); } catch (e) { wave = null; }
  if (!wave) intro.classList.add("no-gl");

  // manifesto: every word scrambles in at its own scroll threshold (staggered)
  const man = intro.querySelector("[data-manifesto]");
  const lines = man.textContent.split("|").map(s => s.trim());
  man.innerHTML = lines.map(l => `<span class="ml">${l.split(/\s+/).map(w => `<span class="w" data-w="${w}">${w}</span>`).join(" ")}</span>`).join("");
  const words = [...man.querySelectorAll(".w")].map((el, i, all) => ({ el, word: el.dataset.w, at: 0.03 + 0.17 * i / all.length, since: -1, done: false }));
  const l1 = intro.querySelector(".l1"), l2 = intro.querySelector(".l2");
  const scrEl = intro.querySelector("[data-scramble]");
  const target = scrEl.textContent;
  const pct = document.getElementById("introPct");
  const cue = intro.querySelector(".corner.tr");

  let visible = true, lastScr = "", frames = 0, acc = 0;
  const progress = () => { const r = intro.getBoundingClientRect(); return clamp(-r.top / (r.height - innerHeight)); };
  function scramble(k, time) {
    const n = Math.floor(target.length * k), tick = Math.floor(time * 18);
    let out = "";
    for (let i = 0; i < target.length; i++) {
      const ch = target[i];
      if (i < n || ch === " ") out += ch.replace(/[&<>]/g, "");
      else out += `<span class="x">${GLYPHS[(i * 7 + tick * 3) % GLYPHS.length]}</span>`;
    }
    if (out !== lastScr) { scrEl.innerHTML = out; lastScr = out; }
  }
  function wordFrame(w, p, now) {
    const on = p >= w.at;
    if (!on) { if (w.since >= 0) { w.since = -1; w.done = false; w.el.textContent = w.word; w.el.classList.remove("on"); } return; }
    if (w.since < 0) { w.since = now; w.el.classList.add("on"); }
    if (w.done) return;
    const k = (now - w.since) / 420; // 0.42 s per word to settle
    if (k >= 1) { w.el.textContent = w.word; w.done = true; return; }
    const n = Math.floor(w.word.length * k), tick = Math.floor(now / 55);
    let s = w.word.slice(0, n);
    for (let i = n; i < w.word.length; i++) s += GLYPHS[(i * 5 + tick) % GLYPHS.length];
    w.el.textContent = s;
  }
  function frame(now) {
    requestAnimationFrame(frame);
    const time = now / 1000;
    const p = progress();
    if (!visible) return;
    const t0 = performance.now();
    if (wave) wave.draw(time, p);
    // if the GPU struggles (>22 ms per draw for a while), render the shader at a lower resolution
    if (wave && ++frames < 90) { acc += performance.now() - t0; if (frames === 60 && acc / 60 > 22) wave.lower(); }
    words.forEach(w => wordFrame(w, p, now));
    const o1 = smooth(0.24, 0.31, p);
    l1.style.opacity = 1 - o1;
    l1.style.transform = `translateY(${-30 * o1}px)`;
    l1.style.filter = o1 > 0 ? `blur(${o1 * 8}px)` : "";
    const in2 = smooth(0.38, 0.42, p), out2 = smooth(0.64, 0.70, p);
    l2.style.opacity = in2 * (1 - out2);
    if (in2 > 0 && out2 < 1) scramble(smooth(0.42, 0.58, p), time);
    pct.textContent = String(Math.round(p * 100)).padStart(2, "0");
    // labels: plain on dark, dark chips over the blocks, white chips once the page turns white;
    // the "Scroll To Start" cue retires as the page turns white (a section indicator takes over)
    intro.dataset.phase = p < 0.34 ? "dark" : p < 0.68 ? "blocks" : "light";
    cue.style.opacity = String(1 - smooth(0.66, 0.74, p));
    cue.style.visibility = p > 0.74 ? "hidden" : "";
    intro.style.setProperty("--corner-fade", String(1 - smooth(0.88, 0.97, p)));
  }
  new IntersectionObserver(es => { visible = es[0].isIntersecting; }, { threshold: 0 }).observe(intro);
  addEventListener("resize", () => wave && wave.resize());
  requestAnimationFrame(frame);
}

/* ---------------- footer wave (the intro's ribbon returns, calm) ---------------- */
const footCanvas = document.getElementById("footWave");
if (footCanvas) {
  let fw = null;
  try { fw = createWave(footCanvas, { foot: true, maxDpr: 1 }); } catch (e) { fw = null; }
  if (fw) {
    let on = false;
    const loop = now => { if (!on) return; fw.draw(now / 1000, 0); if (!reduce) requestAnimationFrame(loop); };
    new IntersectionObserver(es => { const was = on; on = es[0].isIntersecting; if (on && !was) requestAnimationFrame(loop); }).observe(footCanvas);
    addEventListener("resize", () => { fw.resize(); if (on) fw.draw(performance.now() / 1000, 0); });
  }
}
