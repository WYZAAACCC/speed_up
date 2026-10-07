#!/bin/bash
# _t5_threecmp2.sh --- 从**启动脚本**取三臂的逐字参数（确定来源）+ 查存活
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ 三臂的**逐字启动参数**（取自启动脚本）════'
for t in t5AD_500 t5AD_700 t5AM_combo; do
  echo "  ── $t ──"
  grep -B1 -A7 -- "--tag $t " _t5_ab_dose2.sh _t5_dose_hi.sh _t5_relaunch_mob2.sh _t5_ab_mob.sh 2>/dev/null \
    | grep -vE '^--$|^_t5_.*\.sh-' | sed 's/^/     /'
  echo
done
echo '════ 三臂是否还活着 ════'
for t in t5AD_500 t5AD_700 t5AM_combo; do
  printf '  %-12s 进程=%s  末步=%s\n' "$t" \
    "$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t")" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ 引擎进程总数 ════'
ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py'
