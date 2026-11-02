@echo off
rem v6 hero loop: panels on all four faces, two wave fronts, champagne tint. 144 frames, resumable.
rem Frames: C:\Jarvis\tmp\v6-loop\fNNNN.png   Then: node scripts/encode_loop_v5.mjs C:/Jarvis/tmp/v6-loop assets/v6
set RE_MODE=loop
set RE_NOFRAME=1
set RE_SCALE=0.7
set RE_SAMPLES=48
set RE_PITCH=27
set RE_ROLL=-34
set RE_YAW=-25
set RE_SIDE=-1
set RE_FLOORGAP=0.12
set RE_FLOORY=1.0
set RE_EXP=0.2
set RE_WORLD=0.6
set RE_TAPER=0.7
set RE_OUT=C:/Jarvis/tmp/v6-loop
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "%~dp0v6_hero.py"
