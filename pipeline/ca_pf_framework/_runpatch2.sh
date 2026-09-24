#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _patch_step2.py
echo "rc=$?"
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io, sys
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py", encoding="utf-8").read()
ast.parse(s); print("syntax OK, lines =", s.count(chr(10))+1)
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import ca3d, numpy as np
c = ca3d.CA3D(20,20,20,1e-6, seed=1)
c.nucleate_substrate_grid(2,2)
T = np.full(c.shape, 300.0)
n = c.seed_solid_from_substrate(T, ca3d.T_SOL)
print("基底填充", n, "胞; 各晶粒胞数", {int(g): int((c.gid==g).sum()) for g in np.unique(c.gid) if g>0})
EOF