#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_patch_cell3.py || exit 2
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io, sys
s = io.open('/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py', encoding='utf-8').read()
ast.parse(s); print('syntax OK, lines =', s.count(chr(10))+1)
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
import numpy as np, ca3d
ca = ca3d.CA3D(8,8,8,1e-6, capture='cell'); g = ca.add_grain(4,4,4)
T = ca.T_iso(12.0)
for s_ in range(30):
    ca.t = s_*1e-7; ca.step(1e-7, T, window='full')
print('cell 跑 30 步: 晶粒胞数 =', int((ca.gid>0).sum()), ' (单胞种子应长大)')
EOF