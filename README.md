# RISK/ENGINE, remade

The plain-language Value at Risk explainer from `../risk-engine/site/`, rebuilt as one page that
opens in the dark and ends in the light:

1. **Intro**: a glowing orange "market wave" on charcoal (a live WebGL shader). Scrolling turns it
   into a blurred orange field, then black and white blocks, a checkerboard that gets finer, and a
   diagonal wipe to white. Two lines appear on the way: one word by word, one that decodes from symbols.
2. **Main page**: white, framed, hairline rows, pill buttons, round arrow buttons, grey rounded cards.
   The hero is a silver Möbius "infinity" ribbon made in Blender, shown live with Three.js.
3. **All eight original sections** with their text and interactive charts: the idea, VaR/ES
   explorer (slider + bell-curve toggle), three methods (accordion), backtest (tabs), stress tests,
   custom shock sliders, honesty, inspiration, and the footer with the run command and a risk warning.

Colour has a meaning: **green = safe days / inside the line**, **orange (the intro's wave) = the tail,
the worst days**.

## Run it

```powershell
cd C:\Jarvis\projects\kaib-style-site
python -m http.server 8137 --bind 127.0.0.1    # or: npm run serve
```
Open http://127.0.0.1:8137/ . Everything is local; there are no CDN requests.

If `vendor/` is ever missing: `npm install` then `npm run vendor` (copies three.js and the Inter font
out of `node_modules`).

## How it was built

| Part | File | Notes |
| --- | --- | --- |
| Page | `index.html`, `css/style.css` | Plain HTML/CSS, no framework. Inter variable font (vendored). |
| Intro shader | `js/intro.js` | One fragment shader driven by scroll progress; also draws the calm wave in the footer. |
| 3D hero | `js/hero3d.js` | Three.js 0.187 (vendored), `RoomEnvironment` lighting, slow time/pointer/scroll rotation, only renders while visible. The Blender render `assets/hero-poster.webp` shows first and stays as the fallback if WebGL fails. |
| Charts | `js/explainer.js` | Ported from `risk-engine/site/main.js`. Same seeds and maths; only colours and DOM hooks changed. |
| Blender | `blender/build_hero.py` | Builds the hero and four card props procedurally with `bpy`/`bmesh`. |
| | `blender/render.py` | Lighting, cameras, EEVEE renders, glTF export. |
| | `blender/to_webp.py` | Converts renders to WebP. |
| | `blender/hero.blend` | Saved scene (scenes "Hero" and "Props"). |

Rebuild the 3D assets (background mode, the stable path):
```powershell
$bl = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
& $bl -b --factory-startup --python blender\build_hero.py            # geometry -> blender\hero.blend
$env:RE_MODE="render"; & $bl -b blender\hero.blend --python blender\render.py   # PNG renders
$env:RE_MODE="export"; & $bl -b blender\hero.blend --python blender\render.py   # GLB files
& $bl -b --factory-startup --python blender\to_webp.py               # PNG -> WebP
```
PNG renders are written to `assets/`; only the WebP copies are kept in the repo.

### The hero model
- Centre line: a 3D figure eight. A thin lens-shaped cross-section is swept along it with a half
  twist (Möbius). Because the lens is point-symmetric, the twisted ends join exactly, so the solid is
  closed and watertight.
- 1,095 extruded metal tiles cover part of the loop; they thin out at the edges and a few float off.
- A 4x4x4 cluster of green glass cubes (some missing) sits in the right loop.
- `assets/hero.glb` is 1.2 MB. Props: rings + green sphere, stacked slabs, dice cloud (orange = tail
  shocks), stress bar chart (orange = worst crisis), each as WebP render + GLB.

## Accessibility and behaviour
- `prefers-reduced-motion`: the intro is skipped entirely and the page opens on the main hero; the 3D
  model does not drift; count-ups and bars appear instantly.
- Pinch zoom allowed (no `user-scalable=no`). "Skip the intro" link for keyboard users.
- Animated text copies are `aria-hidden`; screen readers get the plain sentences.
- Accordion uses real buttons with `aria-expanded`; tabs use `aria-pressed`; readouts are live regions.
- Tested at 1440x900 and 390x844 with zero console errors. Screenshots: `docs/shots/`.

See `docs/NOTES.md` for what was borrowed from which reference and the number check.
