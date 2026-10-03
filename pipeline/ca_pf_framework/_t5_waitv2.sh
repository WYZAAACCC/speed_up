#!/bin/bash
# _t5_waitv2.sh --- ★ 第 23 条机制：等 `t5V2` 的**事件 #23**，到点**自动跑判决器**
#
# ## 为什么（第 23 条）
# `t5V2` 的事件 #23 = 首个 `fresh` 触发 ⇒ **判据⑥ 的判定点**。
# 现在形核 15 个 ⇒ 还需 8 个事件。**每轮查一次就是重复调用**（§183 的教训）
# ⇒ **把等待写进一次调用，到点自动判**。
#
# ## 判据（**预先写死在 `_t5_v2judge.sh` 里**，本脚本不改它，只负责"到点触发"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t5V2.log
DEADLINE=$(( $(date +%s) + 10800 ))      # 最多等 3 小时
echo "[$(date '+%F %T')] 开始等：t5V2 的形核事件数 >= 23（首个 fresh 触发）"
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  N=$(grep -c 'athermal 形核' "$L" 2>/dev/null); [ -z "$N" ] && N=0
  NF=$(grep -c '模式 \*\*fresh\*\*' "$L" 2>/dev/null); [ -z "$NF" ] && NF=0
  if [ "$N" -ge 23 ] || [ "$NF" -ge 1 ]; then
    echo "[$(date '+%F %T')] ★ 到点：事件 = $N，其中 fresh = $NF"
    break
  fi
  sleep 60
done
echo
echo "════ 到点后**自动跑判决器**（判据预先写死，本脚本不改它）════"
bash _t5_v2judge.sh 2>&1 | tail -22
echo
echo "════ 附：两臂健康 ════"
bash _t5_both.sh 2>&1 | sed -n '1,16p'
