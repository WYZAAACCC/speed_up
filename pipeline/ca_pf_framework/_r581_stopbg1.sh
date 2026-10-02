#!/bin/bash
# _r581_stopbg1.sh --- 停掉**被我自己判为作废**的 `BG1`（R181：种子撑满盒子 ⇒ 问不出问题）
# ★ 只 kill 进程；**数据留在磁盘上**（绝不 rm -rf，见 goal 硬禁令）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 停之前 ──'
for p in $(pgrep -f '_bk_exp.py.*--tag BG1' 2>/dev/null); do
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  echo "  BG1 pid=$p RSS=${rss}MB"
done
for p in $(pgrep -f '_bk_exp.py.*--tag BG1' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM pid=$p"
done
sleep 5
for p in $(pgrep -f '_bk_exp.py.*--tag BG1' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && echo "  KILL pid=$p"
done
sleep 2
echo
echo '── 停之后的臂 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  tag=%-9s pid=%-7s RSS=%sMB\n' "${tag:-?}" "$p" "$rss"
done
echo
echo '── BG1 的数据**还在**吗（不许删）──'
ls _exp/_bk_blk/dry_BG1/ 2>/dev/null | tr '\n' ' '
echo
wc -l < _exp/_bk_blk/dry_BG1/series.csv 2>/dev/null | sed 's/^/  series.csv 行数=/'
echo
free -m | sed -n 2p | sed 's/^/  /'
