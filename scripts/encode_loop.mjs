// Encode the hero loop frames (RE_MODE=loop render, transparent PNGs) into a seamless video on white.
// Needs ffmpeg on PATH. Run: npm run loop   (frames dir can be overridden: node scripts/encode_loop.mjs <dir>)
import { execFileSync } from "node:child_process";
import { statSync, mkdirSync } from "node:fs";
import sharp from "sharp";

const dir = process.argv[2] || "C:/Jarvis/tmp/v2-loop";
const out = "assets/v2";
mkdirSync(out, { recursive: true });
const fps = 24, W = 1600, H = 1100;
const input = ["-y", "-framerate", String(fps), "-i", `${dir}/f%04d.png`];
// flatten the alpha onto the page white (#ffffff)
const run = args => execFileSync("ffmpeg", args, { stdio: "inherit" });
run([...input.slice(0, 1), "-f", "lavfi", "-i", `color=white:s=${W}x${H}:r=${fps}`, ...input.slice(1),
  "-filter_complex", `[1:v]format=rgba[fg];[0:v][fg]overlay=shortest=1,format=yuv420p`,
  "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", "-an", `${out}/hero-loop.webm`]);
run([...input.slice(0, 1), "-f", "lavfi", "-i", `color=white:s=${W}x${H}:r=${fps}`, ...input.slice(1),
  "-filter_complex", `[1:v]format=rgba[fg];[0:v][fg]overlay=shortest=1,format=yuv420p`,
  "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-profile:v", "high", "-movflags", "+faststart", "-an", `${out}/hero-loop.mp4`]);
// poster = frame 0 (so first paint and the first video frame are identical)
await sharp(`${dir}/f0000.png`).flatten({ background: "#ffffff" }).webp({ quality: 86, effort: 6 }).toFile(`${out}/hero-poster.webp`);
for (const f of ["hero-loop.webm", "hero-loop.mp4", "hero-poster.webp"])
  console.log(f, (statSync(`${out}/${f}`).size / 1048576).toFixed(2), "MB");
