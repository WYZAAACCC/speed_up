#!/bin/bash
echo "=== 磁盘:"; df -h / /mnt/f | tail -3
mkdir -p /root/bench && cd /root/bench
echo; echo "=== 取 Small 算例与 unit_test 清单:"
cd /mnt/f/speed_up/bench/exaca_src/ExaCA-master
ls examples/Inp_Small*.json unit_test/ 2>/dev/null | head -30
echo; echo "=== SmallDirSolidification:"; cat examples/Inp_SmallDirSolidification.json
echo; echo "=== 单元测试目录内容:"; ls -R unit_test 2>/dev/null | head -40