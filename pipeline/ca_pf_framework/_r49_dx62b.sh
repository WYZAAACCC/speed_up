#!/bin/bash
# _r49_dx62b.sh —— R49：**Δx=62.5 nm 的对照臂，重跑版**
#
# ## 为什么重跑（而不是接着 `_r47_dx62.sh` 的产物）
# `_r47_dx62.sh` 用的是 `--every 40 --snap-every 250`，而**旧代码把快照块放在
# `--every` 门里面** ⇒ 实际快照间隔 = **lcm(40,250) = 1000 步**，
# 1500 步的臂**只会有 3 个快照**（0/1000/1500）。
# 这条臂的**唯一目的**就是给 `face_separations`（金标准面间距量具）提供
# **时间序列**，3 个点等于没有误差棒、也没法把初始瞬态与稳态段分开
# ⇒ 花 68 min 换一个"量不出不确定度"的数，不划算。**已在 360 步处杀掉重跑。**
#
# ## 修复（`_bk_exp.py` R49）
# 快照单开一条路径 ⇒ `--snap-every` **精确生效**。
# 正对照 `_r49_snapgate.sh`：`--every 50 --snap-every 40` 的 CSV 行 = 0/50/100/120，
# 快照 = 0/40/80/120 ⇒ PASS（旧代码只会给 0/100/120）。
#
# ## 与 `mb1s` 的差别（**只差 Δx**，其余逐项相同）
#   mb1s  : N=96 / Δx=125  nm / 盒 12 µm
#   mb1s62: N=96 / Δx=62.5 nm / 盒 **6 µm**
# ⚠ **记账**：盒也随之减半（同一 N）⇒ 这是"Δx + 盒尺寸"的混合对照。
#   可接受的理由：实测该臂的核心 ~2.9 µm ≪ 盒半宽 3 µm（**未被壁面限制**），
#   且本对照**只回答"速率的口径与 Δx 依赖"**，不回答"盒子该多大"。
#
# ## 判据（预先登记，与 `_r47_dx62.sh` 逐字相同，便于对照）
#   R-1  `tip/side/wide` 三个面族的速率**量级**必须与 mb1s 同阶（同物理）
#   R-2  `t/Δx` 从 5.08 升到 10.16 ⇒ **几何解析更好**；若速率显著变化
#        ⇒ 说明 mb1s 的速率受分辨率影响，必须记账
#   R-3  `wide` 是否仍为负（退湿/变薄）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_mb/dry_mb1s62          # 清掉旧的 3 快照产物（口径不同，不可混用）

"$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 1500 --every 40 --snap-every 40 --pair-every 40 --nthreads 3 \
  --tag mb1s62 --out _exp/_bk_mb > _w2_r49_mb1s62.log 2>&1
echo "=== R49 mb1s62 DONE rc=$? $(date '+%F %T') ==="
