#!/bin/bash
# _t5_keeper_all.sh --- ★★★★★ 守护**三个**监控（补全：原守护只管 `_t5_armon`）
#
# ## 为什么需要
# `_t5_mon_keeper.sh` 只检查 `_t5_armon.py`（几何量）⇒
# **块监控 `_t5_blkmon.py` 与里程碑监视器 `_t5_milewatch.py` 死了没人管**。
# 而本算例要跑 ~12 小时 ⇒ **必须三个都被守护**。
#
# ## 做法
# 每 600 s 检查一次；**哪个不在就 setsid 续起哪个**（参数与最初一致）；
# 全部输出**追加**到各自日志（**不删**）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
KEEP=_w2_t5_keeper_all.log
echo "[$(date '+%F %T')] 三监控守护启动（每 600 s；缺谁补谁）" >> "$KEEP"

n_of() { ps -eo args --no-headers 2>/dev/null | awk -v p="$1" 'index($0,p){n++} END{print n+0}'; }

for i in $(seq 1 400); do          # 400 × 600 s ≈ 66 h
  # ① 几何监控
  if [ "$(n_of '_t5_armon.py')" -eq 0 ]; then
    echo "[$(date '+%F %T')] ⚠ _t5_armon 不在 ⇒ 续起" >> "$KEEP"
    setsid $PY _t5_armon.py 80 300 < /dev/null >> _w2_t5_ar_monitor.log 2>&1 &
    sleep 10
  fi
  # ② 块监控
  if [ "$(n_of '_t5_blkmon.py')" -eq 0 ]; then
    echo "[$(date '+%F %T')] ⚠ _t5_blkmon 不在 ⇒ 续起" >> "$KEEP"
    setsid $PY _t5_blkmon.py 200 300 < /dev/null >> _w2_t5_n276_monitor.log 2>&1 &
    sleep 10
  fi
  # ③ 里程碑监视器
  if [ "$(n_of '_t5_milewatch.py')" -eq 0 ]; then
    echo "[$(date '+%F %T')] ⚠ _t5_milewatch 不在 ⇒ 续起" >> "$KEEP"
    setsid $PY _t5_milewatch.py 120 400 < /dev/null >> _w2_t5_n276_milestones.log 2>&1 &
    sleep 10
  fi
  sleep 600
done
echo "[$(date '+%F %T')] 守护结束（400 轮）" >> "$KEEP"
