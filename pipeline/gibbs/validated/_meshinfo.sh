#!/bin/bash
L=/mnt/f/speed_up/pipeline/gibbs/results_p3d/run.log
[ -f "$L" ] || L=/root/work/p3d/run.log
echo "=== Mesh Information ==="
sed "s/\x1b\[[0-9;]*m//g" "$L" | awk '/Mesh Information/{f=1} f{print} /^$/{if(f&&++c>2) exit}' | head -60