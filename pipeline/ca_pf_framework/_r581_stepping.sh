#!/bin/bash
# _r581_stepping.sh --- 两臂是否**开始步进**了（构造完成的直接判据，P33 的验证）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
free -m | sed 's/^/  /'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
echo
echo '── 每条臂：step / CSV mtime / 行数（row>1 ⇒ 已开始步进）──'
for t in p2_m12 p2_m12b p2_m20 p2_b5 p2_b5ov; do
  f="_exp/_bk_p2/dry_${t}/series.csv"
  if [ -f "$f" ]; then
    printf '  %-9s step=%-6s mtime=%s 行数=%s\n' \
      "$t" "$(tail -1 "$f" | cut -d, -f1)" "$(date -r "$f" '+%T')" "$(wc -l < "$f")"
  else
    printf '  %-9s （无 series.csv）\n' "$t"
  fi
done
echo
echo '── 臂 D（N=64）──'
f=_exp/_bk_mn64/dry_D/series.csv
[ -f "$f" ] && printf '  D         step=%-6s mtime=%s 行数=%s\n' \
  "$(tail -1 "$f" | cut -d, -f1)" "$(date -r "$f" '+%T')" "$(wc -l < "$f")"
echo
echo '── worker RSS ──'
for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
  cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  tag=$(echo "$cmd" | grep -oE "\-\-tag [A-Za-z0-9_]+" | head -1 | awk '{print $2}')
  r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  printf '  pid=%-7s tag=%-10s RSS=%5d MB\n' "$p" "${tag:-?}" "$((r/1024))"
done
echo
echo '── 两臂日志尾（有无 Traceback / 进度）──'
for t in p2_m12 p2_m12b; do
  f=_w2_r581_p2_${t}.log
  echo "  --- $t（mtime $(date -r "$f" '+%T' 2>/dev/null)）---"
  tail -2 "$f" 2>/dev/null | cut -c1-90 | sed 's/^/    /'
  printf '    Traceback 行数 = %s\n' "$(grep -c '^Traceback' "$f" 2>/dev/null)"
done
