# Plan: RISK/ENGINE, remade

Source content: `../risk-engine/site/` (read only). Build here.
v1 (dark wave intro -> bright silver main page) is done; see "v1 history" at the bottom.

## v2: premium models + a more extravagant page

User feedback: "the 3D models look flat and low-fidelity; make it more extravagant and more detailed."

### Blender (all background mode: `blender -b ... --python ...`, never the open GUI window)
- [ ] `blender/v2_textures.py`: procedural detail maps (numpy, in Blender): ribbon trim sheet
      (panel lines, engraved circuit traces, micro grid) as normal / roughness / emissive-mask, coin engraving
- [ ] `blender/v2_build.py`: hero v2
  - [ ] thick Möbius loop, rounded-rect (bevelled) cross-section, real thickness, UVs, ~200k tris
  - [ ] tile breakdown: bevelled tiles in a grid that spreads organically (noise mask), varying depth,
        gradient solid -> inset grid -> raised tiles -> floating cubes (instanced, one mesh per variant)
  - [ ] emerald glass cube cluster: bevelled glass cubes, inner faces, emissive edge accents, internal lattice
  - [ ] props: machined rings + orbiting green sphere; stacked glass/metal plates; bar-chart sculpture; engraved coin + dice
  - [ ] materials: layered PBR (metal base, clearcoat, roughness variation, edge wear), studio rig, grey gradient backdrop
- [ ] `blender/v2_bake.py`: AO bakes for ribbon + props (Cycles GPU)
- [ ] `blender/v2_export.py`: GLB export (GPU instancing for tiles) -> `npm run optimize` (gltf-transform, meshopt, textures <= 2048)
- [ ] `blender/v2_render.py`: Cycles posters 2400 px (denoised) for hero + props, turntable WebM/MP4 < 8 MB
- [ ] budgets: hero.glb <= 12 MB, each prop <= 4 MB

### Site
- [ ] Three.js: procedural studio environment (PMREM), new materials hooks, tile dissolve shader (break apart / reassemble)
- [ ] scroll-driven cinematic camera around/through the hero across the main page (fixed backdrop layer)
- [ ] per-section 3D scenes (rings in "Three ways", plates in "Report card", bars in "Crises", coin in footer),
      lazy-loaded, parallax + mouse tilt, reduced-motion = static
- [ ] intro: particles, light streaks, depth-of-field blur, chromatic fringe; word-by-word manifesto with scramble; smoother block/checker transition
- [ ] KAIB-style detailing: hairline frame with corner ticks, animated counters, marquee strip, richer footer + final 3D piece, grain, desktop-only cursor
- [ ] fallbacks: poster images / turntable video when WebGL fails
- [ ] fix: bottom-right intro label unreadable over checker squares
- [ ] fix: "Scroll To Start NN" stays visible after the page turns white -> becomes a section indicator
- [ ] fix: empty gap under the hero buttons before section 01

### Verify
- [ ] Playwright screenshots 1440x900 + 390x844 of every stage, >= 4 review rounds, finals as `docs/shots/v2-*`
- [ ] console clean, numbers match the original, frame-time probe, reduced motion, 390 px, no CDN
- [ ] README, NOTES, C:\Jarvis\log.md

### Progress log
- (empty)

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
