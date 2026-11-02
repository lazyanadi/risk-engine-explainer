@echo off
rem Pass 1 of 2: loop + whole frame, floor shortened so it does not hide the frame. Output C:Jarvis	mp5hero_final.png
set RE_MODE=both
set RE_SCALE=1.0
set RE_SAMPLES=120
set RE_PITCH=20
set RE_ROLL=-34
set RE_YAW=-25
set RE_SIDE=-1
set RE_FLOORGAP=0.12
set RE_FLOORY=-0.4
set RE_EXP=0.2
set RE_WORLD=0.6
set RE_NAME=hero_final.png
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "%~dp0v5_hero.py"
