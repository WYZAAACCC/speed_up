#!/bin/bash
# _r581_pokeD.sh --- 看臂 D 到底跑到第几步（**读 CSV，不猜**；P30：CSV 是 step 的权威）
cd "$(dirname "$0")" || exit 1
F=_exp/_bk_mn64/dry_D/series.csv
echo "NOW = $(date '+%F %T')"
echo "文件 mtime = $(date -r "$F" '+%F %T' 2>/dev/null)"
echo "行数 = $(wc -l < "$F" 2>/dev/null)"
echo
echo '── 表头（前 12 列）──'
head -1 "$F" 2>/dev/null | tr ',' '\n' | head -12 | cat -n
echo
echo '── 末行（前 100 字符）──'
tail -1 "$F" 2>/dev/null | cut -c1-100
echo
echo '── 末行的 step 列（第 1 列）──'
tail -1 "$F" 2>/dev/null | cut -d, -f1
echo
echo '── 目录内容 ──'
ls -la _exp/_bk_mn64/dry_D/ 2>/dev/null
echo
echo '── D 的 worker 进程 ──'
for p in $(pgrep -f "_bk_exp.py" 2>/dev/null); do
  t=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -o "tag [A-Z]" | head -1)
  r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null)
  case "$t" in *D*) echo "  pid=$p $t RSS=$((r/1024)) MB";; esac
done
echo
echo '── 臂 D 的日志（若有）──'
tail -5 _w2_r581_mn64_D.log 2>/dev/null | cut -c1-100 || echo "  （无日志文件）"
