/* Shared 3D pieces: a procedural studio environment (the same light layout as blender/v2_render.py:
   grey gradient room, overhead softbox, two strip lights, a rim strip, two black flags), the GLB
   loader with the meshopt decoder, and the material tune-up applied to every model. */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

export const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

export function webglOK() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch (e) { return false; }
}

/* An HDR-like room: everything is unlit geometry with colours above 1.0, so PMREM sees real
   light sources. Original layout, nothing downloaded. */
export function studioScene() {
  const s = new THREE.Scene();
  const room = new THREE.Mesh(new THREE.SphereGeometry(30, 48, 24), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: `varying vec3 vP;
      void main(){
        float y = vP.y * 0.5 + 0.5;                       // 0 floor .. 1 ceiling
        vec3 lo = vec3(0.045, 0.05, 0.06), mid = vec3(0.34, 0.37, 0.42), hi = vec3(0.86, 0.88, 0.92);
        vec3 c = mix(lo, mid, smoothstep(0.30, 0.50, y));
        c = mix(c, hi, smoothstep(0.50, 0.78, y));
        c += vec3(0.06, 0.08, 0.1) * smoothstep(0.55, 0.45, abs(y - 0.5)) * 0.4; // faint cool horizon
        gl_FragColor = vec4(c, 1.0);
      }`,
  }));
  s.add(room);
  const card = (w, h, pos, intensity, tint = [1, 1, 1], black = false) => {
    const m = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, toneMapped: false });
    if (black) m.color.setRGB(0.004, 0.004, 0.005);
    else m.color.setRGB(tint[0] * intensity, tint[1] * intensity, tint[2] * intensity);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
    p.position.set(...pos); p.lookAt(0, 0.3, 0); s.add(p);
    return p;
  };
  // Blender coords (x, y, z-up) -> three (x, z, -y)
  const b = (x, y, z) => [x, z, -y];
  card(7, 4.5, b(-1.2, -1.5, 6.5), 5.5);                        // overhead softbox
  card(0.7, 6, b(-6.5, -2.5, 1.2), 9.0, [1.0, 0.98, 0.95]);       // left strip
  card(0.6, 6, b(6.5, -1.0, 1.5), 7.0, [0.9, 0.95, 1.0]);         // right strip
  card(8, 0.8, b(0.5, 6.5, 2.5), 8.0, [0.92, 0.96, 1.0]);         // rim
  card(6, 2.2, b(0.5, -8, -0.5), 1.6);                            // front fill
  card(3, 6, b(-5, 3.5, 0.5), 0, undefined, true);                // black flags for chrome contrast
  card(3, 6, b(5, -5.5, -1.5), 0, undefined, true);
  return s;
}

const envCache = new WeakMap();
export function studioEnv(renderer) {
  if (envCache.has(renderer)) return envCache.get(renderer);
  const pm = new THREE.PMREMGenerator(renderer);
  const tex = pm.fromScene(studioScene(), 0.02).texture;
  pm.dispose();
  envCache.set(renderer, tex);
  return tex;
}

export function makeRenderer(canvas, { maxDpr = 1.75 } = {}) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  r.setPixelRatio(Math.min(maxDpr, devicePixelRatio || 1));
  r.toneMapping = THREE.AgXToneMapping;
  r.toneMappingExposure = 1.18;
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.setClearColor(0x000000, 0);
  return r;
}

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
export function loadGLB(url) {
  return new Promise((res, rej) => loader.load(url, g => res(g.scene), undefined, rej));
}

/* Material polish after loading. Names come from blender/v2_build.py. */
export function tune(root, { envIntensity = 1.0 } = {}) {
  root.traverse(o => {
    if (!o.isMesh) return;
    o.frustumCulled = !o.isInstancedMesh; // instanced bounds are per-geometry; keep them always drawn
    const m = o.material;
    m.envMapIntensity = envIntensity;
    const n = m.name || "";
    if (/Chrome|Polished|TileBright/.test(n)) { m.envMapIntensity = envIntensity * 1.15; }
    if (/Glass/.test(n)) {
      m.transmission = m.transmission || 1; m.thickness = 0.35; m.roughness = Math.max(0.03, m.roughness);
      m.attenuationColor = new THREE.Color(/Clear/.test(n) ? 0xe8f4ee : 0x0d6a43);
      m.attenuationDistance = /Clear/.test(n) ? 3 : 0.45;
      m.specularIntensity = 1; m.envMapIntensity = envIntensity * 1.3;
    }
    if (/Glow/.test(n)) { m.emissiveIntensity = Math.max(m.emissiveIntensity, 3); m.toneMapped = true; }
    if (/TailOrange/.test(n)) { m.emissiveIntensity = 0.35; }
    if (/Core/.test(n)) { m.userData.baseEmissive = m.emissiveIntensity; }
    if (m.normalMap) m.normalScale.set(0.85, 0.85);
  });
}
