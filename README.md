# RISK/ENGINE, remade (v2)

The plain-language Value at Risk explainer from `../risk-engine/site/`, rebuilt as one page that
opens in the dark and ends in the light:

1. **Intro**: a glowing orange "market wave" on charcoal (a live WebGL shader) with drifting sparks and
   soft bokeh, light streaks running along the wave, strands at different depths (depth-of-field blur)
   and a slight chromatic fringe. A three-line manifesto appears word by word, each word decoding from
   symbols. Scrolling turns the wave into a blurred orange field, then black and white blocks that fade
   in cell by cell, a checkerboard that refines smoothly, and a diagonal wipe in which every dark square
   shrinks away to the white main page.
2. **Main page**: white, framed, hairline rows with corner ticks, pill buttons, round arrow buttons, grey
   rounded cards. The hero is a thick, polished-chrome Möbius loop made in Blender. **It stays fixed in
   place**: a calm pre-rendered loop video plays on it (tiles shimmer, a light sweeps across the chrome,
   a few cubes lift off and settle back). Under the buttons: a row of counters (4,987 trading days, 4
   assets, 3 methods, 99%). Then a marquee strip, and a small section indicator in the left margin.
3. **All eight original sections** with their text and interactive charts (numbers identical to the
   original). Each themed section has a Blender product render (machined rings, glass/metal plates, crisis
   bar sculpture, engraved coin with dice) with a very slow light sheen.
4. **Footer**: the wave returns, the coin render, a section index, the risk warning and a large outline wordmark.

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
| Hero video | `assets/v2/hero-loop.webm`, `.mp4`, `hero-poster.webp` | 6 s seamless loop, 1600x1100, poster = frame 0. |
| Renders | `assets/v2/{rings,plates,bars,coin,hero-beauty}.webp` | Cycles, 2400 px wide, denoised. |
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
$env:RE_MODE="loop";  & $bl -b --factory-startup blender\v2_models.blend --python blender\v2_render.py   # 144 loop frames -> C:\Jarvis\tmp\v2-loop
npm run loop                                                                      # frames -> hero-loop.webm/.mp4 + poster (needs ffmpeg)
```
`npm install` brings the dev tools (`@gltf-transform/cli`, `sharp`). `npm run vendor` copies the font.

### What the models are
- **Hero**: a figure-eight centre line swept with a rounded-rectangle cross-section (real thickness,
  rounded/bevelled edges) and a half twist (Möbius); 84k vertices. A procedural trim sheet adds machined
  edge grooves, panel lines with screw dimples, faintly engraved circuit traces and a brushed micro layer
  (normal + roughness maps). On the left loop an organic, noise-shaped zone breaks into ~2,570 bevelled
  tiles: flush grid -> stepped tiles of varying height -> floating, rotated cubes (some emerald glass),
  with the band sunk underneath into a dark core whose circuit traces glow green. Inside the right loop: a
  5x5x5 cluster of bevelled emerald/clear/dark-green glass cubes with emissive inner crystals and a thin
  metal lattice. Studio lighting: grey gradient world, overhead softbox, strip lights, rim, black flags.
- **Props**: machined rings (lathe profiles with chamfers and grooves, glowing green inlays, tick-marked
  base, green core and an orbiting sphere); stacked brushed-metal and engraved green-glass plates on posts
  with a glowing layer; a bar sculpture whose stacked blocks are sized by the real crisis losses (2022 in
  orange, breaking into cubes) with a green glass blade at a normal bad day (99% VaR); a reeded coin with an
  embossed fat-tailed histogram (orange tail) and engraved wordmark, plus dice with real sunken pips.

## Accessibility and behaviour
- `prefers-reduced-motion`: intro skipped, hero shows the still poster (no video), no counters/sheen/grain motion.
- Video: muted, looping, inline, paused when off screen; if it fails the poster stays.
- Pinch zoom allowed. "Skip the intro" link. Animated text copies are `aria-hidden`; screen readers get plain sentences.
- Tested at 1440x900 and 390x844 with a clean console. Screenshots: `docs/shots/v2-*`.

See `docs/NOTES.md` for what was borrowed from which reference and the number check, `docs/PLAN.md` for the plan.
