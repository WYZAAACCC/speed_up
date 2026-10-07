#!/bin/bash
# _r299_verifyptr.sh —— 核对补记指针是否落在**正确的节**里，并复跑自查。
cd "$(dirname "$0")" || exit 1
echo "=== 每处补记指针的上下文（前 1 行 / 本行 / 后 1 行）==="
grep -n '本节已被.*撤回/更正（\*\*补记\*\*）' R30_AUDIT_LEDGER.md | cut -d: -f1 \
| while read -r L; do
    echo "  --- 行 $L ---"
    sed -n "$((L-1)),$((L+2))p" R30_AUDIT_LEDGER.md | sed 's/^/    /'
  done
echo
echo "=== 复跑自查（期望：真阳性 = 0）==="
/root/miniconda3/envs/ml/bin/python -u _r298_ledgerfix.py 2>&1 | tail -14
