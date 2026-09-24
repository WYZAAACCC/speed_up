#!/bin/bash
cd /root/bench/ExaCA-master
echo "=== _init_oct_size 定义:"; grep -rn '_init_oct_size' src/*.hpp | head -6
echo; echo "=== createNewOctahedron 中段（角点选择 -> ℓ_new）:"
awk '/Determine which of the 3 corners/,/octahedron_data\[3\] = new_octahedron_diag_length/' src/CAinterface.hpp