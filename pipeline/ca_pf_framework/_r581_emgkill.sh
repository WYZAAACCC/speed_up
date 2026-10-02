#!/bin/bash
# _r581_emgkill.sh --- 🚨 内存急救：停掉吃 16.9 GB 的 TUNED 臂 + 清掉重复看门狗
# ★ 只 kill 进程；**数据一个字节不删**（goal 硬禁令）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ 停之前 ════'
free -m | sed -n 2,3p | sed 's/^/  /'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  tag=%-9s pid=%-7s RSS=%sMB\n' "${tag:-?}" "$p" "$rss"
done
echo
echo '════ ① 停 A/B 编排器（否则它会接着起 ARENA/PLAIN）════'
for p in $(pgrep -f '_r581_alloc160.sh' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM 编排器 pid=$p"
done
sleep 2
for p in $(pgrep -f '_r581_alloc160.sh' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && echo "  KILL 编排器 pid=$p"
done
echo
echo '════ ② 停 TUNED 臂（16.9 GB 的那个）════'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM 臂 pid=$p"
done
sleep 6
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && echo "  KILL 臂 pid=$p"
done
echo
echo '════ ③ 清掉**重复的**看门狗（只留一个，且要重配 PROTECT）════'
n=0
for p in $(pgrep -f '_r581_memguard.sh' 2>/dev/null); do
  n=$((n + 1))
  if [ "$n" -gt 1 ]; then
    kill -9 "$p" 2>/dev/null && echo "  KILL 多余看门狗 pid=$p"
  else
    echo "  留 pid=$p"
  fi
done
sleep 3
echo
echo '════ 停之后 ════'
free -m | sed -n 2,3p | sed 's/^/  /'
echo
echo '════ 数据还在吗（**不许删**）════'
for d in _exp/_bk_alloc160/dry_TUNED _exp/_bk_blk/dry_BK6 _exp/_bk_blk/dry_BK7; do
  [ -d "$d" ] || { echo "  $d（不存在）"; continue; }
  printf '  %-34s 行数=%-5s step=%-6s\n' "$d" \
    "$(wc -l < "$d/series.csv" 2>/dev/null)" \
    "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)"
done
echo
echo '════ TUNED 的 time -v 峰值（若已落盘）════'
grep -o 'Maximum resident set size (kbytes): [0-9]*' _w2_r581_alloc160_TUNED.time 2>/dev/null | sed 's/^/  /' || echo '  （还没写）'
