#!/bin/bash
# _r167_st.sh —— 当前作业状态（R165 两条 + 回归）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "现在：$(date '+%F %T')"
echo "_bk_exp 进程数：$(pgrep -f '_bk_exp[.]py' 2>/dev/null | wc -l)"
free -g | sed -n '2p'
echo
echo "--- R165 F2 配对对照 ---"
for t in saSet2F2 saOddGF2; do
  printf -- '  %-10s %s\n' "$t" "$(grep 's/步' _w2_r165_${t}.log 2>/dev/null | tail -1 | cut -c1-95)"
done
cat _w2_r165_run.log 2>/dev/null | tail -4
echo
echo "--- 回归（R164 的 windowB_lath 改动）---"
tail -6 _w2_r30_regress.log 2>/dev/null
