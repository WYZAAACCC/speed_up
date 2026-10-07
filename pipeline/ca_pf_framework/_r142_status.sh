#!/bin/bash
# _r142_status.sh —— R139（选支 v2）/ R141（自协调同几何）状态
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)"
free -g | awk 'NR==2{printf "内存：%s GB available\n", $7}'
echo
for t in swN128 swINV128; do
  printf -- '--- R139 %-10s %s\n' "$t" "$(grep -c 's/步' _w2_r139_${t}.log 2>/dev/null) 个读数"
  grep 's/步' "_w2_r139_${t}.log" 2>/dev/null | tail -1 | cut -c1-115
done
echo
for t in saOddG saSet2; do
  printf -- '--- R141 %-8s %s\n' "$t" "$(grep -c 's/步' _w2_r141_${t}.log 2>/dev/null) 个读数"
  grep 's/步' "_w2_r141_${t}.log" 2>/dev/null | tail -1 | cut -c1-115
done
echo
echo "--- SA-0：两臂 step0 ---"
$PY - <<'PY'
import csv, os
for t in ('saOddG', 'saSet2'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-8s （无数据）' % t); continue
    rs = list(csv.DictReader(open(p)))
    r0, r1 = rs[0], rs[-1]
    print('  %-8s step0: nf2=%-4s nblk=%-3s blk_laths=%-13s blk_nprof=%-13s | 末(%s) r=%s'
          % (t, r0.get('nf2'), r0.get('nblk_sig'), r0.get('blk_laths'),
             r0.get('blk_nprof'), r1.get('step'), r1.get('r_selfac')))
PY
