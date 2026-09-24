#!/bin/bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _fix_oct.py || exit 2
echo "=== 单元测试重跑:"
/root/miniconda3/envs/ml/bin/python _unit_oct.py 2>&1 | tail -12