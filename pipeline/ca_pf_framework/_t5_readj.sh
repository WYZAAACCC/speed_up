#!/bin/bash
# _t5_readj.sh --- 读诊断跑的 nuc_dbg.json（形核落位的归因计数）
cd "$(dirname "$0")" || exit 1
J=_exp/_bk_t5/dry_t5diag/nuc_dbg.json
echo '════ 诊断跑（N=96/120 步/abA 物理）的形核归因 ════'
if [ -f "$J" ]; then
  /root/miniconda3/envs/ml/bin/python - "$J" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print('  顶层键：%s' % list(d))
for k in sorted(d):
    v = d[k]
    if isinstance(v, dict):
        print('  ── %s ──' % k)
        for kk in sorted(v):
            print('     %-20s = %s' % (kk, v[kk]))
    else:
        print('  %-22s = %s' % (k, str(v)[:70]))
PYEOF
else
  echo "  ❌ $J 不存在"
fi
echo
echo '════ 同一跑的日志里形核/拒绝行 ════'
grep -nE 'athermal|被引擎拒|形核诊断' _w2_t5_short_t5diag.log 2>/dev/null | head -14 | cut -c1-126 | sed 's/^/  /'
