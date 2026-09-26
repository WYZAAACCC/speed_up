#!/bin/bash
F=/mnt/f/speed_up/pipeline/gibbs/validated/proto3d_gibbs_coupled.i.tpl
echo "=== [Kernels] ==="
awk '/^\[Kernels\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F" | grep -E "^  \[|type ="
echo "=== [Materials] ==="
awk '/^\[Materials\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F" | grep -E "^  \[|type ="
echo "=== [Constraints] ==="
awk '/^\[Constraints\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F" | grep -E "^  \[|type =|secondary|primary|variable|kex"
echo "=== [BCs] ==="
awk '/^\[BCs\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F" | grep -E "^  \[|type ="