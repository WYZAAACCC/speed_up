#!/bin/bash
# _bk_syn.sh <file.py> ...  —— 语法检查（不在 PowerShell 里内联 python -c）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for f in "$@"; do
  "$PY" - "$f" <<'PYEOF'
import ast, sys
p = sys.argv[1]
ast.parse(open(p, encoding='utf-8').read())
print('syntax OK:', p)
PYEOF
done
