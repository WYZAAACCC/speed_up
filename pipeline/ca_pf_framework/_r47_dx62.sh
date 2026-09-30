#!/bin/bash
# _r47_dx62.sh —— R47：**Δx=62.5 nm 的对照臂**（阶段计划第 2 步的"必需项"）
#
# ## 为什么必须跑（`R30_AUDIT_LEDGER.md` §18(5)）
# `BLOCK_DERIVATION §9.5` 的盒子尺寸约束用的是 **15.5 nm/步**，而那是
# **包围盒口径**；实测包围盒把面间距的增长放大 **2.5–2.8×**（`a`/`w` 两方向都验过）。
# 但**历史臂没有落盘 φ** ⇒ `_r47_rates.py --scan` 明确报"**无法重报**"。
# ⇒ 要替换那个数，**只能新跑一个带 φ 的 Δx=62.5 nm 臂**。
#
# ## 与 `mb1s` 的差别（**只差 Δx**，其余逐项相同）
#   mb1s  : N=96 / Δx=125  nm / 盒 12 µm
#   mb1s62: N=96 / Δx=62.5  nm / 盒 **6 µm**
# ⚠ **记账**：盒也随之减半（同一 N）⇒ 这是"Δx + 盒尺寸"的混合对照。
#   可接受的理由：实测该臂的核心 ~2.9 µm ≪ 盒半宽 3 µm（**未被壁面限制**），
#   且本对照**只回答"速率的口径与 Δx 依赖"**，不回答"盒子该多大"。
#
# ## 判据（预先登记）
#   R-1  `tip/side/wide` 三个面族的速率**量级**必须与 mb1s 同阶（同物理）
#   R-2  `t/Δx` 从 5.08 升到 10.16 ⇒ **几何解析更好**；若速率显著变化
#        ⇒ 说明 mb1s 的速率受分辨率影响，必须记账
#   R-3  `wide` 是否仍为负（退湿/变薄）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 1500 --every 40 --snap-every 250 --pair-every 40 --nthreads 3 \
  --tag mb1s62 --out _exp/_bk_mb > _w2_r47_mb1s62.log 2>&1
echo "=== R47 mb1s62 DONE rc=$? $(date '+%F %T') ==="
