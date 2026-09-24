#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== 源文件:"; ls src/ | tr '\n' ' '
echo; echo "=== SurfaceSiteDensity 的语义:"; grep -rn -A12 'SurfaceSiteDensity' src/*.hpp src/*.cpp 2>/dev/null | head -50
echo; echo "=== Directional 的初始温度/过冷:"; grep -rn -B3 -A18 'InitUndercooling' src/*.hpp src/*.cpp 2>/dev/null | head -60