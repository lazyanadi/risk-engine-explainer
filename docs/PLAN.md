# Plan: RISK/ENGINE, remade (dark wave intro -> bright silver main page)

Source content: `../risk-engine/site/` (read only). Build here.

## Idea
1. **Intro (Infinite Field spirit, original code):** sticky full-screen WebGL fragment shader on charcoal.
   A glowing orange "market signal" ribbon -> blooms into a blurred orange field -> black/white blocks
   (glitch) -> checkerboard that gets finer -> diagonal wipe to white. Corner labels pinned, "Scroll To Start".
   Two short lines reveal word by word / letter-scramble (aria-hidden visual copy, real text for screen readers).
2. **Main page (KAIB spirit):** white page, thin page frame, near-black text, grey copy, hairlines,
   pill buttons, round arrow buttons, grey rounded cards. Hero = Blender-made silver Möbius ribbon
   with a tile/pixel region and a green glass cube cluster, live in Three.js (poster PNG fallback).
3. **Meaning of colour:** green = safe days / passes / calm; orange (the intro wave) = tail losses, danger.
4. All risk-engine sections kept: idea, VaR/ES explorer, three methods (accordion), backtest,
   stress tests (hairline table + bars), custom shock sliders, honesty, inspiration, launch footer.

## Files
- `index.html`, `css/style.css`, `js/intro.js` (shader), `js/hero3d.js` (Three.js), `js/explainer.js` (ported charts)
- `vendor/three/` copied from `node_modules/three` by `npm run vendor` (no CDN)
- `blender/build_hero.py` (hero + props, procedural bpy), `blender/render.py` (posters, card renders, GLB export)
- `assets/hero.glb`, `assets/hero-poster.webp`, `assets/prop-*.webp|glb`

## Status
- [x] Blender hero + props, .blend saved, GLB + renders exported (see "Blender notes")
- [x] Page structure + styles
- [x] Intro shader + scroll choreography
- [x] Three.js hero
- [x] Ported charts (numbers checked against original)
- [x] Screenshots 1440x900 + 390x844, 3 fix rounds
- [x] README, NOTES, log

## Blender notes
- Built first in the open Blender GUI via the MCP add-on socket. The GUI session crashed during
  glTF export: Blender 5.2 depsgraph EXCEPTION_ACCESS_VIOLATION (BKE_base_eval_flags) when the
  exporter ran with a context override to a non-active scene. Renders had finished; export had not.
- Retried in background mode (stable path now):
  1. `blender -b --factory-startup --python blender/build_hero.py` -> builds + saves blender/hero.blend
  2. `set RE_MODE=export` then `blender -b blender/hero.blend --python blender/render.py` -> GLBs + save
     (export now links objects into the active scene temporarily: no scene override, no crash)
  3. `blender -b --factory-startup --python blender/to_webp.py` -> PNG renders to WebP
  4. Re-render posters if geometry changes: `set RE_MODE=render` + step 2 command.

## Done / next
- Done: all of the above. Review rounds: r1 (hero 3D black patches from anisotropy, 4-line heading,
  soft ribbon, corner labels on orange, wrapped readout, footer wave behind text), r2 (verified fixes),
  r3 mobile (corner label wrap, small model, portrait wave zoom) + final shots in docs/shots.
- Possible next: smaller hero.glb with Draco/meshopt; a Lenis-style smooth scroll (left out on purpose
  for native scrolling and accessibility).