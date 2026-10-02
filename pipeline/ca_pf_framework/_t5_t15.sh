#!/bin/bash
# _t5_t15.sh --- 第 15 轮状态：Vt 是否反转
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
for t in t5L62 t5L0; do
  $PY - "$t" <<'PYEOF'
import csv, sys, os
t = sys.argv[1]
p = '_exp/_bk_t5/dry_%s/series.csv' % t
if not os.path.exists(p):
    print('  %s ⚠ 无 series' % t); raise SystemExit
r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
print('  ── %s：%d 行 ──' % (t, len(r)))
print('     %-6s %-15s %-7s %-7s %-7s' % ('step', 'Vt', 'nf3', 'nslab', 'box_touch'))
for x in r[-8:]:
    print('     %-6s %-15s %-7s %-7s %-7s'
          % (x['step'], x['Vt'][:15], (x.get('nf3') or '')[:7],
             (x.get('nslab_n') or '')[:7], (x.get('box_touch') or '')[:7]))
v = [float(x['Vt']) for x in r if (x.get('Vt') or '').strip()]
if len(v) >= 3:
    print('     末三行 Vt = %s ⇒ **%s**' % (['%.4g' % z for z in v[-3:]],
          '升 ↑' if v[-1] > v[-2] else '降 ↓'))
    lo = min(v)
    print('     全程最低 = %.4g（在"下降段"的最低点）' % lo)
PYEOF
done
echo
/root/miniconda3/envs/ml/bin/python -c "
import csv
r=list(csv.DictReader(open('_exp/_bk_mb/dry_abA/series.csv',encoding='utf-8',errors='replace')))
v=[(int(x['step']),float(x['Vt'])) for x in r if (x.get('Vt') or '').strip()]
print('  对照 abA 早段：', [(s,'%.3g'%y) for s,y in v[:9]])
" 2>/dev/null
