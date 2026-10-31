"use strict";
/* Ported from risk-engine/site/main.js. The maths, seeds and numbers are unchanged;
   only colours (green = safe, orange = tail) and the DOM hooks for the new layout differ. */
(function () {
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const C = { ink: "#1c1f22", grey: "#6b7178", line: "#d3d7dc", safe: "rgba(13,106,67,.55)", safeLine: "rgba(13,106,67,.22)",
  tail: "#ff5a1f", tailD: "#d9480f", amber: "#ffad33", font: '"InterV","Inter","Segoe UI",sans-serif' };

// seeded RNG so every visit shows the same data
function rng(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const gauss = r => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r());

/* ---------- scroll progress + reveal ---------- */
addEventListener("scroll", () => {
  const h = document.documentElement;
  $("#progress").style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100 + "%";
}, { passive: true });

const io = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  e.target.classList.add("in");
  $$("[data-count]", e.target).forEach(countUp);
  if (e.target.id === "bars") $$(".bar", e.target).forEach((b, i) => setTimeout(() => $("i", b).style.width = (b.dataset.v / 25 * 100) + "%", reduce ? 0 : i * 220));
  if (e.target.id === "btCanvas") drawBt();
  io.unobserve(e.target);
}), { threshold: .2 });
$$(".reveal, #bars, #btCanvas, #acc").forEach(el => io.observe(el));

function countUp(el) {
  if (el.dataset.done) return; el.dataset.done = 1;
  const to = +el.dataset.count, dec = +el.dataset.dec || 0, t0 = performance.now();
  const step = t => {
    const k = Math.min(1, (t - t0) / 1400), e = 1 - Math.pow(1 - k, 3);
    el.textContent = (to * e).toFixed(dec);
    if (k < 1) requestAnimationFrame(step);
  };
  reduce ? el.textContent = to.toFixed(dec) : requestAnimationFrame(step);
}

/* ---------- accordion (three methods) ---------- */
$$(".acc-btn").forEach(btn => btn.addEventListener("click", () => {
  const item = btn.closest(".acc-item"), open = !item.classList.contains("open");
  item.classList.toggle("open", open); btn.setAttribute("aria-expanded", open);
}));

/* ---------- canvas helper ---------- */
function setup(cv) {
  const dpr = Math.min(2, devicePixelRatio || 1), r = cv.getBoundingClientRect();
  cv.width = Math.max(1, r.width * dpr); cv.height = Math.max(1, r.height * dpr);
  const c = cv.getContext("2d"); c.scale(dpr, dpr);
  return { c, w: r.width, h: r.height };
}

/* ---------- 01: a fan of simulated price paths (was the old hero) ---------- */
(function paths() {
  const cv = $("#pathsCanvas");
  let c, w, h, paths, t0, running = false;
  const N = 140, STEPS = 220;
  function init() {
    ({ c, w, h } = setup(cv));
    const r = rng(7);
    paths = Array.from({ length: N }, () => {
      const p = [0]; let v = 0;
      for (let i = 1; i < STEPS; i++) {
        const shock = gauss(r) * (r() < .015 ? 4 : 1);
        v += shock * .55 - .015; p.push(v);
      }
      return p;
    });
  }
  function frame(now) {
    const prog = reduce ? 1 : Math.min(1, (now - t0) / 4200), upto = Math.floor(prog * (STEPS - 1)) + 1;
    c.clearRect(0, 0, w, h);
    const sx = w * .98 / STEPS, mid = h * .5, sy = h * .016;
    const finals = paths.map(p => p[STEPS - 1]).sort((a, b) => a - b), cut = finals[Math.floor(N * .05)];
    c.strokeStyle = C.line; c.lineWidth = 1; c.beginPath(); c.moveTo(0, mid); c.lineTo(w, mid); c.stroke();
    paths.forEach(p => {
      const bad = p[STEPS - 1] <= cut;
      c.beginPath();
      for (let i = 0; i < upto; i++) { const x = w * .01 + i * sx, y = mid - p[i] * sy; i ? c.lineTo(x, y) : c.moveTo(x, y); }
      c.strokeStyle = bad ? "rgba(255,90,31,.8)" : "rgba(28,31,34,.13)";
      c.lineWidth = bad ? 1.6 : 1; c.stroke();
    });
    if (prog < 1) requestAnimationFrame(frame); else running = false;
  }
  function start() { if (running) return; running = true; t0 = performance.now(); requestAnimationFrame(frame); }
  init();
  new IntersectionObserver((es, o) => { if (es[0].isIntersecting) { start(); o.disconnect(); } }, { threshold: .3 }).observe(cv);
  addEventListener("resize", () => { init(); if (!running) { t0 = -1e9; frame(performance.now()); } });
})();

