#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_patch_cell2.py || exit 2
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io, sys
s = io.open('/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py', encoding='utf-8').read()
ast.parse(s); print('syntax OK, lines =', s.count(chr(10))+1)
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
import ca3d
ca = ca3d.CA3D(6,6,6,1e-6, capture='cell')
ca.add_grain(3,3,3)
print('capture=cell 构造 OK')
EOF