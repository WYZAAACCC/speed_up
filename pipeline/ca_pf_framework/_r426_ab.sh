#!/bin/bash
# _r426_ab.sh —— ★★★ **A/B 受控双臂正式启动**（用户 2026-10-01 裁定：两条都跑，作受控对照）
#
# ## 目标（用户裁定）
#   **6 块 × 4 根 = 24 根板条**；A = 守 C-3（有序），B = 入 burst（C-3 违反，记账）。
#
# ## 实测预算（`_r425` 探针，25 场 / N=112 / 3 线程）
#   峰值 RSS = **2.03 GB/臂**（不是外推的 3.6 GB）；≈ **6 s/步**（保险取值）。
#
# ## 参数（`_r424_design.py` 解算，判据 D-1…D-4 全过）
#   α_KM = 24/(M_s − 298) = **0.041739 /K**（由**室温终温**反解，不是硬凑）
#   T_start = T_1 = **849.04 K**；冷却窗口 849 → 298 K（ΔT = 551 K）
#   q_cap(α, L=1000nm) = **2.9405e6 K/s**
#   步数与 q 的关系（框架自带闭式）：`N_steps(q) = steps_min_ordered·(q_cap/q)`
#     * **A 臂**：q = 0.8·q_cap = 2.3524e6 K/s（**守 C-3**，Δt_grow/Δt_nuc = 0.80）
#                ⇒ steps = 4737/0.8 = **5922**
#     * **B 臂**：q = q_cap·4737/800 = 1.7412e7 K/s（**burst**，比值 **5.92×**）
#                ⇒ steps = **800**
#   ⇒ **单变量**：两臂除 q 与 steps 外**逐字相同**。
#
# ## 记账（必须随任何结论一起报）
#   1. `α_KM` 由 0.011 重标到 **0.041739** —— 原值本就标 [标]、**无 Ti-64 实测值**
#      （`windowB_closure.limitations()` 第 2 条）；重标依据是"24 根 / 室温终温"。
#   2. B 臂**违反 C-3**（5.92×）。框架原话：违反"**不是数值错误**"，
#      而是模型进入 burst regime —— "真实马氏体确有 burst，但**本模型的逐片平衡形状
#      是在'长完'这个前提下才成立**的 ⇒ 必须记账"。
#   3. `--nuc-fresh-every 4` ⇒ **块数是规定的、不是涌现的**（`§189.3`），不得当物理结论。
#   4. 板条长 **1000 nm**（物理实测 ~8 µm）—— 受盒尺寸与 C-3 步数预算限制的折中。
#   5. 环境温度终点 298 K；`--T-end` 只影响 athermal 钟的终点计数。
#
# ## 判据（跑完核）
#   R-1 两臂都不带 Traceback；事件数 = 23（= n − 1）。
#   R-2 A 臂 `closure.json` 的 `q_source` 是 user 且 q = 2.3524e6；B 臂 q = 1.7412e7。
#   R-3 两臂末态 `blk_nprof` 里**同时**出现 >1 的值**和**多个块。
#   R-4 所有数据落 **F 盘** `_exp/_bk_mb/dry_ab{A,B}/`（含逐步快照）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

LATHS="1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11"

COMMON="--N 112 --dx-nm 62.5 --pair-every 20 --every 20 \
--norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
--laths $LATHS --plate-L 1000 --plate-W 500 --plate-T 510 \
--grow-stack --nuc-law athermal --nuc-init 6 --nuc-fresh-every 4 \
--alpha-km 0.041739 --T-end 298.0 --facet-proj 0 --facet-excl 0"

# ---------- 前置：把两臂的关键数解出来并落盘（**先算后跑**） ----------
"$PY" -u _r424_design.py > _r426_design.log 2>&1
echo "设计解算退出码 = $?"

rm -rf _exp/_bk_mb/dry_abA _exp/_bk_mb/dry_abB
: > _r426_ab.log

echo "############ A 臂（守 C-3）启动  $(date '+%F %T')" | tee -a _r426_ab.log
nohup "$PY" -u _bk_exp.py $COMMON \
    --steps 5922 --snap-every 40 --cool-rate 2.3524e6 \
    --tag abA --out _exp/_bk_mb > _r426_abA.log 2>&1 &
PA=$!
echo "  PID=$PA" | tee -a _r426_ab.log

echo "############ B 臂（burst）启动  $(date '+%F %T')" | tee -a _r426_ab.log
nohup "$PY" -u _bk_exp.py $COMMON \
    --steps 800 --snap-every 20 --cool-rate 1.7412e7 \
    --tag abB --out _exp/_bk_mb > _r426_abB.log 2>&1 &
PB=$!
echo "  PID=$PB" | tee -a _r426_ab.log

echo "两臂已启动（A=$PA, B=$PB）。A 预计 ≈10 h，B 预计 ≈1.4 h。" | tee -a _r426_ab.log
echo "监控：bash _r427_watch.sh" | tee -a _r426_ab.log
