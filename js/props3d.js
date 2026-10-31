/* Section props (rings, plates, bars, coin) on one shared transparent canvas that sits above the
   content (below the nav). Each `.prop3d[data-model]` placeholder is a window: its model loads when
   it comes near the viewport (lazy), then draws into exactly that rectangle (scissor). The Blender
   render inside the placeholder is the poster and stays as the fallback.
   Motion: only a very gentle idle sway (and the rings' orbiting sphere); none with reduced motion. */
import * as THREE from "three";
import { reduce, webglOK, makeRenderer, studioEnv, loadGLB, tune } from "./studio.js";

const canvas = document.getElementById("fxGL");
const holders = [...document.querySelectorAll(".prop3d[data-model]")];
const nav = document.querySelector(".nav");

// per-model framing (camera distance multiplier, height of the look-at point, base rotation)
const SETUP = {
  rings: { dist: 2.15, look: 0.12, el: 0.62, rot: 0.3 },
  plates: { dist: 2.3, look: 0.0, el: 0.5, rot: -0.5 },
  bars: { dist: 2.15, look: 0.06, el: 0.36, rot: -0.42 },
  coin: { dist: 2.0, look: 0.02, el: 0.3, rot: 0.25 },
};

function start() {
  let renderer;
  try { renderer = makeRenderer(canvas, { maxDpr: 1.75 }); } catch (e) { return; }
  renderer.setScissorTest(true);
  renderer.autoClear = false;
  const env = studioEnv(renderer);

  const items = holders.map(el => ({ el, key: el.dataset.model, state: "idle", scene: null, cam: null, group: null, live: false }));

  function load(it) {
    it.state = "loading";
    loadGLB(`assets/v2/${it.key}.glb`).then(root => {
      tune(root, { envIntensity: it.key === "coin" ? 1.15 : 1 });
      const s = SETUP[it.key];
      const scene = new THREE.Scene(); scene.environment = env;
      const box = new THREE.Box3().setFromObject(root), c = box.getCenter(new THREE.Vector3()), sz = box.getSize(new THREE.Vector3());
      root.position.sub(c);
      const holder = new THREE.Group(); holder.add(root);
      const k = 2 / Math.max(sz.x, sz.y, sz.z); holder.scale.setScalar(k);
      const group = new THREE.Group(); group.add(holder); scene.add(group);
      const cam = new THREE.PerspectiveCamera(32, 1, 0.05, 50);
      it.radius = s.dist * 1.0; it.s = s;
      it.scene = scene; it.cam = cam; it.group = group; it.root = root;
      it.orbit = root.getObjectByName("RE2_Orbiter");
      it.worst = root.getObjectByName("RE2_BarsWorst");
      it.state = "ready";
      renderer.compile(scene, cam);
    }).catch(() => { it.state = "failed"; });
  }

  const io = new IntersectionObserver(es => es.forEach(e => {
    const it = items.find(i => i.el === e.target);
    it.near = e.isIntersecting;
    if (e.isIntersecting && it.state === "idle") load(it);
  }), { rootMargin: "120% 0px" });
  items.forEach(it => io.observe(it.el));

  function size() { renderer.setSize(innerWidth, innerHeight, false); }
  addEventListener("resize", size); size();

  let lastSig = "";
  function frame(now) {
    requestAnimationFrame(frame);
    if (document.hidden) return;
    const t = now / 1000, H = innerHeight, W = innerWidth;
    const navB = nav ? Math.max(0, nav.getBoundingClientRect().bottom) : 0;
    const vis = [];
    for (const it of items) {
      if (it.state !== "ready" || !it.near) continue;
      const r = it.el.getBoundingClientRect();
      if (r.width < 20 || r.height < 20 || r.bottom < navB || r.top > H) continue;
      vis.push([it, r]);
    }
    // with reduced motion only redraw when something on screen moved
    const sig = vis.map(([it, r]) => `${it.key}${Math.round(r.top)}x${Math.round(r.width)}`).join("|") + `${W}x${H}`;
    if (reduce && sig === lastSig) return;
    lastSig = sig;
    renderer.setScissor(0, 0, W, H); renderer.setViewport(0, 0, W, H);
    renderer.clear(true, true, true);
    for (const [it, r] of vis) {
      // clip to the visible part below the nav, draw into the full placeholder rect
      const top = Math.max(r.top, navB), bottom = Math.min(r.bottom, H);
      if (bottom - top < 2) continue;
      renderer.setScissor(r.left, H - bottom, r.width, bottom - top);
      renderer.setViewport(r.left, H - r.bottom, r.width, r.height);
      const cam = it.cam, s = it.s;
      cam.aspect = r.width / r.height;
      cam.fov = cam.aspect < 1 ? 40 : 30;
      // fixed camera; only a very gentle idle sway (none with reduced motion)
      const el = s.el;
      const d = s.dist * (cam.aspect < 1 ? 1.25 / Math.min(1, cam.aspect + 0.35) : 1);
      cam.position.set(Math.sin(s.rot) * Math.cos(el) * d, Math.sin(el) * d + s.look, Math.cos(s.rot) * Math.cos(el) * d);
      cam.lookAt(0, s.look, 0);
      cam.updateProjectionMatrix();
      const idle = reduce ? 0 : t;
      it.group.rotation.set(0, Math.sin(idle * 0.2) * 0.06, 0);
      if (it.orbit && !reduce) it.orbit.position.set(1.22 * Math.cos(idle * 0.5), 0, -1.22 * Math.sin(idle * 0.5)); // green sphere orbits the rings
      renderer.render(it.scene, cam);
      if (!it.live) { it.live = true; it.el.classList.add("is-live"); }
    }
  }
  requestAnimationFrame(frame);
}

if (canvas && holders.length && webglOK()) start();
