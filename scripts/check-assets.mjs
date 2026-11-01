// Fails if any image or video file is referenced more than once by the page (index.html, css, js),
// or if a referenced file is missing. Run: npm run check:assets
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";

const files = ["index.html", ...readdirSync("css").map(f => join("css", f)), ...readdirSync("js").map(f => join("js", f))];
const re = /assets\/[\w./-]+\.(?:webp|png|jpe?g|avif|svg|gif|mp4|webm)/gi;
const seen = new Map();
for (const f of files) {
  const text = readFileSync(f, "utf8");
  for (const m of text.matchAll(re)) {
    const line = text.slice(0, m.index).split("\n").length;
    if (!seen.has(m[0])) seen.set(m[0], []);
    seen.get(m[0]).push(`${f}:${line}`);
  }
}
let bad = 0;
for (const [asset, where] of seen) {
  const dup = where.length > 1, missing = !existsSync(asset);
  if (dup || missing) bad++;
  console.log(`${dup || missing ? "FAIL" : "ok  "} ${asset}  (${where.join(", ")})${missing ? "  MISSING" : ""}`);
}
console.log(`\n${seen.size} assets referenced, ${bad} problem(s).`);
process.exit(bad ? 1 : 0);