/* ---------- 02: histogram with VaR / ES ---------- */
const SIGMA = 0.0085, DF = 5, NS = 5000;
const sample = (() => {
  const r = rng(42), out = [], scale = SIGMA / Math.sqrt(DF / (DF - 2));
  for (let i = 0; i < NS; i++) {
    let chi = 0; for (let k = 0; k < DF; k++) chi += gauss(r) ** 2;
    out.push(gauss(r) / Math.sqrt(chi / DF) * scale);
  }
  return out.sort((a, b) => a - b);
})();
const normQ = p => { // inverse normal CDF via bisection, fine for display
  let lo = -8, hi = 8;
  for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2, cdf = .5 * (1 + erf(m / Math.SQRT2)); cdf < p ? lo = m : hi = m; }
  return (lo + hi) / 2;
};
function erf(x) { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + .3275911 * x);
  return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - .284496736) * t + .254829592) * t * Math.exp(-x * x)); }
const pct = x => (x * 100).toFixed(2) + "%", usd = x => "$" + Math.round(x * 1e6).toLocaleString("en-US");

function drawHist() {
  const cv = $("#histCanvas"), { c, w, h } = setup(cv);
  const conf = +$("#conf").value / 100, tail = 1 - conf;
  $("#confOut").textContent = (conf * 100).toFixed(1) + "%";
  const k = Math.max(1, Math.floor(tail * NS)), VaR = -sample[k - 1];
  const ES = -sample.slice(0, k).reduce((a, b) => a + b, 0) / k, nVaR = -normQ(tail) * SIGMA;
  $("#varOut").textContent = pct(VaR); $("#esOut").textContent = pct(ES); $("#nvarOut").textContent = pct(nVaR);
  $("#varSentence").textContent = `On ${(conf * 100).toFixed(1)}% of days the loss should stay under ${usd(VaR)}. On the other ${(tail * 100).toFixed(1)}%, it averages ${usd(ES)}.`;

  const lo = -.05, hi = .05, B = 90, bw = (hi - lo) / B, bins = new Array(B).fill(0);
  sample.forEach(v => { const i = Math.floor((Math.max(lo, Math.min(hi - 1e-9, v)) - lo) / bw); bins[i]++; });
  const peak = Math.max(...bins), pad = 8, base = h - 26, sx = v => pad + (v - lo) / (hi - lo) * (w - 2 * pad);
  c.clearRect(0, 0, w, h);
  // safe zone wash (right of the VaR line) in light green
  c.fillStyle = "rgba(13,106,67,.06)"; c.fillRect(sx(-VaR), 0, w - pad - sx(-VaR), base);
  bins.forEach((n, i) => {
    const x0 = lo + i * bw, bh = n / peak * (base - 14);
    c.fillStyle = x0 + bw <= -VaR ? C.tail : C.safe;
    c.fillRect(sx(x0) + 1, base - bh, Math.max(1, (w - 2 * pad) / B - 2), bh);
  });
  c.strokeStyle = C.line; c.lineWidth = 1; c.beginPath(); c.moveTo(pad, base + .5); c.lineTo(w - pad, base + .5); c.stroke();
  if ($("#showNormal").checked) { // bell curve with the same spread
    c.beginPath(); c.setLineDash([6, 5]); c.strokeStyle = C.ink; c.lineWidth = 1.5;
    for (let i = 0; i <= 200; i++) {
      const v = lo + i / 200 * (hi - lo), y = Math.exp(-.5 * (v / SIGMA) ** 2) * (peak * .78) / peak * (base - 14);
      i ? c.lineTo(sx(v), base - y) : c.moveTo(sx(v), base - y);
    }
    c.stroke(); c.setLineDash([]);
  }
  c.strokeStyle = C.ink; c.lineWidth = 2; c.beginPath(); c.moveTo(sx(-VaR), 6); c.lineTo(sx(-VaR), base); c.stroke();
  c.fillStyle = C.ink; c.font = `600 12px ${C.font}`; c.fillText("VaR −" + pct(VaR), Math.min(sx(-VaR) + 6, w - 90), 18);
  c.strokeStyle = C.tailD; c.beginPath(); c.moveTo(sx(-ES), 26); c.lineTo(sx(-ES), base); c.stroke();
  c.fillStyle = C.tailD; c.fillText("ES", sx(-ES) - 22, 38);
  c.fillStyle = C.grey; c.font = `11px ${C.font}`;
  [-.04, -.02, 0, .02, .04].forEach(v => c.fillText((v * 100).toFixed(0) + "%", sx(v) - 8, h - 8));
}
$("#conf").addEventListener("input", drawHist);
$("#showNormal").addEventListener("change", drawHist);

