#!/bin/bash
# _t5_mon_restart.sh --- 重启监控（纳入 t5V2/t5H3），**无管道**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ar_monitor.log

echo "[$(date '+%F %T')] ════ 重启监控：纳入 t5V2（还在跑的长臂）与 t5H3（参照）════" >> "$LOG"

# ① 停掉旧监控（**只按精确 pid**，不用 pkill -f）
for P in $(pgrep -f '_t5_armon.py' 2>/dev/null); do
  [ "$P" = "$$" ] && continue
  kill -TERM "$P" 2>/dev/null && echo "  已停旧监控 pid=$P"
done
sleep 3

# ② 语法检查
$PY -m py_compile _t5_armon.py && echo "[$(date '+%F %T')]   语法 OK" >> "$LOG"

# ③ **无管道**重启（§197 的教训：管道接 head 会 SIGPIPE 静默杀死写端）
nohup taskset -c 16-19 $PY _t5_armon.py 80 300 >> "$LOG" 2>&1 &
NP=$!
echo "[$(date '+%F %T')]   新监控 pid=$NP（80 轮 × 300 s ≈ 6.7 小时）" >> "$LOG"
sleep 20
echo
echo '── 确认新监控存活 ──'
if kill -0 "$NP" 2>/dev/null; then echo "  ✅ pid=$NP 存活"; else echo "  ⚠ pid=$NP 已退出"; fi
echo
echo '── 最新一轮（去重）──'
tail -24 "$LOG" | awk '!seen[$0]++' | tail -10 | sed 's/^/  /'
