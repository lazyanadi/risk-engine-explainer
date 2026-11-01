# RISK/ENGINE, remade (v3)

The plain-language Value at Risk explainer from `../risk-engine/site/`, rebuilt as one page that
opens in the dark and ends in the light:

1. **Intro**: a glowing orange "market wave" on charcoal (a live WebGL shader) with drifting sparks and
   soft bokeh, light streaks running along the wave, strands at different depths (depth-of-field blur)
   and a slight chromatic fringe. A three-line manifesto appears word by word, each word decoding from
   symbols. Scrolling turns the wave into a blurred orange field, then black and white blocks that fade
   in cell by cell, a checkerboard that refines smoothly, and a diagonal wipe in which every dark square
   shrinks away to the white main page.
2. **Main page**: white, wide (frame up to 1760 px), hairline rows with corner ticks, pill buttons, round arrow
   buttons, grey rounded cards. The hero is a wide, thin **satin-silver Möbius loop made in Blender whose whole
   surface is a fine grid of tiles**. It stays fixed in place; a calm, seamless pre-rendered video plays on it: a
   scatter wave travels once round the loop every 7 seconds, pushing tiles out to different depths (a few lift off)
   and letting them settle back into a smooth surface. Under the buttons: a row of counters, then a marquee strip.
3. **All eight original sections** with their text and interactive charts (numbers identical to the original).
   Every picture is a different Blender object, used once: stacked plates (Historical), machined rings
   (Parametric), dice cloud (Monte Carlo), traffic light (Report card), crisis bars (Crises), four asset pillars
   (Your turn), coin with dice on dark (footer). `npm run check:assets` fails if any image or video is used twice.
4. **Footer**: a full-width dark band: the wave returns, the coin render, a section index, the risk warning and a
   large solid wordmark.

Colour has a meaning: **green = safe days / inside the line**, **orange (the intro's wave) = the tail,
the worst days**.

## Run it

```powershell
cd C:\Jarvis\projects\kaib-style-site
python -m http.server 8137 --bind 127.0.0.1    # or: npm run serve
```
Open http://127.0.0.1:8137/ . Everything is local; there are no CDN requests.

## Files

| Part | File | Notes |
| --- | --- | --- |
| Page | `index.html`, `css/style.css` | Plain HTML/CSS, no framework. Inter variable font (vendored). |
| Intro shader | `js/intro.js` | One fragment shader driven by scroll progress; also draws the calm wave in the footer. |
| Page details | `js/ui.js` | Hero loop video (with poster fallback), counters, section indicator, desktop cursor ring. |
| Charts | `js/explainer.js` | Ported from `risk-engine/site/main.js`. Same seeds and maths. |
| Hero video | `assets/v3/hero-loop.webm`, `.mp4`, `hero-poster.webp` | 7 s seamless loop, 1920x1320, poster = frame 0. |
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
# v3 hero: whole ribbon tiled, travelling scatter wave
& $bl -b --factory-startup --python blender\v3_hero.py                             # -> blender\v3_hero.blend
$env:RE_MODE="loop"; & $bl -b --factory-startup blender\v3_hero.blend --python blender\v3_hero.py   # 168 frames -> C:\Jarvis\tmp\v3-loop
npm run loop                                                                      # -> assets\v3\hero-loop.webm/.mp4 + poster (needs ffmpeg)
npm run check:assets                                                              # fails if any image/video is used twice
```
`npm install` brings the dev tools (`@gltf-transform/cli`, `sharp`). `npm run vendor` copies the font.

### What the models are
- **Hero (v3)**: a figure-eight centre line swept with a thin rounded-edge cross-section and a half twist
  (Möbius), 1,400 rings along the loop. About 11,100 bevelled tiles cover both faces of the whole ribbon, sitting
  flush with the surface. For each frame a scatter wave (a smooth bump along the loop with a ragged, per-tile front)
  chooses how far each tile extrudes (10 height steps), how much it tilts, and lets about 2.5% of them lift off.
  The wave centre moves exactly once round the loop per cycle, so the last frame leads straight back into the
  first. Material: pale blue-grey satin metal (metallic, roughness 0.23, light anisotropy). Lighting: a white-to-
  blue-grey gradient sky plus soft emissive cards (top, sides, back, a cool blue bounce), transparent film, then
  composited on pure white.
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
