#!/bin/bash
# _r581_postkill.sh --- ★★★★★ 看门狗误杀后的**清点与复盘**
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '########## ① 看门狗干了什么（逐字）##########'
grep -n '杀 pid=\|⚠⚠ available' _w2_r581_memguard.log 2>/dev/null | tail -8
echo
echo '########## ② 被杀的臂：**已落盘的数据还在吗** ##########'
for T in p2_m12 p2_m12b L; do
  d="_exp/_bk_mn64/dry_$T"
  [ -d "$d" ] || d="_exp/_bk_n160/dry_$T"
  [ -d "$d" ] || { echo "  $T: 目录没找到"; continue; }
  printf '  %-9s ' "$T"
  printf 'step=%-6s ' "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)"
  printf '快照=%-28s ' "$(ls "$d" 2>/dev/null | grep -c '^snap_')"
  printf 'series=%-9s ' "$(wc -l < "$d/series.csv" 2>/dev/null)"
  echo "字节=$(stat -c%s "$d/series.csv" 2>/dev/null)"
done
echo
echo '########## ③ 现在在跑什么（新起的臂是谁起的）##########'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | \
  sed -n 's/.*--tag \([^ ]*\).*/  tag=\1/p'
echo '  ── 队列脚本 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep -E '_r581_(mqueue|mn64|p2q)' | grep -v grep | cut -c1-80
echo
echo '########## ④ 新臂 p2_m20 的横幅（它在跑什么）##########'
f=$(ls -t _w2_r581_*p2_m20*.log 2>/dev/null | head -1)
[ -n "$f" ] && { echo "  日志：$f"; grep -E 'N=[0-9]+|m=[0-9]+|nv=|--steps|steps=' "$f" 2>/dev/null | head -4 | sed 's/^/    /'; } || echo '  （没找到 p2_m20 的日志）'
echo
echo '########## ⑤ 内存 ##########'
free -m | sed -n 2,3p
