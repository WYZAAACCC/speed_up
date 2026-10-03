#!/bin/bash
# _t5_v2.sh --- ★★★★★ 起 V2 臂（多变体/多块路径）并与长跑并行
#
# ## 为什么要起它（§119 的洞察 + §121 的决策）
# `t5H3` 的 `nslab_n` 封顶于 `m = 24`（逐字消息"无可用空场/落位失败"）⇒
# **判据 ③(多块)/④/⑥ 在本配置下不可能达成**。而要让"新块"出现，**两个条件必须同时满足**：
#   ① **每组场数 `m` 有余量**（`t5H3` 是 24，已用尽）；
#   ② **`fresh` 能选到**不同变体**（`--var-rule ed` 永远 `argmax(drv)` ⇒ 总选同一变体）。
# ⇒ 本臂：`--nvar 2 --m 36`（`nv = 72` **内存不变**）+ `--var-rule random` + `--nuc-fresh-every 5`。
#
# ## 判据（**预先写死**，§121.4）
#   `n_var_sig > 1`（随机选变体生效）
#   `nblk_sig >= 2`（**真的出现新块**）
#   `nf2 > 0`（块相遇）
#   若三者仍不变 ⇒ `fresh` 被拒**另有原因** ⇒ 回到 `nuc_dbg.json` 归因。
#
# ## ⚠ 三项偏离记账（**必须**）
#   1. `--var-rule random` 是**显式的物理选择**（代码注明 `ed` 默认逐位不变）；
#   2. `--nuc-fresh-every 5` 与 abA 的 `K = n(T_end) = 23` **不同** ⇒ **块数不可与 abA 直接比**；
#   3. **本臂不保证成功** —— 它只是**同时解除了两个已识别的障碍**。
#   ⚠ 两项都带"默认档不传"的守卫 ⇒ **`t5H3` 与归档路径逐字不受影响**（s122 已验证）。
#
# ## 内存（P23）
#   `t5H3` ~6 GB + 本臂 ~12 GB = **18 GB < 22 GB** ✓
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_v2.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ 起臂前检查 ════'
free -m | sed -n 2p | sed 's/^/  /'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  在场: pid=%s 已跑=%s\n", $1, $2}'
say '  ★ 本臂参数：--N 160 --nvar 2 --m 36 --B 3 --var-rule random --nuc-fresh-every 5'
say '  ★ 核 8-15（长跑用 0-7）  内存上限 12 GB  目标 6000 步'

$PY _t5_short.py --tag t5V2 \
   --N 160 --nvar 2 --m 36 --B 3 --steps 6000 --cores 8-15 --mem-limit-gb 12.0 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --var-rule random --nuc-fresh-every 5 \
   --archive-old > _w2_t5_v2_A.log 2>&1 &
NP=$!
say "  ★ pid=$NP（tag=t5V2）—— 本脚本会**一直等它**（不提前退出）"
sleep 240
say '  ── 240 s 后：引擎横幅里的关键行 ──'
grep -E 'var-rule|fresh-every|N8 自动推导|导出板条数|总根数|必须至少|nv=' \
  _w2_t5_short_t5V2.log 2>/dev/null | head -8 | cut -c1-134 | sed 's/^/    /'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  在场: pid=%s 已跑=%s\n", $1, $2}'
free -m | sed -n 2p | sed 's/^/    /'
say '=== V2 LAUNCHED ==='
wait $NP
say "  V2 结束：exit=$?"
