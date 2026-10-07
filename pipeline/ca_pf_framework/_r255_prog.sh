#!/bin/bash
# _r255_prog.sh —— 关键臂进度 + saSet2DT 末态关键列。
cd "$(dirname "$0")" || exit 1
echo "=== 进度 ==="
for d in saSet2DT saOddGDT p45L p45P p45L0 p45P0 saSet2EDV; do
  f="_exp/_bk_mb/dry_$d/series.csv"
  if [ -f "$f" ]; then
    printf '  %-12s rows=%-4s last_step=%-6s\n' "$d" "$(wc -l < "$f")" \
      "$(tail -1 "$f" | cut -d, -f1)"
  else
    printf '  %-12s (未开始)\n' "$d"
  fi
done
echo
echo "=== saSet2DT 末态关键列（**已跑满 400 步**）==="
/root/miniconda3/envs/ml/bin/python - <<'PY'
import csv
p = '_exp/_bk_mb/dry_saSet2DT/series.csv'
rows = list(csv.DictReader(open(p)))
r = rows[-1]
print('  末步 = %s（共 %d 行）' % (r['step'], len(rows)))
for k in ('f3_area_m2', 'f2_area_m2', 'f1_area_m2', 'Vt', 'nf2', 'nf3',
          'nf1', 'r_selfac', 'blk_nprof', 'blk_span_nm'):
    v = r.get(k)
    if v in (None, ''):
        print('  %-14s （列不存在）' % k)
        continue
    try:
        print('  %-14s %.6g' % (k, float(v)))
    except ValueError:
        print('  %-14s %s' % (k, v))
PY
echo
echo "=== saSet2DT 三项量级命中数 ==="
grep -c '三项量级' _w2_r210_saSet2_run.log 2>/dev/null || echo 0
