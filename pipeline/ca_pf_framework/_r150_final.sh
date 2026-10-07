#!/bin/bash
# _r150_final.sh —— 一屏：回归里的自检痕迹 + 两条长跑的进度
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)"
free -g | awk 'NR==2{printf "内存：%s GB available\n", $7}'
echo
echo "=== 回归那次运行里，自检有没有打出来 ==="
grep -n '块内界面自检\|cov_norm' _w2_r30_regress_run.log 2>/dev/null | head -4 || echo "  （没找到）"
echo
echo "=== R141 自协调（同几何）==="
for t in saOddG saSet2; do
  printf -- '  %-8s %s\n' "$t" "$(grep 's/步' _w2_r141_${t}.log 2>/dev/null | tail -1 | cut -c1-100)"
done
echo
echo "=== R139 选支对照 v2 ==="
for t in swN128 swINV128; do
  printf -- '  %-9s %s\n' "$t" "$(grep 's/步' _w2_r139_${t}.log 2>/dev/null | tail -1 | cut -c1-100)"
done
echo
echo "=== R141 的 r_selfac 轨迹（判据 SA-1/SA-2）==="
$PY - <<'PY'
import csv, os
for t in ('saOddG', 'saSet2'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-8s （无）' % t); continue
    rs = list(csv.DictReader(open(p)))
    print('  %-8s 行数=%-4d  %s' % (t, len(rs),
          '  '.join('s%s:r=%s,nf2=%s,touch=%s' % (r.get('step'), r.get('r_selfac'),
                                                  r.get('nf2'), r.get('box_touch_core'))
                    for r in rs[::max(1, len(rs)//5)][-4:] + [rs[-1]])))
PY
