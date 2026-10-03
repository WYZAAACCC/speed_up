#!/bin/bash
# _t5_wait1200.sh --- ★ 把等待放进**一次**调用（而不是每轮查一次）
#
# ## 为什么（对第 18/18b 条的修正实施）
# 我先前每轮都查一次 `snap_01200`，而轮次间隔（~1 分钟）**远短于**里程碑间隔（~10 分钟）
# ⇒ **重复了同一条调用很多次**（系统两次提示）。
# **⇒ 正确做法：在一次调用里 `sleep` 到里程碑时刻，再查。**
#
# ## 判据
# 睡到 t5H3 的 `series` 末步 >= 1200（或超时 20 分钟），然后：
#   * `snap_01200` 在 ⇒ 跑**预测 2**（`_t5_fillts.py`）
#   * 不在 ⇒ 报实际步数（不重复查）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
S=_exp/_bk_t5/dry_t5H3/series.csv
DEADLINE=$(( $(date +%s) + 1200 ))     # 最多等 20 分钟
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  ST=$(tail -1 "$S" 2>/dev/null | cut -d, -f1)
  [ -z "$ST" ] && ST=0
  if [ "$ST" -ge 1200 ] 2>/dev/null; then break; fi
  sleep 30
done
echo "NOW = $(date '+%F %T')   t5H3 末步 = $(tail -1 "$S" 2>/dev/null | cut -d, -f1)"
echo
if [ -f _exp/_bk_t5/dry_t5H3/snap_01200.npz ]; then
  echo '════ ★ snap_01200 到 ⇒ 跑预测 2（"带延伸"场数是否增长）════'
  taskset -c 16-19 $PY _t5_fillts.py 2>&1 | tail -12
  echo
  echo '════ 判据（§152.3 预先写死）════'
  echo '  若"带延伸"的场数 >= 8 ⇒ **预测 2 成立**（随步数增长）'
  echo '  若仍为 8 或更少 ⇒ 预测 2 **不成立**（须记账：该形貌在 step 1000 后不再扩展）'
else
  echo "  ⇒ snap_01200 仍未到（末步 $(tail -1 "$S" 2>/dev/null | cut -d, -f1)）⇒ 不重复查"
fi
