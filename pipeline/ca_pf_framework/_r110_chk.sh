#!/bin/bash
# _r110_chk.sh —— R110 三臂启动核对：t=0 分离判据 + 步时 + 内存
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
ps -eo pid,etimes,rss,args --no-headers | grep '[_]bk_exp' | \
  awk '{printf "  pid=%-7s %5ss  rss=%6.0f MB\n", $1, $2, $3/1024}'
free -g | awk 'NR==1||NR==2'
echo
for t in saPair saPairE0 saOdd; do
  L="_w2_r110_${t}.log"
  [ -f "$L" ] || { echo "--- $t （无日志）"; continue; }
  echo "--- $t"
  grep -E "exceeds domain|ValueError|Traceback" "$L" | head -2
  tail -1 "$L" | cut -c1-135
done
echo
echo "--- step0 判据（`nf2(t=0)==0` 且 `nblk_sig==6`）---"
$PY - <<'PY'
import csv, os
for t in ('saPair', 'saPairE0', 'saOdd'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-9s （无 series.csv）' % t); continue
    rs = list(csv.DictReader(open(p)))
    r0, r1 = rs[0], rs[-1]
    print('  %-9s step0: nf2=%-6s nblk_sig=%-3s blk_laths=%-13s blk_nprof=%-13s | 末(%s) r_selfac=%s'
          % (t, r0.get('nf2'), r0.get('nblk_sig'), r0.get('blk_laths'),
             r0.get('blk_nprof'), r1.get('step'), r1.get('r_selfac')))
PY
