#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
/root/miniconda3/envs/ml/bin/python - <<'PY'
import ast
for f in ('_r1_exp.py', '_r1_analyze.py'):
    ast.parse(open(f, encoding='utf-8').read())
    print('SYNTAX OK', f)
PY
