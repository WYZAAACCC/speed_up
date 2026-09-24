#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== getUndercooling 的定义（Directional 用哪个）:"; grep -n -B3 -A18 'float getUndercooling' src/CAtemperature.hpp | head -50
echo; echo "=== 是否按 freezing range 归一:"; grep -n 'freezing_range' src/CAtemperature.hpp | head -10