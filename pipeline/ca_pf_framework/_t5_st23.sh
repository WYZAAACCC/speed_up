#!/bin/bash
# _t5_st23.sh --- 第 23 轮状态（全部走脚本，避开引号问题）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
echo '── 形核计数 ──'
printf '  修复臂 t5G3：公告=%s  被拒=%s\n' \
  "$(grep -c 'athermal 形核' _w2_t5_short_t5G3.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5G3.log 2>/dev/null)"
printf '  旧臂 t5L62 ：公告=%s  被拒=%s\n' \
  "$(grep -c 'athermal 形核' _w2_t5_short_t5L62.log 2>/dev/null)" \
  "$(grep -c '被引擎拒' _w2_t5_short_t5L62.log 2>/dev/null)"
echo
echo '── series 读数 ──'
$PY _t5_series.py t5G3 2>&1 | head -22
echo
echo '── 日志末尾 ──'
grep -oE '\[ *[0-9]+\] Vt=[0-9.]+' _w2_t5_short_t5G3.log 2>/dev/null | tail -3 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
