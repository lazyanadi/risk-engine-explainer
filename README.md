# RISK/ENGINE: How Bad Could a Bad Day Get?

**A cinematic, interactive guide to market risk, built as a scroll-driven website with a Blender-made 3D hero.**

Live site: https://lazyanadi.github.io/risk-engine-explainer/

RISK/ENGINE explains Value at Risk (VaR), Expected Shortfall, backtesting and stress tests to people with no
finance background. It answers one question, "how bad could a bad day get?", with a number, and then checks
whether that number can be trusted. Every idea has a slider, chart or button you can play with.

The page is designed as one continuous story that **opens in the dark and ends in the light**:

- It starts on a charcoal screen with a live WebGL "market wave", glowing orange, with drifting sparks,
  soft bokeh and light streaks.
- Scrolling melts the wave into a blurred field, then black-and-white blocks, then a checkerboard that
  refines and wipes away to a bright white page.
- On the white page, a polished silver square-section bar looping into an infinity shape, modelled and rendered
  in Blender. All four faces are paneled in a fine grid, and a champagne-gold wave of panels pops out and settles
  back as it travels round the loop, in a seamless 6-second video, with a hard shadow and a thin grey frame behind.
- Underneath sits the full explainer, in a clean editorial style of hairline rows, pill buttons and grey cards.

Colour carries meaning throughout: **green is a normal day, inside the line; orange is the tail, the worst days.**

Built with plain HTML, CSS and JavaScript (no framework), one GLSL fragment shader for the intro, and Blender
(Python) for every 3D picture and the hero video. The explainer's maths is a faithful port of a tested
Python market-risk engine, and its numbers were checked against the original site (all 13 readouts identical).

> Design note: the layout and the opening sequence were inspired by ideas seen on two public websites
> (a bright corporate finance home page and a dark trading-firm intro). Only ideas were taken. No code, text,
> images, logos or names were copied; all code and 3D assets here are original. See `docs/NOTES.md`.

## What is on the page

1. **Intro**: a glowing orange "market wave" on charcoal (a live WebGL shader) with drifting sparks and
   soft bokeh, light streaks running along the wave, strands at different depths (depth-of-field blur)
   and a slight chromatic fringe. A three-line manifesto appears word by word, each word decoding from
   symbols. Scrolling turns the wave into a blurred orange field, then black and white blocks that fade
   in cell by cell, a checkerboard that refines smoothly, and a diagonal wipe in which every dark square
   shrinks away to the white main page.
2. **Main page**: white, wide (frame up to 1760 px), hairline rows with corner ticks, pill buttons, round arrow
   buttons, grey rounded cards. The hero is a **polished silver square-section bar twisting through an infinity
   shape, made in Blender, paneled on all four faces**. It stays fixed in place; a calm, seamless 6-second video
   plays on it: two wave fronts, half a loop apart, run round the loop, lifting panels out to different heights
   (a few sink in) and warming them to champagne gold before they settle back to silver. Under the buttons: a row
   of counters, then a marquee strip.
3. **All seven sections** with their text and interactive charts (numbers identical to the original).
   Every picture is a different Blender object, used once: stacked plates (Historical), machined rings
   (Parametric), dice cloud (Monte Carlo), traffic light (Report card), crisis bars (Crises), four asset pillars
   (Your turn), coin with dice on dark (footer). `npm run check:assets` fails if any image or video is used twice.
4. **Footer**: a full-width dark band: the wave returns, the coin render, a section index, the risk warning and a
   large solid wordmark.

