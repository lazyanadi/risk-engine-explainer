// Encode the v5 hero loop frames (blender/v5_loop.cmd, transparent PNGs) into a seamless video on white,
// with the thin grey rectangle frame drawn on the white background UNDER the loop (the loop passes in front of it).
// Needs ffmpeg on PATH. Run: node scripts/encode_loop_v5.mjs [frames dir] [out dir]
import { execFileSync } from "node:child_process";
import { statSync, mkdirSync } from "node:fs";
import sharp from "sharp";

const dir = process.argv[2] || "C:/Jarvis/tmp/v5-loop";
const out = process.argv[3] || "assets/v5";
mkdirSync(out, { recursive: true });
const fps = 24, W = +(process.env.LOOP_W || 1344), H = +(process.env.LOOP_H || 924);
const k = W / 1920;                       // the frame was measured on the 1920x1320 render
const box = `drawbox=x=${Math.round(193 * k)}:y=${Math.round(133 * k)}:w=${Math.round(1533 * k)}:h=${Math.round(1054 * k)}:color=0xDEDEE0:t=${Math.max(2, Math.round(3 * k))}`;
const input = ["-y", "-framerate", String(fps), "-i", `${dir}/f%04d.png`];
const run = args => execFileSync("ffmpeg", args, { stdio: "inherit" });
const base = ["-f", "lavfi", "-i", `color=white:s=${W}x${H}:r=${fps}`];
const chain = `[0:v]${box}[bg];[1:v]format=rgba[fg];[bg][fg]overlay=shortest=1,format=yuv420p`;
const args = (codec) => [...base, ...input, "-filter_complex", chain, ...codec];
run(args(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", "-an", `${out}/hero-loop.webm`]));
run(args(["-c:v", "libx264", "-preset", "slow", "-crf", "20", "-profile:v", "high", "-movflags", "+faststart", "-an", `${out}/hero-loop.mp4`]));
// poster = frame 0 through the same chain, so first paint and the first video frame are identical
run(args(["-frames:v", "1", `${out}/poster.png`]));
await sharp(`${out}/poster.png`).webp({ quality: 88, effort: 6 }).toFile(`${out}/hero-poster.webp`);
for (const f of ["hero-loop.webm", "hero-loop.mp4", "hero-poster.webp"])
  console.log(f, (statSync(`${out}/${f}`).size / 1048576).toFixed(2), "MB");
