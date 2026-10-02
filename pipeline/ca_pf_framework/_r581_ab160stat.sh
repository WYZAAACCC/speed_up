#!/bin/bash
# _r581_ab160stat.sh --- A4 的 N=160 A/B：现场速查
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 编排器与臂 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_alloc160' | grep -v grep | cut -c1-100 | sed 's/^/  /'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '  tag=%-9s pid=%-7s RSS=%-7s 时长=%s\n' "${tag:-?}" "$p" "${rss:-?}" "$et"
done
echo
echo '── A/B 日志尾 ──'
tail -10 _w2_r581_alloc160.log 2>/dev/null | sed 's/^/  /' || echo '  （还没有日志）'
echo
echo '── 三臂的产物 ──'
for t in TUNED ARENA PLAIN; do
  d="_exp/_bk_alloc160/dry_$t"
  if [ -d "$d" ]; then
    printf '  %-6s series 行数=%-5s step=%-6s 峰值(从 time -v)=%s\n' "$t" \
      "$(wc -l < "$d/series.csv" 2>/dev/null)" \
      "$(tail -1 "$d/series.csv" 2>/dev/null | cut -d, -f1)" \
      "$(grep -o 'Maximum resident set size (kbytes): [0-9]*' "_w2_r581_alloc160_${t}.time" 2>/dev/null | grep -o '[0-9]*' | awk '{printf "%.0f MB", $1/1024}')"
  else
    printf '  %-6s （还没起）\n' "$t"
  fi
done
echo
free -m | sed -n 2p | sed 's/^/  /'