Colour has a meaning: **green = safe days / inside the line**, **orange (the intro's wave) = the tail,
the worst days**.

## Run it locally

```powershell
git clone https://github.com/lazyanadi/risk-engine-explainer.git
cd risk-engine-explainer
python -m http.server 8137 --bind 127.0.0.1    # or: npm run serve
```
Open http://127.0.0.1:8137/ . Everything is local; there are no CDN requests.

## Files

| Part | File | Notes |
| --- | --- | --- |
| Page | `index.html`, `css/style.css` | Plain HTML/CSS, no framework. Inter variable font (vendored). |
| Intro shader | `js/intro.js` | One fragment shader driven by scroll progress; also draws the calm wave in the footer. |
| Page details | `js/ui.js` | Hero loop video (with poster fallback), counters, section indicator, desktop cursor ring. |
| Charts | `js/explainer.js` | Ported from the original risk-engine explainer. Same seeds and maths. |
| Hero video | `assets/v6/hero-loop.webm`, `.mp4`, `hero-poster.webp` | 6 s seamless loop, 1344x924, poster = frame 0, grey frame drawn under it by the encoder. |
| Renders | `assets/v2/{rings,plates,bars}.webp`, `assets/v3/{dice,traffic,pillars,coin-dark}.webp` | Cycles, 2000-2400 px, denoised. |
| Models | `assets/v2/*.glb` | Meshopt-compressed GLBs of the hero and the four props (for reuse; the page itself shows renders). |

## Blender pipeline (background mode only; the open Blender window is never used)

```powershell
$bl = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
& $bl -b --factory-startup --python blender\v2_textures.py                       # detail maps -> blender\tex\
& $bl -b --factory-startup --python blender\v2_build.py                          # models -> blender\v2_models.blend
& $bl -b --factory-startup blender\v2_models.blend --python blender\v2_export.py   # AO bake + raw GLBs -> blender\out\
npm run optimize                                                                  # GLBs -> assets\v2 (instancing, meshopt, WebP)
$env:RE_MODE="final"; & $bl -b --factory-startup blender\v2_models.blend --python blender\v2_render.py   # 2400 px posters
npm run posters                                                                   # PNG -> WebP
# v3: three more props (every picture on the page is a different object)
& $bl -b --factory-startup blender\v2_models.blend --python blender\v3_props.py    # dice, traffic light, pillars -> blender\v3_props.blend
$env:RE_MODE="final"; $env:RE_ONLY="dice,traffic,pillars,coindark"; & $bl -b --factory-startup blender\v3_props.blend --python blender\v2_render.py
node scripts\posters.mjs blender\renders assets\v3 dice,traffic,pillars,coindark
# v6 hero (current): square bar, panels on all four faces, two travelling champagne wave fronts
& blender\v6_loop.cmd                                                              # 144 frames -> C:\Jarvis\tmp\v6-loop (resumable)
node scripts\encode_loop_v5.mjs <frames-folder> assets/v6                          # -> hero-loop.webm/.mp4 + poster (needs ffmpeg)
# (blender\v4_hero.py = earlier tiled bar, blender\v5_hero.py = single-wave ribbon; both kept for reference)
npm run check:assets                                                              # fails if any image/video is used twice
```
`npm install` brings the dev tools (`@gltf-transform/cli`, `sharp`). `npm run vendor` copies the font.

### What the models are
- **Hero (v6)**: a figure-eight centre line swept with a rounded SQUARE cross-section (0.56 x 0.56 at the nearest
  lobe, tapering to 70% on the far lobe). The sweep is one continuous, solid mesh (about 184,000 vertices), with no
  twist and a clear gap at the crossing so one band passes cleanly over the other. All four faces are paneled:
  hairline grooves on the three mirror faces, deep slots on the inside face. For each frame a wave function lifts
  every panel along its face normal (a few sink in) and writes a per-vertex "Pop" colour attribute, which the shader
  uses to warm raised panels toward champagne gold; two wave fronts run round the loop once per 6-second cycle.
  Materials: polished metal (roughness 0.03) with a warm silver base; the inside face is satin with ambient-occlusion
  darkening in the slots. Lighting: dark gradient studio, hard sun, a big key light and thin rim strips, a dark
  shadow-catcher floor under the loop; transparent film flattened on white by the encoder, which also draws the thin
  grey frame behind the loop.
- **Props**: (v2) machined rings (lathe profiles with chamfers and grooves, glowing green inlays, tick-marked
  base, green core and an orbiting sphere); stacked brushed-metal and engraved green-glass plates on posts
  with a glowing layer; a bar sculpture whose stacked blocks are sized by the real crisis losses (2022 in
  orange, breaking into cubes) with a green glass blade at a normal bad day (99% VaR); a reeded coin with an
  embossed fat-tailed histogram (orange tail) and engraved wordmark, plus dice with real sunken pips. (v3) a dice cloud on a brushed plate with orange far-out dice; a brushed traffic light (green lens lit) with a 250-day ruler; four pillars cut to the 2008-style shock (orange down, green up) with glass rings at the starting height.

## Accessibility and behaviour
- `prefers-reduced-motion`: intro skipped, hero shows the still poster (no video), no counter/sheen/grain motion.
- Video: muted, looping, inline, paused when off screen; if it fails the poster stays.
- Pinch zoom allowed. "Skip the intro" link. Animated text copies are `aria-hidden`; screen readers get plain sentences.
- Tested at 1440x900, 1920x1080 and 390x844 with a clean console. Screenshots: `docs/shots/v3-*` (older: `v2-*`).

See `docs/NOTES.md` for what was borrowed from which reference and the number check, `docs/PLAN.md` for the plan.
