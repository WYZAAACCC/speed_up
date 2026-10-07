#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for f in windowB_surface.py windowB_wulff.py _bk_exp.py; do
  $PY -c "import ast;ast.parse(open('$f').read())" && echo "SYNTAX-OK  $f" || echo "SYNTAX-FAIL $f"
done
echo '--- 检查 nd_ref_ / wtab 在该作用域可用'
sed -n '3355,3375p' windowB_surface.py | grep -nE 'nd_ref_|wtab|ndir_' | head -6
