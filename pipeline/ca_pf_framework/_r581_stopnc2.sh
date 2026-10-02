#!/bin/bash
# _r581_stopnc2.sh --- 停掉旧的无分辨力作业（只 kill 进程，**数据不删**）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo '── 停之前 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_negctl2|_bk_nc2' | grep -v grep | cut -c1-96 | sed 's/^/  /'
for p in $(pgrep -f '_r581_negctl2.sh' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM 编排器 $p"
done
for p in $(pgrep -f '_bk_nc2' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && echo "  TERM 算例 $p"
done
sleep 4
for p in $(pgrep -f '_r581_negctl2.sh\|_bk_nc2' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && echo "  KILL $p"
done
sleep 2
echo '── 停之后 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_negctl2|_bk_nc2' | grep -v grep | cut -c1-96 | sed 's/^/  /'
echo '  （空 = 已停）'
echo '── 数据还在吗（**不许删**）──'
ls -d _exp/_bk_nc2/* 2>/dev/null | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
