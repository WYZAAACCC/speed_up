#!/bin/bash
# _r114_prog.sh —— R110 三臂进度 + r_selfac 轨迹（本实验的核心观测量）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
ps -eo pid,etimes,rss,args --no-headers | grep '[_]bk_exp' | \
  awk '{printf "  pid=%-7s %5ss  rss=%6.0f MB\n", $1, $2, $3/1024}'
echo
for t in saPair saPairE0 saOdd; do
  printf -- '--- %-9s %s\n' "$t" "$(tail -1 _w2_r110_${t}.log 2>/dev/null | cut -c1-70)"
done
echo
$PY - <<'PY'
import csv, os
print('  %-9s %-7s %-11s %-11s %-9s %-8s %s'
      % ('臂', 'step', 'r_selfac', 'r_norm~', 'nf2', 'V0(µm³)', 'span(块0)'))
for t in ('saPair', 'saPairE0', 'saOdd'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-9s （无）' % t); continue
    rs = list(csv.DictReader(open(p)))
    for r in rs[::max(1, len(rs)//5)][-4:] + [rs[-1]]:
        try:
            v0 = float(r.get('V0', 'nan')) * 1e18
        except (TypeError, ValueError):
            v0 = float('nan')
        vs = [x for x in str(r.get('blk_vars','')).split('/') if x.strip()]
        sp = [x for x in str(r.get('blk_span_nm','')).split('/') if x.strip()]
        s0 = '?'
        try:
            s0 = sp[[int(float(v)) for v in vs].index(1)]
        except (ValueError, IndexError):
            pass
        print('  %-9s %-7s %-11s %-11s %-9s %-8.4f %s'
              % (t, r.get('step'), r.get('r_selfac'), '', r.get('nf2'), v0, s0))
PY
