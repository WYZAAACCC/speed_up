#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '=== m3out10b 状态'
tail -3 _w2_r74_run.log 2>/dev/null
d=_exp/_bk_mb/dry_m3out10b
if [ -f "$d/series.csv" ]; then
  echo "  step=$(tail -1 "$d/series.csv" | cut -d, -f1)"
  echo
  echo '=== P-1/P-4：nslab_n 全程 + 撞壁'
  $PY - <<'PY'
import csv, os
p = '_exp/_bk_mb/dry_m3out10b/series.csv'
rows = list(csv.DictReader(open(p)))
print('  nslab_n 序列(每80步):', [r['nslab_n'] for r in rows[::4]])
print('  nf3_col  序列(每80步):', [r['nf3_col'] for r in rows[::4]])
print('  box_touch_core 取值:', sorted({r.get('box_touch_core','') for r in rows}))
r = rows[-1]
print('  末态: step=%s nslab_n=%s nf3_col=%s Vt=%s' % (r['step'], r['nslab_n'], r['nf3_col'], r['Vt'][:10]))
PY
  echo
  echo '=== 与三条参照臂的终态对照'
  $PY - <<'PY'
import csv, os
for t in ('m3fp0', 'm3fp10', 'm3out10', 'm3out10b'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-10s （无）' % t); continue
    r = list(csv.DictReader(open(p)))[-1]
    print('  %-10s step=%-4s nslab_n=%-3s nf3_col=%-3s Vt=%s'
          % (t, r['step'], r['nslab_n'], r['nf3_col'], r['Vt'][:10]))
PY
  echo
  echo '=== P-2/P-3：f_flat 与判词'
  timeout 900 $PY _r65_corner.py "$d" 2>&1 | grep -E '首末'
  timeout 600 $PY _r53_v2run.py "$d" 2>&1 | grep -E '全程'
else
  echo '  （无产物）'
fi
