#!/bin/bash
# _r581_arms.sh --- 现在有几条臂、各自投入多久（用于**按价值**决定停哪条）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 各 _bk_exp 进程：tag / 启动时刻 / 已跑时长 / RSS / state ──'
printf '  %-7s %-9s %-9s %-9s %-5s %s\n' 'pid' 'tag' '启动' '时长' 'RSS' 'state'
echo '  --------------------------------------------------------------------'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  # 启动时刻：用 /proc/<pid>/stat 的 starttime（jiffies since boot）+ btime
  st=$(awk '{print $22}' "/proc/$p/stat" 2>/dev/null)
  btime=$(awk '/btime/{print $2}' /proc/stat)
  hz=100
  start=$(( btime + st / hz ))
  dur=$(( $(date +%s) - start ))
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  s=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  printf '  %-7s %-9s %-9s %-9s %-5s %s\n' "$p" "${tag:-?}" \
    "$(date -d "@$start" '+%H:%M:%S')" "$((dur/60))min" "$rss" "$s"
done
echo
echo '── 队列脚本还在跑吗（谁在起臂）──'
ps -eo pid,args --no-headers 2>/dev/null | grep -E '_r581_mn64[a-zA-Z]*\.sh|_r581_memguard|_r581_softguard' | grep -v grep | cut -c1-84
echo
echo '── 内存 ──'
awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} /SwapTotal/{st=$2} /SwapFree/{sf=$2} END{
  printf "  available=%.0f MB   swap_used=%.0f / %.0f MB\n", a/1024, (st-sf)/1024, st/1024
}' /proc/meminfo
