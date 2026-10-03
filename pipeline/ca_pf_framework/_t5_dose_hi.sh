#!/bin/bash
# _t5_dose_hi.sh --- ★★★★★ 剂量-响应再加一点：`--eng-elong 10`（判据 2 未触发 ⇒ 预登记允许往上试）
#
# ## 依据（**预先写死的判据**，§220）
# 判据 2：「若 **7 与 5 的差 < 5%** ⇒ 核的拉长已饱和」。
# **实测（§222）：7 相对 5 是 4.78 → 6.66 = **+39%**** ⇒ **远未饱和** ⇒ **判据允许往上试** ✓
#
# ## 设计
# **单臂**（`t5AD_1000`，`--eng-elong 10.00`），**参数与 `t5AD_500/700` 逐项一致** ⇒ 唯一变量 = 剂量。
# **内存账**：现有用 12.9 GB / 余 11.1 GB；本臂 ~2.5 GB ⇒ 加后余 ~8.6 GB ⇒ **安全** ✓
#
# ## 判据（**预先写死**）
# 1. **长宽比是否继续升**（10 > 7？）；
# 2. **若 10 与 7 的差 < 5%** ⇒ **饱和点找到了**（在 7–10 之间）；
# 3. **⚠ 副作用闸**：若报错（如 `elong*R > margin` 越界，§212 提过这条硬检查） ⇒ **该档不可用**；
# 4. **⚠ 一致性闸**：本臂在 step 0 应仍给出 **1.86**（种子不受 `eng-elong` 影响，§222.2）
#    ⇒ **若不符，说明参数没生效**（先验）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ab_dose.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════ 剂量-响应加点：t5AD_1000（--eng-elong 10.00）════'
say '  依据：判据 2 未触发（7 相对 5 是 +39%，远未饱和）⇒ 预登记允许往上试'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

$PY _t5_short.py --tag t5AD_1000 --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 --eng-elong 10.00 \
    > _w2_t5_ad_t5AD_1000.log 2>&1 &
PID=$!
say "  起 t5AD_1000：eng-elong=10.00  pid=$PID"
sleep 45
if kill -0 "$PID" 2>/dev/null; then say "  ✅ 45 s 后存活"; else
  say "  ❌ 45 s 内退出 ⇒ **该档不可用**（记账）"; tail -5 _w2_t5_ad_t5AD_1000.log >> "$LOG"
fi
free -m | sed -n 2p | awk '{printf "  起后 45 s 内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '  ── 等本臂结束 ──'
wait "$PID" 2>/dev/null
say '════ t5AD_1000 结束 ════'
say '=== DOSE_HI DONE ==='
