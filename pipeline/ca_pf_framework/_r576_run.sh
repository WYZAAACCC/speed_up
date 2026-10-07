#!/bin/bash
# _r576_run.sh --- R576 两件事：① 新量具的交错配对 A/B（BEFORE / AFTER）
#                          ② **记账钩子自身的代价**（HOOKED vs STRIPPED 源码剥离）
# 先归档旧日志（绝不删除）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _w2_r572_acct_BEFORE_24x64_w4.log _w2_r572_acct_AFTER_24x64_w4.log \
         _w2_r30_regress.log _w2_r30_regress_stdout.log; do
  [ -f "$f" ] && cp -f "$f" "$f.r575arch"
done
echo "############ PART 1：新量具 A/B  $(date '+%F %T')"
bash _r576_prof_ab.sh > _w2_r576_profab_run.log 2>&1
echo "  rc=$?"
tail -30 _w2_r576_profab_run.log
echo ""
echo "############ PART 2：钩子代价 A/B  $(date '+%F %T')"
bash _r576_acct_cost.sh > _w2_r576_acctcost_run.log 2>&1
echo "  rc=$?"
cat _w2_r576_acctcost_run.log
echo "=== R576 RUN DONE $(date '+%F %T') ==="
