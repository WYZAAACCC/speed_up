#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose
echo "=== README (前 60 行):"; head -60 README.md
echo; echo "=== B_3D / B3_3D 内容:"; ls B_3D | head -15; echo '---'; ls B3_3D | head -15
echo; echo "=== 最近改动的文件（前 12）:"; ls -lat | head -14