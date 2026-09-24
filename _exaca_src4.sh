#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== Angle_z 的定义:"; grep -rn -B6 -A4 'Angle_z' src/*.hpp src/*.cpp | head -40
echo; echo "=== idle frame / 增量输出的条件:"; grep -rn 'print_idle\|PrintIdleFrames\|Increment\|intralayer' src/CAprint.hpp src/runCA.hpp 2>/dev/null | head -20