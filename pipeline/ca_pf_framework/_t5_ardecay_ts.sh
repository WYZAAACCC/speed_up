#!/bin/bash
# _t5_ardecay_ts.sh --- ★★★★★ `t5N276` 的长宽比**完整时间序列**（判定"继续衰减 or 止跌"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ t5N276 长宽比/长厚比 全序列（按 step 去重）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import re
PAT = re.compile(r'\]\s+(\S+)\s+step\s+(\d+)\s+场=(\d+)\s+\*\*长宽比 中位 ([\d.]+)'
                 r'[^\n]*?\*\*长厚比 中位 ([\d.]+)')
seen = {}
for line in open('_w2_t5_ar_monitor.log', errors='ignore'):
    m = PAT.search(line)
    if m and m.group(1) == 't5N276':
        seen[int(m.group(2))] = (int(m.group(3)), float(m.group(4)), float(m.group(5)))
rows = sorted(seen.items())
print('  %-7s %-6s %-10s %-10s %s' % ('step', '场数', '长宽比', '长厚比', '相对峰值'))
pk = max(r[1][1] for r in rows) if rows else 0
for st, (n, ar, lt) in rows:
    bar = '█' * max(1, int(ar * 4))
    print('  %-7d %-6d %-10.2f %-10.2f %+6.1f%%  %s' % (st, n, ar, lt, (ar / pk - 1) * 100, bar))
print()
print('  峰值 = %.2f ｜ 末值 = %.2f ｜ **总跌 %.0f%%**' % (pk, rows[-1][1][1], (1 - rows[-1][1][1] / pk) * 100))
# 分段趋势：最后一个值 vs 倒数第 3 个
if len(rows) >= 3:
    a = rows[-3][1][1]; b = rows[-1][1][1]
    print('  最近三点：%.2f → %.2f ⇒ %s' % (a, b,
          '**仍在跌**' if b < a - 0.05 else ('**止跌/回升**' if b > a + 0.05 else '**持平**')))
PYEOF
