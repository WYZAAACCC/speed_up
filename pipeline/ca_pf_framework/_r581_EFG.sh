#!/bin/bash
# _r581_EFG.sh --- 看 N=64 上**同时在跑**的 E/F/G（三条都与 C5 直接相关）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
free -m | sed 's/^/  /'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
echo
echo '── N=64 各臂：step / CSV mtime / 行数 / 末行关键列 ──'
for t in A B C D E F G H; do
  f="_exp/_bk_mn64/dry_${t}/series.csv"
  if [ -f "$f" ]; then
    step=$(tail -1 "$f" | cut -d, -f1)
    printf '  %-4s step=%-6s mtime=%s 行数=%-4s\n' \
      "$t" "$step" "$(date -r "$f" '+%T')" "$(wc -l < "$f")"
  else
    printf '  %-4s （无 series.csv）\n' "$t"
  fi
done
echo
echo '── 各臂的 worker RSS + tag ──'
for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
  cmd=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
  tag=$(echo "$cmd" | grep -oE "\-\-tag [A-Za-z0-9_]+" | head -1 | awk '{print $2}')
  out=$(echo "$cmd" | grep -oE "\-\-out [^ ]+" | head -1 | awk '{print $2}')
  r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  # 关键参数
  bt=$(echo "$cmd" | grep -oE "\-\-nuc-block-target [0-9]+" | awk '{print $2}')
  vr=$(echo "$cmd" | grep -oE "\-\-var-rule [a-z]+" | awk '{print $2}')
  ml=$(echo "$cmd" | grep -oE "\-\-laths [0-9,]+" | awk -F, '{print NF}')
  printf '  pid=%-7s tag=%-10s RSS=%5d MB  B=%-4s var_rule=%-7s nv=%s\n' \
    "$p" "${tag:-?}" "$((r/1024))" "${bt:-默认5}" "${vr:-默认ed}" "${ml:-?}"
done
echo
echo '── E/F/G 的日志尾（有无 Traceback）──'
for t in E F G H; do
  f=_w2_r581_mn64_${t}.log
  if [ -f "$f" ]; then
    printf '  --- %s（mtime %s，Traceback=%s）---\n' "$t" "$(date -r "$f" '+%T')" "$(grep -c '^Traceback' "$f")"
    tail -2 "$f" | cut -c1-88 | sed 's/^/    /'
  fi
done
