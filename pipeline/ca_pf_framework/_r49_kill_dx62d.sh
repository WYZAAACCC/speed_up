#!/bin/bash
# R49: 杀 mb1s62（起在 F1/F3 拆分之前）⇒ 重跑。
#   ⚠ 这次只匹配**唯一标识** `--tag mb1s62`，不再匹配公共参数 `dx-nm 62.5`
#     （上次就是那样把回归作业一起杀了，见 R30_AUDIT_LEDGER §24 教训 #2）。
set -u
K=0
for P in $(pgrep -f -- '--tag mb1s62' 2>/dev/null); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P : $(echo "$CMD" | cut -c1-70)"; kill -9 "$P"; K=1 ;;
    *) echo "skip $P (非 _bk_exp)" ;;
  esac
done
[ "$K" = 0 ] && echo "（没有找到 --tag mb1s62 的进程）"
sleep 2
echo "--- 残留（应剩 cln11 / mb1L / mb1Ls 三条）"
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-72
