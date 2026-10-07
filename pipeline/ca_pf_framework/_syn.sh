#!/usr/bin/env bash
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'EOF'
import ast
for f in ('T13b_verify_nv.py', 'T17_converge.py', 'T24_verify_grouping.py',
          'T21_beta_calib.py', 'windowB_surface.py'):
    ast.parse(open(f).read())
    print('SYNTAX OK', f)
EOF
