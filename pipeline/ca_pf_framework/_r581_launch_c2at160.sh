#!/bin/bash
# _r581_launch_c2at160.sh --- 起"10 µm 尺度 C2 测量"（P42：setsid nohup + 防重复）
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_c2at160.log
if pgrep -f '_r581_c2at160.py' >/dev/null 2>&1; then
  echo '  ⚠ 已在跑 ⇒ 不重复起'
else
  setsid nohup taskset -c 0-7 /root/miniconda3/envs/ml/bin/python -u _r581_c2at160.py \
    > "$LOG" 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo '  已起（setsid nohup taskset 0-7）'
fi
sleep 60
echo
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_r581_c2at160' | grep -v grep | cut -c1-96 | sed 's/^/  /'
echo
echo '── 日志 ──'
tail -14 "$LOG" 2>/dev/null | sed 's/^/  /' || echo '  （还没有）'
echo
free -m | sed -n 2p | sed 's/^/  /'
