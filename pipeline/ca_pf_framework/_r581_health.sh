#!/bin/bash
# _r581_health.sh --- E/F/G 的健康（P29：日志 mtime + 大小 + Traceback + 进程状态，四样一起看）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 三条臂的日志（mtime 在动 = 活着）──'
for T in E F G; do
  f="_w2_r581_mn64_${T}.log"
  if [ -f "$f" ]; then
    printf '  %-3s log mtime=%-9s 大小=%-9s Traceback=%s\n' \
      "$T" "$(date -r "$f" '+%T')" "$(stat -c%s "$f")" "$(grep -c '^Traceback' "$f")"
  else
    printf '  %-3s （无日志）\n' "$T"
  fi
done
echo
echo '── CSV ──'
for T in E F G; do
  f="_exp/_bk_mn64/dry_${T}/series.csv"
  [ -f "$f" ] && printf '  %-3s step=%-6s mtime=%s\n' \
    "$T" "$(tail -1 "$f" | cut -d, -f1)" "$(date -r "$f" '+%T')"
done
echo
echo '── worker 进程（状态 + RSS + 核）──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  cmd=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(echo "$cmd" | grep -oE '\-\-tag [A-Za-z0-9_]+' | head -1 | awk '{print $2}')
  r=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  th=$(awk '/^Threads/{print $2}' "/proc/$p/status" 2>/dev/null)
  cp=$(taskset -pc "$p" 2>/dev/null | sed 's/.*: //')
  printf '  pid=%-7s tag=%-10s RSS=%5d MB state=%s 线程=%-3s 核=%s\n' \
    "$p" "${tag:-?}" "$((r/1024))" "$st" "$th" "${cp:-?}"
done
echo
echo '── E/F/G 日志末行（看进度）──'
for T in E F G; do
  f="_w2_r581_mn64_${T}.log"
  [ -f "$f" ] && printf '  %-3s %s\n' "$T" "$(tail -1 "$f" | cut -c1-88)"
done
