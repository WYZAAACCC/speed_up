#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '=== 进程'
ps -eo pid,pcpu,rss,etimes,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | awk '{printf "  %-7s %5s%% %5dMB %6ss %s\n",$1,$2,$3/1024,$4,$5}'
echo
echo '=== b62f 日志尾'
tail -3 _w2_r52_b62f.log 2>/dev/null | cut -c1-160
echo "  产物 mtime: $(stat -c %y _exp/_bk_mb/dry_b62f/series.csv 2>/dev/null | cut -c1-19)"
echo "  现在:       $(date '+%F %T')"
echo
echo '=== b62f 的 J-3 进度（nf2 应开始增大）'
/root/miniconda3/envs/ml/bin/python - <<'PY'
import csv, os
p = '_exp/_bk_mb/dry_b62f/series.csv'
rows = list(csv.DictReader(open(p)))
cs = [c for c in ('step','nslab_n','nf3_col','nf2','f2_area_m2','box_touch','box_touch_core') if c in rows[0]]
print('  ' + ' '.join('%-11s' % c for c in cs))
for r in rows[::4][-6:]:
    print('  ' + ' '.join('%-11s' % str(r.get(c,''))[:11] for c in cs))
PY
