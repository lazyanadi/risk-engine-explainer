// Convert the Cycles renders (blender/renders/*.png, 2400 px wide) into WebP posters in assets/v2/.
// Run: npm run posters   (uses sharp, installed with @gltf-transform/cli)
import sharp from "sharp";
import { readdirSync, statSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const src = "blender/renders", out = "assets/v2";
mkdirSync(out, { recursive: true });
const rename = { hero: "hero-poster", herobeauty: "hero-beauty" };
for (const f of readdirSync(src).filter(f => f.endsWith(".png"))) {
  const base = f.replace(".png", "");
  const to = join(out, (rename[base] || base) + ".webp");
  await sharp(join(src, f)).webp({ quality: 84, alphaQuality: 90, effort: 6, smartSubsample: true }).toFile(to);
  console.log(to, Math.round(statSync(to).size / 1024), "KB");
}
