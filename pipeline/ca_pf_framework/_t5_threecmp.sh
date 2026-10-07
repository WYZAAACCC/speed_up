#!/bin/bash
# _t5_threecmp.sh --- ★★★ `t5AM_combo` / `t5AD_700` / `t5AD_500` 的**实际参数**逐项对照
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
for t in t5AD_500 t5AD_700 t5AM_combo; do
  echo "════════ $t ════════"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep "dry_$t" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  （运行中 pid=$P —— 取**实际命令行**）"
    tr '\0' '\n' < /proc/$P/cmdline 2>/dev/null | grep -E '^--' | paste - - 2>/dev/null \
      | grep -E 'tag|N$|nvar|^-*m$|B$|steps|cores|overlap|eng-elong|mob-|facet|var-rule|nuc-law|every|snap' \
      | sed 's/^/     /'
  else
    echo "  （进程不在 —— 从**启动脚本**取，脚本里是逐字参数）"
    grep -A6 "\-\-tag $t " _t5_ab_dose2.sh _t5_dose_hi.sh _t5_relaunch_mob2.sh _t5_ab_mob.sh 2>/dev/null \
      | head -10 | sed 's/^/     /'
  fi
  echo
done
