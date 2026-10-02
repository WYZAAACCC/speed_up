#!/bin/bash
# _r581_memchk.sh --- 内存/看门狗现状（一条命令看全，避免嵌套引号问题）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 看门狗在跑吗 ──'
ps -eo pid,args --no-headers 2>/dev/null | grep -E 'memguard|softguard' | grep -v grep | cut -c1-86
echo
echo '── 看门狗日志尾（有过报警就说明触发过）──'
tail -5 _w2_r581_memguard.log 2>/dev/null || echo '  （无日志）'
echo
echo '── 内存 ──'
awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} /SwapTotal/{st=$2} /SwapFree/{sf=$2} END{
  printf "  total=%.0f MB  available=%.0f MB  swap_used=%.0f / %.0f MB\n",
         t/1024, a/1024, (st-sf)/1024, st/1024
}' /proc/meminfo
echo
echo '── 各 _bk_exp 进程（tag / state / RSS）──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  rss=$(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null)
  printf '  pid=%-7s tag=%-10s state=%-3s RSS=%s MB\n' "$p" "${tag:-?}" "$st" "$(( ${rss:-0} / 1024 ))"
done
echo
echo '── 臂 L（应被内存闸挡住）──'
tail -2 _w2_r581_mn64L.log 2>/dev/null || echo '  （无）'
