#!/bin/bash
# _r64_el.sh —— **§53 预登记的决定性实验**：关掉/减弱弹性驱动，看 `v_a/v_w` 会不会跳到 ≳9。
#
# ## 为什么这是唯一剩下的实验
# 角函数端的三条假设**全部被排除**：
#   ① 大小（§40：`β_w` 加到 12 只给 5.83）
#   ② 形状/凹陷（§45 E-1：三种平流格式都 1.6–2.0）
#   ③ 极比（§53：3 → 9 只动 0.82 → 1.59）
# ⇒ 剩下两个嫌疑：**弹性驱动 `dG(n)` 的反向补偿** 与 **界面表示（无刻面机制）**。
#
# ## 判据（**先写死**）
#   L-1 `el_scale=0` 的 `v_a/v_w` **≥ 6** ⇒ **限速环节是弹性驱动**
#       （那 `M(n)` 的设计是好的，问题在 `ed` 的角分布）
#   L-2 `el_scale=0` 仍 ≈1.6 ⇒ **限速环节在平流/界面表示**（回到 §43）
#   L-3 `el_scale=0.5` 应落在两者之间（单调性守卫：若不然，说明不是线性叠加）
#
# 配置与 `_r64_accept.sh` 逐项相同（单板条、N=64、Δx=62.5、400 步），**只差 `--el-scale`**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== 弹性缩放实验  $(date '+%F %T')"
for ES in 0 0.5 1; do
  TAG="el$(echo "$ES" | tr -d '.')"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  el_scale=$ES  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --el-scale "$ES" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r64_${TAG}.log" 2>&1
  echo "    rc=$?"
done
echo "=== 完成 $(date '+%F %T')"
