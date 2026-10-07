#!/bin/bash
# _r51_b62p.sh —— R51 **方案 B′**：修正后的"分辨率合规 + 两块互不接触"盒子
#
# ## 为什么是 B′（不是 B）（`BLOCK_SELFAC.md` §7.2h/§7.2i）
# 6 µm 盒（N=96）**装不下两块**：实测 t=0 就有 **`nf2 = 692`** 个异变体界面
# ⇒ 初始混杂 ⇒ 读数不可用。根因是**分辨率判据（`Δx≤63 nm`）与盒子设计冲突**：
# Δx 一压，盒边长 `N·Δx` 就小，而结构尺寸是按 12 µm 盒设计的。
# 定量解：两块各 3 层、板 `L=2000 W=700 T=510`（`L/W=2.9`、`W/T=1.37`、`t/Δx=8.2`）
#   `L_grown + gap + L_grown + 2×余量 ≈ 2600+1500+2600+2000 = 8700 nm`
#   ⇒ **N = 144（盒 9 µm）**。
#
# ## 预算（§7.2c 实测标度律）
#   `N³·nreg/1e6 = 144³×7/1e6 = 20.9`
#   时间 ≈ 0.507×20.9 ≈ **10.6 秒/步**；RSS ≈ 227 MB×20.9 ≈ **4.7 GB**
#   ⇒ 900 步 ≈ **2.6 h**（可与其他臂并行）
#
# ## 预登记判据（**先写死，跑完照此判**）
#   J-0  **`nf2(t=0) == 0`** —— 两块初始不接触（*否则整条臂作废*）
#   J-1  `t/Δx = 10.16 ≥ 10` —— 板条被解析（§33）
#   J-2  `nslab_n == M`（或去重场数 == M）—— 两块都堆成块
#   J-3  `nf2` 随步数**单调增** —— 两块真的开始互相影响
#   J-4  `box_touch_core == 0` 全程 —— 没撞壁
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

MODE="${1:-smoke}"
case "$MODE" in
  smoke) STEPS=60 ;;
  full)  STEPS=900 ;;
  *) echo "用法: $0 [smoke|full]"; exit 2 ;;
esac

echo "=== R51 b62p 模式=$MODE steps=$STEPS  $(date '+%F %T')"
"$PY" -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 1500 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps "$STEPS" --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62p --out _exp/_bk_mb > "_w2_r51_b62p_${MODE}.log" 2>&1
rc=$?
echo "=== R51 b62p rc=$rc  $(date '+%F %T')"
echo "--- J-0 初始接触检查（nf2(t=0) 必须为 0）"
"$PY" _r51_b62chk.py _exp/_bk_mb/dry_b62p/series.csv 2>&1 | tail -3
exit $rc
