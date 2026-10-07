#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for f in windowB_surface.py _r68_facet_op.py _bk_exp.py; do
  $PY -c "import ast;ast.parse(open('$f').read())" && echo "SYNTAX-OK  $f" || echo "SYNTAX-FAIL $f"
done
echo '--- facet_project 接线点'
grep -n 'facet_proj\|def facet_project' windowB_surface.py | head -8
