#!/usr/bin/env bash
# R518b —— 找 abA/abB 的 stdout 日志（**只在当前目录**，不递归进 _exp/）
set -u
cd "$(dirname "$0")"
echo "=== 1. 当前目录的 .log 里含 'tag abA' 的 ==="
grep -l -- '--tag abA' _w2_*.log 2>/dev/null | head -8
echo "--- tag abB ---"
grep -l -- '--tag abB' _w2_*.log 2>/dev/null | head -8

echo
echo "=== 2. 启动脚本里含 'tag abA' 的 ==="
grep -l 'tag abA' *.sh 2>/dev/null | head -8

echo
echo "=== 3. 07:00-08:30 之间写的 _w2_*.log（abA 起跑段） ==="
ls -la --time-style=+%m-%d_%H:%M _w2_*.log 2>/dev/null | awk '$6 ~ /10-01_0[78]/' | head -14

echo
echo "=== 4. abA/abB 的 nuc_dbg.json ==="
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import json
for t in ('dry_abA', 'dry_abB'):
    try:
        with open('_exp/_bk_mb/%s/nuc_dbg.json' % t) as fh:
            d = json.load(fh)
        print('  %s:' % t)
        for k, v in d.items():
            print('     %-18s = %s' % (k, str(v)[:150]))
    except Exception as e:
        print('  %s: %r' % (t, e))
PYEOF
