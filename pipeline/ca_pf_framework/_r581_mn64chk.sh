#!/bin/bash
# _r581_mn64chk.sh --- 查 N=64 `m` 判决的进度（**避免嵌套引号**，一律用脚本文件）
cd "$(dirname "$0")" || exit 1
echo "NOW      = $(date '+%F %T')"
for t in A B; do
  f="_w2_r581_mn64_${t}.log"
  if [ -f "$f" ]; then
    st=$(grep -o '\[ *[0-9]*\]' "$f" | tail -1 | tr -d '[] ')
    echo "臂 $t：存在  末step=${st:-?}  mtime=$(date -r "$f" '+%T')  大小=$(stat -c %s "$f")"
  else
    echo "臂 $t：**还没起**（脚本是顺序跑的：等 A 完再起 B）"
  fi
done
echo
echo "── mn64 目录 ──"
ls -la _exp/_bk_mn64/ 2>/dev/null | sed 's/^/  /'
echo
echo "── 快照 ──"
for t in A B; do
  d="_exp/_bk_mn64/dry_$t"
  [ -d "$d" ] && { echo "  $t: $(ls "$d" | grep -c '^snap_') 个快照"; ls "$d" | grep '^snap_' | tr '\n' ' '; echo; }
done
echo
echo "── 在跑的相关进程 ──"
ps -eo pid,rss,args --no-headers 2>/dev/null | grep -E '_bk_exp\.py|_bk_mn64' | grep -v grep \
  | awk '{printf "  pid=%-7s RSS=%.2f GB  %s\n", $1, $2/1048576, substr($0, index($0,$3), 90)}'
echo
echo "── 内存 / 负载 ──"
free -m | sed -n 2p | sed 's/^/  /'
awk '{printf "  loadavg %s %s %s\n", $1, $2, $3}' /proc/loadavg
