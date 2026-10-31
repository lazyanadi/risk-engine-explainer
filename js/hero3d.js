/* Main-page hero: the Blender-made Moebius ribbon (assets/hero.glb), lit by a procedural
   studio environment, slowly turning with time, pointer and scroll. The Blender render
   (assets/hero-poster.webp) stays visible until the first WebGL frame, and remains the
   fallback if WebGL or the model fails. */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const wrap = document.getElementById("heroVisual");
const canvas = document.getElementById("heroGL");
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

function start() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch (e) { return; } // poster stays
  renderer.setPixelRatio(Math.min(2, devicePixelRatio || 1));
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.035).texture;
  scene.environmentIntensity = 1.0;
  const key = new THREE.DirectionalLight(0xffffff, 1.4); key.position.set(-4, 5, 6); scene.add(key);
  const rim = new THREE.DirectionalLight(0xdbe6ff, 1.2); rim.position.set(5, 2, -4); scene.add(rim);

  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
  camera.position.set(0, 0.25, 13.2);
  camera.lookAt(0, 0, 0);

  const pivot = new THREE.Group(); scene.add(pivot);
  const BASE = new THREE.Euler(0.18, -0.3, 0.12);

  function size() {
    const r = wrap.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height);
    camera.updateProjectionMatrix();
  }
  size();
  new ResizeObserver(size).observe(wrap);

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  addEventListener("pointermove", e => { pointer.tx = e.clientX / innerWidth - 0.5; pointer.ty = e.clientY / innerHeight - 0.5; }, { passive: true });

  let visible = true, live = false, model = null;
  new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible) requestAnimationFrame(loop); }).observe(wrap);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) requestAnimationFrame(loop); });

  function loop(now) {
    if (!model) return;
    const t = now / 1000;
    const r = wrap.getBoundingClientRect();
    const scroll = Math.max(-1, Math.min(1, -r.top / innerHeight)); // 0 when the hero is in place
    pointer.x += (pointer.tx - pointer.x) * 0.05; pointer.y += (pointer.ty - pointer.y) * 0.05;
    const drift = reduce ? 0 : 1;
    pivot.rotation.set(
      BASE.x + drift * (pointer.y * 0.18 + Math.sin(t * 0.21) * 0.05),
      BASE.y + drift * (pointer.x * 0.35 + Math.sin(t * 0.13) * 0.22 + scroll * 0.9),
      BASE.z + drift * Math.sin(t * 0.17) * 0.04);
    renderer.render(scene, camera);
    if (!live) { live = true; wrap.classList.add("is-live"); }
    if (visible && !document.hidden && !reduce) requestAnimationFrame(loop);
  }
  if (reduce) addEventListener("scroll", () => requestAnimationFrame(loop), { passive: true });

  new GLTFLoader().load("assets/hero.glb", gltf => {
    model = gltf.scene;
    // centre and scale to a fixed size so camera framing does not depend on the export
    const box = new THREE.Box3().setFromObject(model), c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
    model.position.sub(c);
    const holder = new THREE.Group(); holder.add(model); holder.scale.setScalar(7.4 / Math.max(s.x, s.y, s.z));
    pivot.add(holder);
    model.traverse(o => {
      if (!o.isMesh) return;
      const m = o.material;
      m.anisotropy = 0; // exported from Blender, but needs tangents three.js does not have here (caused black patches)
      m.side = THREE.FrontSide;
      if (/Silver/.test(m.name)) { m.color.set(0xd9dee6); m.metalness = 1; m.roughness = 0.2; m.envMapIntensity = 1.15; }
      if (/Tile/.test(m.name)) { m.color.set(0xc2c9d3); m.roughness = 0.32; }
      if (/Emerald/.test(m.name)) { m.color.set(0x169b5c); m.roughness = 0.06; m.metalness = 0; m.transmission = 0.6; m.thickness = 0.4; m.ior = 1.55; m.attenuationColor = new THREE.Color(0x0b5c36); m.attenuationDistance = 0.4; }
    });
    requestAnimationFrame(loop);
  }, undefined, () => { /* keep the poster */ });
}

// only spin up WebGL when the hero is near the viewport (after the intro)
const near = new IntersectionObserver(es => { if (es[0].isIntersecting) { near.disconnect(); start(); } }, { rootMargin: "600px 0px" });
near.observe(wrap);
