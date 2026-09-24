#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== freezing_range 的用法:"; grep -rn -B2 -A8 'freezing_range' src/CAinterfacialresponse.hpp src/CAtemperature.hpp 2>/dev/null | head -40
echo; echo "=== 形核: 密度单位与谱:"; grep -rn -B3 -A20 'nucleation_density\|N0\|dT_sigma\|mean_undercooling' src/CAnucleation.hpp 2>/dev/null | head -60