/* ---------- 04: backtest strip ---------- */
const BT = { expected: [47, "—", "If the model were perfect we would expect about 47 breaks, spread evenly."],
  hist: [73, "0.001", "73 breaks: too many, and they bunch together in turbulent stretches. A fixed 250-day window is slow to notice when markets turn wild."],
  norm: [94, "0.000", "94 breaks: twice what it should be. The bell curve says extreme days are nearly impossible, and the market keeps proving it wrong."] };
let btMode = "expected", btTimers = [];
function drawBt() {
  btTimers.forEach(clearTimeout); btTimers = [];
  const cv = $("#btCanvas"), { c, w, h } = setup(cv), n = BT[btMode][0], r = rng(btMode.length * 31 + n);
  c.clearRect(0, 0, w, h);
  c.fillStyle = C.line; c.fillRect(0, h / 2 - 1, w, 2);
  const centers = [.05, .21, .68, .78], pts = [];
  for (let i = 0; i < n; i++) {
    let f;
    if (btMode === "expected") f = r();
    else if (r() < .7) f = centers[Math.floor(r() * 4)] + gauss(r) * .02; else f = r();
    pts.push(Math.min(.995, Math.max(.005, f)));
  }
  pts.forEach((f, i) => btTimers.push(setTimeout(() => {
    const x = f * w; c.strokeStyle = btMode === "expected" ? C.safe : C.tail; c.lineWidth = 2;
    c.beginPath(); c.moveTo(x, h / 2 - 22); c.lineTo(x, h / 2 + 22); c.stroke();
  }, reduce ? 0 : i * 12)));
  c.fillStyle = C.grey; c.font = `11px ${C.font}`;
  ["2008", "2012", "2016", "2020", "2025"].forEach((y, i) => c.fillText(y, 6 + i * (w - 40) / 4, h - 8));
}
$$(".tabs button").forEach(b => b.addEventListener("click", () => {
  $$(".tabs button").forEach(x => { x.classList.remove("on"); x.setAttribute("aria-pressed", "false"); });
  b.classList.add("on"); b.setAttribute("aria-pressed", "true");
  btMode = b.dataset.bt; const [n, p, t] = BT[btMode];
  $("#btCount").textContent = n; $("#btP").textContent = p; $("#btText").textContent = t; drawBt();
}));

/* ---------- 06: custom shocks ---------- */
const shocks = [0, 0, 0, 0];
function updateShock() {
  const pnl = shocks.reduce((a, b) => a + b, 0) / 4 / 100;
  const el = $("#impact"); el.textContent = (pnl * 100).toFixed(1) + "%";
  el.style.color = pnl < -.0001 ? C.tailD : pnl > .0001 ? "var(--green)" : "var(--ink)";
  $("#impactUsd").textContent = (pnl < 0 ? "−" : pnl > 0 ? "+" : "") + "$" + Math.abs(Math.round(pnl * 1e6)).toLocaleString("en-US");
  shocks.forEach((s, i) => $("#v" + i).textContent = (s > 0 ? "+" : "") + s + "%");
}
$$("#shockBox input").forEach(inp => inp.addEventListener("input", () => { shocks[+inp.dataset.i] = +inp.value; updateShock(); }));
$$(".presets button").forEach(b => b.addEventListener("click", () => {
  b.dataset.p.split(",").forEach((v, i) => { shocks[i] = +v; $$("#shockBox input")[i].value = v; }); updateShock();
}));

/* ---------- init ---------- */
drawHist(); updateShock();
let rz; addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { drawHist(); if ($("#btCanvas").getContext) drawBt(); }, 120); });
window.__riskEngine = { sample, normQ, SIGMA, NS }; // exposed for the number check in docs/NOTES.md
})();
