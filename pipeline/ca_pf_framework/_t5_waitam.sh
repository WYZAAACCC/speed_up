#!/bin/bash
# _t5_waitam.sh --- 等到 t5AM_* 有读数再打印（第 23 条：把等待放进一次调用）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_ar_monitor.log
for i in $(seq 1 30); do          # 最多 30 × 20 s = 10 min
  N=$(grep -cE '  t5AM_(ell|combo) +step ' "$L" 2>/dev/null || echo 0)
  [ "$N" -gt 0 ] && break
  sleep 20
done
echo "NOW = $(date '+%F %T')   （t5AM_ 读数条数 = $N）"
echo '════ 迁移率臂（新）════'
grep -E '  t5AM_(ell|combo) +step ' "$L" 2>/dev/null | sort -u | tail -4
echo '════ 对照（exp2 档，已跑）════'
grep -E '  t5AB_A +step |  t5AD_700 +step ' "$L" 2>/dev/null | sort -u | tail -2
echo '════ 若仍无 ⇒ 两臂是否还活着 ════'
ps -eo pid,etime,args --no-headers | grep '[_]bk_exp.py' | grep -c t5AM
