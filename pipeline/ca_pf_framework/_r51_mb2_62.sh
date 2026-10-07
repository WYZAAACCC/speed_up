#!/bin/bash
# _r51_mb2_62.sh —— R51：**多块自协调臂的"分辨率合规"版本**
#
# ## 为什么必须重跑（`R30_AUDIT_LEDGER.md` §33）
# `eng_mb2`/`eng_mb3` 是**多块 + 自协调**（6 变体 × 2 根 = 12 根）的主力臂，
# 但它们用 **Δx = 125 nm**，而板条含界面厚度 635 nm ⇒ **`t/Δx = 5.08`**。
# §33 实测：`t/Δx ≈ 5` 时**界面分不清"侧面推进"与"端面推进"**
# ⇒ 板条被抹成等轴的（`mb1s` 给 side > tip）；
# 而 `t/Δx = 10.2` 时**恢复各向异性**（`mb1s62` 给 tip > side）。
# ⇒ **`eng_mb2` 的结论（P-SA-1 等）是在一个"板条性已失真"的分辨率下得到的**
#    ⇒ 必须在 **Δx = 62.5 nm（`t/Δx = 10.16`）**上复做。
#
# ## 与 `eng_mb2` 的差别（**只差 Δx**，其余逐项相同）
#   eng_mb2 : N=96 / Δx=125  nm / 盒 12 µm
#   mb2_62  : N=96 / Δx=62.5 nm / 盒 **6 µm**
# ⚠ **记账**：同 N ⇒ 盒也随之减半 ⇒ 这是"Δx + 盒尺寸"的混合对照。
#   可接受的理由：`eng_mb2` 的 12 根是**紧凑放置**（`--eng-r-nm 320`、
#   `--nuc-overlap-nm 0`、`gap_nm=0`）⇒ 簇的尺度 ~2 µm ≪ 6 µm；**由本次冒烟验证**。
#
# ## 预算（实测标度律，`_r51_cost.py` / `_r51_mem.py`）
#   `N³·nreg/1e6` = 96³×13/1e6 = **11.5**
#   时间 ≈ 0.507 s × 11.5 ≈ **5.8 秒/步**（当前并行负载下）
#   内存 ≈ 227 MB × 11.5 ≈ **2.6 GB**
#   ⇒ 600 步 ≈ 1.0 h；1500 步 ≈ 2.4 h
#
# ## 模式
#   本文件默认 **SMOKE**（`--steps 120`），只验"构型能建起来 + 12 根被解析"。
#   要转正式跑：把 `STEPS` 改成 900（与 `eng_mb2` 同）或 1500。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

MODE="${1:-smoke}"
case "$MODE" in
  smoke) STEPS=120; EV=20; SNAP=20 ;;
  full)  STEPS=900; EV=20; SNAP=20 ;;
  *) echo "用法: $0 [smoke|full]"; exit 2 ;;
esac

COMMON="--arm eng --N 96 --dx-nm 62.5 \
  --laths 1,1,2,2,3,3,4,4,5,5,6,6 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --eng-r-nm 320 --eng-t-nm 510 --eng-elong 3.0 --nuc-overlap-nm 0 \
  --eng-cadence 60 --nuc-init 30 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps $STEPS --every $EV --snap-every $SNAP --pair-every $EV --nthreads 3"

echo "=== R51 mb2_62 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py $COMMON --var-rule ed --tag mb2_62 --out _exp/_bk_mb \
  > "_w2_r51_mb2_62_${MODE}.log" 2>&1
rc=$?
echo "=== R51 mb2_62 rc=$rc  $(date '+%F %T')"
exit $rc
