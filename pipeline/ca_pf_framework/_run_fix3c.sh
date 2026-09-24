#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _patch_step4b.py
/root/miniconda3/envs/ml/bin/python - <<'EOF'
import ast, io
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py", encoding="utf-8").read()
ast.parse(s); print("syntax OK, lines =", s.count(chr(10))+1)
EOF
/root/miniconda3/envs/ml/bin/python _verify_fix3.py