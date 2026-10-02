#!/bin/bash
# _r581_memtrend.sh --- 采 8 次（每 15 s）看内存**趋势** ⇒ 判"是瞬时尖峰还是持续恶化"
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')   阈值=1800 MB（看门狗）"
echo
printf '  %-9s %-12s %-14s %s\n' '时刻' 'available' 'swap_used' '进程（tag:RSS/state）'
echo '  ----------------------------------------------------------------------------'
for i in 1 2 3 4 5 6 7 8; do
  a=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  st=$(awk '/SwapTotal/{t=$2} /SwapFree/{f=$2} END{printf "%d", (t-f)/1024}' /proc/meminfo)
  ps_str=''
  for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
    c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
    rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
    s=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
    ps_str="$ps_str ${tag}:${rss}/${s}"
  done
  printf '  %-9s %-12s %-14s %s\n' "$(date '+%T')" "$a" "$st" "$ps_str"
  [ "$i" -lt 8 ] && sleep 15
done
echo
echo '  ★ 判读：'
echo '   · available **回升** ⇒ 瞬时尖峰 ⇒ 不必动手'
echo '   · available **持续降** ⇒ 看门狗会触发（它 kill -9 **全部** _bk_exp.py）'
echo '   · ★ 已完成的步都在 /mnt/f 上（series.csv/快照/meta）⇒ **不会不可逆丢失**'
