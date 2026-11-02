@echo off
rem Hero loop: 144 frames (6 s at 24 fps) of the panel pop wave, resumable. Frames: C:\Jarvis\tmp\v5-loop\fNNNN.png
rem Then: node scripts/encode_loop_v5.mjs  (adds the thin grey frame behind, flattens on white, writes assets/v5/)
set RE_MODE=loop
set RE_NOFRAME=1
set RE_SCALE=0.7
set RE_SAMPLES=44
set RE_PITCH=27
set RE_ROLL=-34
set RE_YAW=-25
set RE_SIDE=-1
set RE_FLOORGAP=0.12
set RE_FLOORY=1.0
set RE_EXP=0.2
set RE_WORLD=0.6
set RE_POP=0.38
set RE_TH=0.56
set RE_HW=0.28
set RE_TAPER=0.7
set RE_PANELS=56
set RE_OUT=C:/Jarvis/tmp/v5-loop
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "%~dp0v5_hero.py"
