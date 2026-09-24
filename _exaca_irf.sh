#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== CAinterfacialresponse.hpp 结构（1-70 行）:"; sed -n '1,70p' src/CAinterfacialresponse.hpp
echo; echo "=== 输入里 function 的解析:"; grep -n -B4 -A24 'function\[phase\]\|inputs.function\|== function' src/CAinputs.hpp | head -50