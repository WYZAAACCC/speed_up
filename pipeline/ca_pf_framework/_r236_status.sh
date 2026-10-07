#!/bin/bash
# _r236_status.sh —— 两个在跑作业的状态一览。
cd "$(dirname "$0")" || exit 1
echo "=== ① _r210（真实 R165 几何 + diag-terms）==="
for d in saSet2DT saOddGDT; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-12s rows=%-4s last_step=%s\n' "$d" "$(wc -l < "$f")" \
      "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-12s (未开始)\n' "$d"
  fi
done
echo "  _r210.log 尾：$(tail -1 _w2_r210.log 2>/dev/null)"
echo
echo "=== ② _r225（P1-45：ladder vs perstep，几何 m6a）==="
for d in p45L p45P; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-8s rows=%-4s last_step=%-6s f3_area(µm²)=%s\n' "$d" \
      "$(wc -l < "$f")" "$(tail -1 "$f" | cut -d, -f1)" \
      "$(/root/miniconda3/envs/ml/bin/python -c "
import csv,sys
r=list(csv.DictReader(open('$f')))[-1]
print('%.4f' % (float(r['f3_area_m2'])*1e12))" 2>/dev/null || echo '?')"
  else
    printf '  %-8s (未开始)\n' "$d"
  fi
done
echo "  Traceback 检查：L=$(grep -c Traceback _w2_r225_p45L.log 2>/dev/null || echo NA) P=$(grep -c Traceback _w2_r225_p45P.log 2>/dev/null || echo NA)"
echo
echo "=== ③ 进程 / 内存 ==="
echo "  _bk_exp.py 进程数 = $(pgrep -fc '_bk_exp[.]py' || true)"
free -m | head -2 | sed 's/^/  /'
echo
echo "=== ④ 台账 / 摘要 ==="
printf '  ledger = %s 行；summary = %s 行\n' \
  "$(wc -l < R30_AUDIT_LEDGER.md)" "$(wc -l < AUDIT_SUMMARY_R76.md)"
