#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== Interface 构造处（找 init_oct_size 的值）:"; grep -rn 'init_oct_size' src/*.hpp src/*.cpp | head -10
echo; echo "=== 传入的值:"; grep -rn -B3 -A3 'Interface<' src/runCA.hpp | head -20