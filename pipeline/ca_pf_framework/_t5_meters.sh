#!/bin/bash
# _t5_meters.sh --- 摸清"三条持续观测"各自由哪些量具测量（供随后做量具验证）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① abA 的 series.csv 全部列（末行值）════'
$PY - <<'PYEOF'
import csv
rows = list(csv.DictReader(open('_exp/_bk_mb/dry_abA/series.csv',
                                encoding='utf-8', errors='replace')))
last = rows[-1]
print('  共 %d 列\n' % len(last))
for i, (k, v) in enumerate(last.items()):
    print('   %-22s = %s' % (k, (v or '')[:40]))
PYEOF
