#!/bin/bash
# _r581_memchk2.sh --- 内存安全速查（P40/P41：先看内存，再看别的）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 内存 ──'
free -m | sed -n 2,3p | sed 's/^/  /'
echo
echo '── 各臂 RSS ──'
total=0
n=0
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  r=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  [ -z "${r:-}" ] && r=0
  total=$((total + r))
  n=$((n + 1))
  printf '  tag=%-9s pid=%-7s RSS=%sMB\n' "${tag:-?}" "$p" "$r"
done
printf '  ⇒ **%d 条臂，合计 %d MB**\n' "$n" "$total"
echo
echo '── 看门狗 ──'
tail -4 _w2_r581_memguard.log 2>/dev/null | sed 's/^/  /'
echo
echo '── 在跑的看门狗进程 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep '_r581_memguard' | grep -v grep | cut -c1-96 | sed 's/^/  /'
