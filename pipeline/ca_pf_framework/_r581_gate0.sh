#!/bin/bash
# _r581_gate0.sh --- 起**门 0/门 4**：归档路径逐位回归（P42 防护：setsid nohup + 防重复）
cd "$(dirname "$0")" || exit 1
if pgrep -f '_r30_regress.sh' >/dev/null 2>&1; then
  echo '  ⚠ 已在跑 ⇒ 不重复起'
else
  setsid nohup bash _r30_regress.sh > _w2_r581_gate0_outer.log 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo '  已起（setsid nohup）'
fi
sleep 40
echo
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '_r30_regress|dry_r30reg' | grep -v grep | cut -c1-96 | sed 's/^/  /'
echo
echo '── 日志尾 ──'
tail -8 _w2_r30_regress.log 2>/dev/null | sed 's/^/  /' || echo '  （还没有）'
echo
free -m | sed -n 2p | sed 's/^/  /'
