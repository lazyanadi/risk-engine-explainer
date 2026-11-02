/* Page detailing: hero pin choreography (copy out, chapter captions in), number counters.
   Everything degrades to static content with reduced motion. */
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

/* ---------- hero: the loop stays fixed in place. The hero is a still Blender render; if #heroVisual carries
   data-webm / data-mp4 a calm pre-rendered loop plays over it (muted, looping, inline). ---------- */
const vis = $("#heroVisual");
if (vis && !reduce && vis.dataset.webm) {
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

})();
