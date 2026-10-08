#!/usr/bin/env bash
# _r712_syntax.sh —— 对所有验证脚本做 py_compile（归档后路径修正的验证）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python
FILES="
_auditR712_check.py
_auditR712_final_check.py
_auditR712_verify.py
_auditR712_citecheck2.py
_auditR712_D2.py
_r712_work/_auditR708_facetproj.py
_r712_work/_auditR708_p01_p14.py
_r712_work/_goal_unit_guard.py
_r712_work/_goal_C_settle.py
_r712_work/_goal_growth_TRUE3.py
_r712_work/_goal_A_search.py
"
BAD=0
for f in $FILES; do
  if ! $PY -m py_compile "$f" 2>/tmp/e; then
    echo "FAIL  $f"
    cat /tmp/e
    BAD=1
  fi
done
if [ $BAD -eq 0 ]; then echo "OK：全部 $(( $(echo "$FILES" | grep -c .) )) 个脚本 py_compile 通过"; fi
