#!/bin/bash
cd /mnt/f/speed_up/bench/exaca
echo "======== TwoGrainDirSolidification:"; cat Inp_TwoGrainDirSolidification.json
echo; echo "======== DirSolidification:"; cat Inp_DirSolidification.json
echo; echo "======== EquiaxedGrain:"; cat Inp_EquiaxedGrain.json
echo; echo "======== README 里与"预期/验证"有关的段落:"
grep -n -i -B2 -A6 'expected\|verif\|validat\|compare\|reproduce' README.md | head -80