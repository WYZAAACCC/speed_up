#!/bin/bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _patch_oct_scalar.py || exit 2
/root/miniconda3/envs/ml/bin/python -c "import ast,io; ast.parse(io.open('/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py',encoding='utf-8').read()); print('syntax OK')"
echo "=== 单元测试（应 8/8）:"; /root/miniconda3/envs/ml/bin/python _unit_oct.py 2>&1 | tail -4
echo "=== 几何:"; OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python _verify_cell_geom.py 2>&1 | tail -5