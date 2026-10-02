#!/bin/bash
# _r581_launch160b.sh --- 起"安全版"A/B（P42：setsid nohup + disown；防重复起）
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_alloc160b.log
if pgrep -f '_r581_alloc160b.sh' >/dev/null 2>&1; then
  echo "  ⚠ 已有 _r581_alloc160b.sh 在跑 ⇒ 不重复起"
else
  setsid nohup bash _r581_alloc160b.sh > _w2_r581_alloc160b_outer.log 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo "  已起（setsid nohup）"
fi
sleep 30
echo
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r581_alloc160b|dry_alloc' | grep -v grep | cut -c1-100 | sed 's/^/  /'
echo
echo '── 日志 ──'
tail -6 "$LOG" 2>/dev/null | sed 's/^/  /' || echo '  （还没有）'
echo
free -m | sed -n 2p | sed 's/^/  /'
