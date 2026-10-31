// Compress the raw Blender exports (blender/out/*.glb) into assets/v2/*.glb.
// GPU instancing for the repeated tiles/cubes, meshopt geometry compression, WebP textures <= 2048 px.
// Run: npm run optimize
import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const src = "blender/out", out = "assets/v2";
mkdirSync(out, { recursive: true });
const cli = join("node_modules", "@gltf-transform", "cli", "bin", "cli.js");
const budget = { hero: 12, rings: 4, plates: 4, bars: 4, coin: 4 }; // MB
for (const f of readdirSync(src).filter(f => f.endsWith(".glb"))) {
  const name = f.replace(".glb", "");
  const to = join(out, f);
  execFileSync(process.execPath, [cli, "optimize", join(src, f), to,
    "--compress", "meshopt", "--texture-compress", "webp", "--texture-size", "2048",
    "--instance", "true", "--instance-min", "2", "--simplify", "false", "--join", "false",
    "--flatten", "false", "--palette", "false", "--prune-attributes", "false"], { stdio: "inherit" });
  const mb = statSync(to).size / 1048576;
  console.log(`${to}: ${mb.toFixed(2)} MB (budget ${budget[name] ?? "?"} MB)${mb > (budget[name] ?? 99) ? "  OVER BUDGET" : ""}`);
}
