// Copy the parts of three.js the page uses from node_modules into vendor/ (no CDN at runtime).
// Run: npm install && npm run vendor
import { cpSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";

const src = "node_modules/three";
const out = "vendor/three";
const files = [
  "build/three.module.js",
  "build/three.core.js",
  "examples/jsm/loaders/GLTFLoader.js",
  "examples/jsm/utils/BufferGeometryUtils.js",
  "examples/jsm/utils/SkeletonUtils.js",
  "examples/jsm/environments/RoomEnvironment.js",
  "LICENSE",
];
for (const f of files) {
  const to = join(out, f.replace("build/", "").replace("examples/jsm/", "addons/"));
  mkdirSync(dirname(to), { recursive: true });
  cpSync(join(src, f), to);
  console.log("copied", to);
}
// Inter variable font (SIL OFL) for the page typography
mkdirSync("vendor/fonts", { recursive: true });
cpSync("node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", "vendor/fonts/inter-latin-wght-normal.woff2");
cpSync("node_modules/@fontsource-variable/inter/LICENSE", "vendor/fonts/LICENSE-inter.txt");
console.log("copied vendor/fonts/inter-latin-wght-normal.woff2");
const v = JSON.parse(readFileSync(join(src, "package.json"), "utf8")).version;
console.log("three", v);
