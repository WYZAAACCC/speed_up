#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 各臂步数'
for d in _exp/_bk_mb/dry_mb1L _exp/_bk_mb/dry_mb1Ls _exp/_bk_mb/dry_b62f; do
  [ -f "$d/series.csv" ] || continue
  printf '  %-26s step=%-6s snap=%s\n' "$d" \
    "$(tail -1 "$d/series.csv" | cut -d, -f1)" "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
echo
echo '=== b62f 的 J-2/J-4 预览'
/root/miniconda3/envs/ml/bin/python - <<'PY'
import csv, os
p = '_exp/_bk_mb/dry_b62f/series.csv'
rows = list(csv.DictReader(open(p)))
cs = [c for c in ('step','nslab_n','nf3_col','nf2','f2_area_m2','box_touch',
                  'box_touch_core','nslab_nu','Vt') if c in rows[0]]
print('  ' + ' '.join('%-12s' % c for c in cs))
for r in rows[::3][:8] + [rows[-1]]:
    print('  ' + ' '.join('%-12s' % str(r.get(c, ''))[:12] for c in cs))
PY
echo
echo '=== 进程'; ps -eo pcpu,rss,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "  %5s%% %5dMB %6ss\n",$1,$2/1024,$3}'
uptime; free -g | head -2
