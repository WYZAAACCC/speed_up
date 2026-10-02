#!/bin/bash
# _r581_fchk.sh --- 臂 F 到底还活着吗（P29：日志 mtime + 大小 + Traceback + 进程状态 + 产物，五样一起看）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── F 的日志 ──'
f=_w2_r581_mn64_F.log
if [ -f "$f" ]; then
  printf '  mtime=%s  大小=%s  Traceback=%s\n' \
    "$(date -r "$f" '+%T')" "$(stat -c%s "$f")" "$(grep -c '^Traceback' "$f")"
  echo '  ── 末 5 行（去重后）──'
  tail -20 "$f" | sort -u | tail -5 | cut -c1-96 | sed 's/^/    /'
else
  echo "  （无）"
fi
echo
echo '── F 的 CSV ──'
c=_exp/_bk_mn64/dry_F/series.csv
[ -f "$c" ] && printf '  step=%s 行数=%s mtime=%s\n' \
  "$(tail -1 "$c" | cut -d, -f1)" "$(wc -l < "$c")" "$(date -r "$c" '+%T')"
echo
echo '── F 的进程（状态/wchan/线程/RSS/核/CPU 时间）──'
for p in $(pgrep -f 'tag F' 2>/dev/null); do
  printf '  pid=%s state=%s wchan=%s 线程=%s RSS=%sMB 核=%s\n' \
    "$p" "$(awk '/^State/{print $2}' /proc/$p/status 2>/dev/null)" \
    "$(cat /proc/$p/wchan 2>/dev/null)" \
    "$(awk '/^Threads/{print $2}' /proc/$p/status 2>/dev/null)" \
    "$(( $(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null) / 1024 ))" \
    "$(taskset -pc "$p" 2>/dev/null | sed 's/.*: //')"
  echo "  utime+stime = $(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null) jiffies"
done
echo
echo '── 对比：G 的日志（它在推进）──'
printf '  mtime=%s  大小=%s\n' "$(date -r _w2_r581_mn64_G.log '+%T')" "$(stat -c%s _w2_r581_mn64_G.log)"
echo
echo '── 系统负载 ──'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
free -m | sed -n 2p | sed 's/^/  /'
