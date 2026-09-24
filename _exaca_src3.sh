#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== CAnucleation.hpp 里的函数与密度:"; grep -n 'void \|double \|nuc_den\|density\|M_PI\|exp(' src/CAnucleation.hpp | head -40
echo; echo "--- placeNuclei:"; sed -n '/placeNuclei/,/^    }/p' src/CAnucleation.hpp | head -55
echo; echo "=== 形核输入解析:"; grep -n -B3 -A12 'Nucleation' src/CAinputs.hpp | head -45