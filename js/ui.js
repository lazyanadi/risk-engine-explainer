/* Page detailing: hero pin choreography (copy out, chapter captions in), number counters,
   section indicator, desktop cursor ring. Everything degrades to static content with reduced motion. */
(function () {
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };

/* ---------- number counters: <span data-num="4987" data-dec="0" data-sep>0</span> ---------- */
const fmt = (v, dec, sep) => { const s = v.toFixed(dec); return sep ? Number(s).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) : s; };
const cio = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  cio.unobserve(e.target);
  const el = e.target, to = +el.dataset.num, dec = +el.dataset.dec || 0, sep = el.hasAttribute("data-sep");
  if (reduce) { el.textContent = fmt(to, dec, sep); return; }
  const t0 = performance.now(), dur = 1600;
  const step = t => { const k = Math.min(1, (t - t0) / dur), e2 = 1 - Math.pow(1 - k, 4); el.textContent = fmt(to * e2, dec, sep); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}), { threshold: 0.4 });
$$("[data-num]").forEach(el => cio.observe(el));

/* ---------- hero: the loop stays fixed in place; a calm pre-rendered Blender loop plays over the
   poster (muted, looping, inline). Reduced motion or a failed video keeps the poster. ---------- */
const vis = $("#heroVisual");
if (vis && !reduce) {
  const v = document.createElement("video");
  v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true;
  v.setAttribute("muted", ""); v.setAttribute("playsinline", ""); v.setAttribute("aria-hidden", "true");
  v.preload = "auto"; v.poster = vis.querySelector(".poster").currentSrc || vis.querySelector(".poster").src;
  for (const [type, src] of [["video/webm", vis.dataset.webm], ["video/mp4", vis.dataset.mp4]]) {
    const so = document.createElement("source"); so.type = type; so.src = src; v.appendChild(so);
  }
  v.addEventListener("playing", () => vis.classList.add("playing"), { once: true });
  v.addEventListener("error", () => v.remove(), true);
  vis.appendChild(v);
  const p = v.play(); if (p && p.catch) p.catch(() => {});
  // pause when the hero is off screen (saves battery), resume when back
  new IntersectionObserver(es => { es[0].isIntersecting ? v.play().catch(() => {}) : v.pause(); }).observe(vis);
}

/* ---------- section indicator (replaces the intro's "Scroll To Start" once on the main page) ---------- */
const ind = $("#secInd"), indNum = $("#secIndNum"), indLab = $("#secIndLab");
const secs = $$("main .sec");
let curSec = null;
function indicator() {
  if (!ind) return;
  const page = $(".page").getBoundingClientRect();
  let cur = null;
  for (const s of secs) if (s.getBoundingClientRect().top < innerHeight * 0.5) cur = s;
  // only once a numbered section is on screen (not over the hero), and not over the footer
  const show = !!cur && page.top < 0 && $("#launch").getBoundingClientRect().top > innerHeight * 0.6;
  ind.classList.toggle("on", show);
  if (cur !== curSec) {
    curSec = cur;
    const n = cur ? $(".num", cur).textContent : "00";
    const l = cur ? $(".label", cur).textContent : "Overview";
    indNum.textContent = n; indLab.textContent = l;
    ind.classList.remove("flip"); void ind.offsetWidth; ind.classList.add("flip");
  }
}

let ticking = false;
function onScroll() { if (ticking) return; ticking = true; requestAnimationFrame(() => { ticking = false; indicator(); }); }
addEventListener("scroll", onScroll, { passive: true });
addEventListener("resize", onScroll);
onScroll();

/* ---------- desktop cursor ring (the native cursor stays; the ring only follows it) ---------- */
if (!reduce && matchMedia("(hover: hover) and (pointer: fine)").matches) {
  const ring = document.createElement("div");
  ring.id = "cursor"; ring.setAttribute("aria-hidden", "true");
  document.body.appendChild(ring);
  let x = -100, y = -100, tx = -100, ty = -100, big = false;
  addEventListener("pointermove", e => { tx = e.clientX; ty = e.clientY; const h = e.target.closest("a,button,input,label"); if (!!h !== big) { big = !!h; ring.classList.toggle("big", big); } }, { passive: true });
  document.addEventListener("pointerleave", () => { tx = ty = -100; });
  const loop = () => { x += (tx - x) * 0.2; y += (ty - y) * 0.2; ring.style.transform = `translate(${x}px,${y}px)`; requestAnimationFrame(loop); };
  loop();
}
})();
