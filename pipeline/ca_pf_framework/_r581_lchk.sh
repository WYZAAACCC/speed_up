#!/bin/bash
# _r581_lchk.sh --- 臂 L 起来了吗 + 现在谁在跑 + 内存
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 臂 L 的日志（末 5 行）──'
tail -5 _w2_r581_mn64L.log 2>/dev/null || echo '  （无）'
echo
echo '── 臂 L 的产物目录 ──'
if [ -d _exp/_bk_mn64/dry_L ]; then
  ls _exp/_bk_mn64/dry_L/ | tr '\n' ' '
  echo
  tail -1 _exp/_bk_mn64/dry_L/series.csv 2>/dev/null | cut -d, -f1 | sed 's/^/  step=/'
else
  echo '  （dry_L 还没建）'
fi
echo
echo '── 内存 ──'
awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} /SwapTotal/{st=$2} /SwapFree/{sf=$2} END{
  printf "  available=%.0f MB   swap_used=%.0f / %.0f MB\n", a/1024, (st-sf)/1024, st/1024
}' /proc/meminfo
echo
echo '── 在跑的 _bk_exp 进程 ──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  st=$(awk '/^State/{print $2}' "/proc/$p/status" 2>/dev/null)
  rss=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
  printf '  pid=%-7s tag=%-10s state=%-3s RSS=%s MB\n' "$p" "${tag:-?}" "$st" "$rss"
done
echo
echo '── G 的进度 ──'
tail -1 _exp/_bk_mn64/dry_G/series.csv 2>/dev/null | cut -d, -f1,9,10,19,24 | sed 's/^/  step,nslab_n,nf3_col,nf3,nf2 = /'
