# Plan: RISK/ENGINE, remade

Source content: `../risk-engine/site/` (read only). Build here.
v1 (dark wave intro -> bright silver main page) is done; see "v1 history" at the bottom.

## v2: premium models + a more extravagant page

User feedback: "the 3D models look flat and low-fidelity; make it more extravagant and more detailed."

### Change of direction (user, mid-way)
The infinity loop must NOT move: no scroll-driven camera flight, no mouse tilt, no rotation of the hero.
It stays fixed like the reference; the motion is a calm, seamless, pre-rendered Blender loop video
(tiles shimmer, a light sweeps across the chrome, a few cubes lift off and settle), WebM + MP4,
poster frame for first paint, reduced motion / failed video = poster. The hero has no live WebGL.
Dropped with it: the pinned hero sequence, chapter captions, both interludes, the tile-dissolve shader.
Section props stay live but only with a very gentle idle sway (no tilt, no parallax).

### Blender (all background mode: `blender -b ... --python ...`, never the open GUI window)
- [x] `blender/v2_textures.py`: procedural trim sheet (panel lines, engraved circuit traces, brushed micro layer) normal / ORM / emissive
- [x] `blender/v2_build.py`: thick bevelled Möbius loop (rounded-rect section, real thickness), organic tile breakdown
      (flush grid -> stepped tiles -> floating cubes, glowing circuit core underneath), emerald glass cube cluster
      with inner emissive crystals and a metal lattice; props: machined rings + orbiting sphere, plates, crisis bars, coin + dice
- [x] `blender/v2_export.py`: vertex AO bake + GLB export; `npm run optimize` (instancing, meshopt, WebP textures)
- [x] `blender/v2_render.py`: studio rig, Cycles posters 2400 px (`npm run posters`)
- [ ] `RE_MODE=loop` hero loop frames (144 @ 24 fps, camera locked) -> `npm run loop` (WebM + MP4 < 8 MB)

### Site
- [x] procedural PMREM studio environment (`js/studio.js`), lazy section props on one shared canvas (`js/props3d.js`)
- [x] hero: fixed loop video over the poster (`js/ui.js`), stats row under the buttons (no empty gap)
- [x] intro: sparks/bokeh, light streaks, depth-of-field strands, chromatic fringe, word-by-word scramble manifesto, smoother blocks + shrinking-square wipe
- [x] detailing: corner ticks, counters, marquee, section indicator, richer footer with the coin, grain, desktop cursor ring
- [x] fixes: corner labels readable over the checker (chips), "Scroll To Start" retires when the page turns white, hero gap
- [ ] verify (1440x900 + 390x844), >= 4 review rounds, `docs/shots/v2-*`, console, numbers, frame time, reduced motion
- [ ] README, NOTES, log

---

## v1 history

1. **Intro (Infinite Field spirit, original code):** sticky full-screen WebGL fragment shader on charcoal.
   A glowing orange "market signal" ribbon -> blurred orange field -> black/white blocks -> finer checkerboard -> diagonal wipe to white.
2. **Main page (KAIB spirit):** white page, thin page frame, hairlines, pill buttons, round arrow buttons, grey rounded cards.
   Hero = Blender-made silver Möbius ribbon with a tile region and a green glass cube cluster, live in Three.js.
3. **Meaning of colour:** green = safe days / passes / calm; orange (the intro wave) = tail losses, danger.
4. All risk-engine sections kept.

### Blender notes (v1)
- The GUI session crashed during glTF export: Blender 5.2 depsgraph EXCEPTION_ACCESS_VIOLATION (BKE_base_eval_flags)
  when the exporter ran with a context override to a non-active scene. Background mode is the stable path:
  `blender -b --factory-startup --python blender/build_hero.py`, then `RE_MODE=export blender -b blender/hero.blend --python blender/render.py`.
