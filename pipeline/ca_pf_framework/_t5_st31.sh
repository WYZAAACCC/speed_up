#!/bin/bash
# _t5_st31.sh --- 第 31 轮：T_3 形核检查 + 进度
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 形核计数 ──'
printf '  修复臂 t5G3：公告=%s  被拒=%s\n' \
  "$(grep -c 'athermal 形核' _w2_t5_short_t5G3.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5G3.log 2>/dev/null)"
echo '  ── 形核事件（末 5 条，看有没有 T_3=801.1 K）──'
grep 'athermal 形核 @ step' _w2_t5_short_t5G3.log 2>/dev/null | tail -5 | cut -c1-104 | sed 's/^/    /'
echo
echo '── 进度（末 3）──'
grep -oE '\[ *[0-9]+\] Vt=[0-9.]+ .*nslab=[0-9]+' _w2_t5_short_t5G3.log 2>/dev/null \
  | tail -3 | cut -c1-72 | sed 's/^/  /'
echo
/root/miniconda3/envs/ml/bin/python _t5_series.py t5G3 2>&1 | sed -n '1,8p;14,18p'
echo
ps -eo etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{printf "  进程 已跑=%s\n", $1}'
free -m | sed -n 2p | sed 's/^/  /'
