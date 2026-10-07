#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
for f in windowB_surface.py _bk_exp.py _bk_verdict.py _r49_dgacct.py _r49_cadence.py; do
  $PY -c "import ast;ast.parse(open('$f').read())" && echo "SYNTAX-OK  $f" || echo "SYNTAX-FAIL $f"
done
echo '--- _face_masks / v_by_face 接线点'
grep -n '_face_masks\|v_by_face' windowB_surface.py
