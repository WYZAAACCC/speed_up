#!/bin/bash
# _t5_mon_keeper.sh --- ★★★ 监控守护：监控若结束/退出，**自动续起**（保证"持续"监控）
#
# ## 为什么需要
# `_t5_armon.py` 只跑固定轮数（80 轮 ≈ 6.7 h），而 `t5V2` 还要跑 10+ h
# ⇒ **监控会在长臂跑完前就停** ⇒ 与"持续监控"不符。
# **⇒ 本守护每 10 分钟检查一次；若监控进程不在（结束或崩溃），就**续起一轮新的****。
#
# ## 安全
# * **不删任何日志**（一直是 `>>` 追加）；
# * **不用 `pkill`/`pgrep -f`**（自匹配坑，§215）⇒ 用 `ps` + 方括号技巧；
# * 内存开销可忽略（一个 bash 循环）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ar_monitor.log
KEEP=_w2_t5_mon_keeper.log
echo "[$(date '+%F %T')] 监控守护启动（每 600 s 检查；监控不在则续起 80 轮）" >> "$KEEP"

for i in $(seq 1 400); do          # 400 × 600 s ≈ 66 h（足够长）
  ALIVE=$(ps -eo args --no-headers | grep -c '[p]ython _t5_armon.py')
  if [ "$ALIVE" -eq 0 ]; then
    echo "[$(date '+%F %T')] ⚠ 监控不在 ⇒ 续起" >> "$KEEP"
    echo "[$(date '+%F %T')] ⚠ 监控不在 ⇒ 续起 80 轮" >> "$LOG"
    setsid $PY _t5_armon.py 80 300 < /dev/null >> "$LOG" 2>&1 &
    sleep 15
    N=$(ps -eo args --no-headers | grep -c '[p]ython _t5_armon.py')
    echo "[$(date '+%F %T')]   续起后监控进程数 = $N" >> "$KEEP"
  fi
  sleep 600
done
echo "[$(date '+%F %T')] 守护结束（400 轮）" >> "$KEEP"
