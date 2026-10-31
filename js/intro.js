/* Intro: one full-screen fragment shader driven by scroll progress p (0..1).
   p 0.00-0.20  glowing orange ribbon ("the market's daily wave") drifting on charcoal
   p 0.14-0.36  the ribbon blooms into a soft blurred orange field
   p 0.36-0.46  the field is sampled into big black/white blocks that flicker (glitch)
   p 0.44-0.72  blocks settle into a checkerboard that gets finer
   p 0.70-0.94  a diagonal wipe turns every cell white = the main page
   Text: line 1 lights up word by word; line 2 decodes from symbols (scramble).
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
vec3 ribbon(vec2 uv, float bloom){
  // uv: x across the screen (aspect corrected), y centred on 0
  float t = uTime * 0.11;
  vec3 col = vec3(0.0); float dark = 0.0;
  for (int i = 0; i < 7; i++){
    float fi = float(i);
    float y = 0.075 * sin(uv.x * 1.35 + t * 1.2 + fi * 0.55)
            + 0.045 * sin(uv.x * 2.9 - t * 1.6 + fi * 1.7)
            + 0.018 * sin(uv.x * 6.1 + t * 2.4 + fi * 0.9)
            + (fi - 3.0) * 0.016 * (0.7 + 0.6 * sin(uv.x * 0.9 - t + fi));
    y -= 0.03 * uv.x;
    float w = (0.010 + 0.042 * (0.5 + 0.5 * sin(uv.x * 1.1 + fi * 1.3 - t * 0.8))) * mix(1.0, 7.0, bloom);
    float d = (uv.y - y) / w;
    float core = exp(-d * d);
    float edge = smoothstep(-1.6, 0.4, d) * exp(-d * d * 0.35); // brighter upper lip, dark fold below
    vec3 hot = mix(vec3(1.0, 0.24, 0.07), vec3(1.0, 0.72, 0.22), 0.5 + 0.5 * sin(uv.x * 1.7 + fi * 0.8 + t));
    col += hot * (core * 0.30 + edge * 0.10);
    dark += exp(-pow((uv.y - y + w * 1.4) / (w * 1.2), 2.0)) * 0.05;
  }
  float fade = smoothstep(1.25, 0.2, abs(uv.x * 0.6));
  return col * mix(0.75, 1.0, fade) - dark * 0.4;
}
vec3 scene(vec2 frag){
  vec2 uv = (frag - 0.5 * uRes) / uRes.y;
  float bloom = smoothstep(0.12, 0.36, uP);
  vec3 c = CHAR + ribbon(uv * mix(1.0, 0.55, bloom), bloom);
  // blurred orange field
  float f = fbm(uv * 1.6 + vec2(uTime * 0.03, -uTime * 0.02));
  vec3 field = mix(vec3(0.22, 0.13, 0.09), vec3(1.0, 0.55, 0.27), smoothstep(0.25, 0.8, f));
  return mix(c, field, smoothstep(0.18, 0.38, uP));
}
void main(){
  vec2 frag = gl_FragCoord.xy;
  if (uFoot > 0.5){ // footer: the plain ribbon, a bit lower and calmer
    vec2 uv = (frag - vec2(0.5 * uRes.x, 0.36 * uRes.y)) / uRes.y;
    gl_FragColor = vec4(CHAR + ribbon(uv * 1.15, 0.0) * 0.9, 1.0); return;
  }
  float pix = smoothstep(0.36, 0.40, uP);
  if (pix <= 0.0){ gl_FragColor = vec4(scene(frag), 1.0); return; }
  float chk = smoothstep(0.44, 0.72, uP);
  float wipe = smoothstep(0.70, 0.94, uP);
  float n = floor(mix(9.0, 54.0, chk * chk));             // cells across the height
  float cs = uRes.y / n;
  vec2 cell = floor(frag / cs);
  vec2 cc = (cell + 0.5) * cs;
  float r = hash(cell + 3.1);
  float flick = hash(cell + floor(uTime * 9.0));
  vec3 src = scene(cc);
  float lum = dot(src, vec3(0.3, 0.5, 0.2));
  vec3 bw = lum > 0.42 + 0.25 * (flick - 0.5) * (1.0 - chk) ? vec3(1.0) : CHAR;
  vec3 checker = mod(cell.x + cell.y, 2.0) < 1.0 ? vec3(1.0) : CHAR;
  vec3 col = r < chk * 1.25 ? checker : bw;
  col = mix(src, col, pix);
  float diag = 0.5 * (cc.x / uRes.x + 1.0 - cc.y / uRes.y);
  if (diag + r * 0.16 < wipe * 1.2) col = vec3(1.0);
  gl_FragColor = vec4(col, 1.0);
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
  function resize() {
    const dpr = Math.min(maxDpr, devicePixelRatio || 1), r = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(r.width * dpr)); canvas.height = Math.max(1, Math.round(r.height * dpr));
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  return {
    resize,
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

if (intro && !reduce) {
  const canvas = document.getElementById("waveCanvas");
  let wave = null;
  try { wave = createWave(canvas); } catch (e) { wave = null; }
  if (!wave) intro.classList.add("no-gl");

  // word-by-word line
  const wordsEl = intro.querySelector("[data-words]");
  const words = wordsEl.textContent.trim().split(/\s+/);
  wordsEl.innerHTML = words.map(w => `<span class="w">${w}</span>`).join(" ");
  const wordSpans = [...wordsEl.querySelectorAll(".w")];
  const l1 = intro.querySelector(".l1"), l2 = intro.querySelector(".l2");
  // scramble line
  const scrEl = intro.querySelector("[data-scramble]");
  const target = scrEl.textContent;
  const GLYPHS = "01%$#<>/+=-*~";
  const pct = document.getElementById("introPct");

  let p = 0, visible = true, lastScr = "";
  const progress = () => {
    const r = intro.getBoundingClientRect(), span = r.height - innerHeight;
    return clamp(-r.top / span);
  };
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
  function frame(now) {
    const time = now / 1000;
    p = progress();
    if (visible) {
      if (wave) wave.draw(time, p);
      // line 1: words light up between p .06 and .22, then fade by .34
      const k1 = smooth(0.05, 0.22, p);
      wordSpans.forEach((s, i) => s.classList.toggle("on", k1 * words.length > i + 0.2));
      l1.style.opacity = 1 - smooth(0.27, 0.35, p);
      l1.style.transform = `translateY(${-30 * smooth(0.27, 0.35, p)}px)`;
      // line 2: decodes between .42 and .58, gone by .70
      const in2 = smooth(0.38, 0.42, p), out2 = smooth(0.64, 0.70, p);
      l2.style.opacity = in2 * (1 - out2);
      if (in2 > 0 && out2 < 1) scramble(smooth(0.42, 0.58, p), time);
      pct.textContent = String(Math.round(p * 100)).padStart(2, "0");
    }
    requestAnimationFrame(frame);
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
