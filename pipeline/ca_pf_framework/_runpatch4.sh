#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _patch_step4.py
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io, sys
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py", encoding="utf-8").read()
ast.parse(s); print("syntax OK, lines =", s.count(chr(10))+1)
EOF
# CA3DSolute 自己做化学 => 关掉 CA3D 内置的，避免双重记账
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d_solute.py"
s = io.open(P, encoding="utf-8").read()
old = "        CA3D.__init__(self, nx, ny, nz, dx, irf=irf, seed=seed)"
new = "        CA3D.__init__(self, nx, ny, nz, dx, irf=irf, seed=seed, chem_local=False)"
if old not in s:
    print("!! ca3d_solute 锚点未找到"); raise SystemExit(1)
io.open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("ca3d_solute: chem_local=False（子类自己做化学）")
EOF