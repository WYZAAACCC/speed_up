#!/bin/bash
# _r70_sweep.sh —— **扫 `--facet-proj`**：分离"保面"与"压回侧向生长"两种效应
#
# ## 为什么要扫（`R30_AUDIT_LEDGER.md` §66 的记账）
# `facet_proj=20` 给 `v_a/v_w = 39.5`，**超过**理论 Wulff 比 8.93
# ⇒ 因为投影**强制**形状回到盒子，宽度被反复压回（`d(w)=0.101` 近乎冻结）
# ⇒ `facet_proj` **同时扮演两个角色**：
#   ① **保面**（把被磨圆的角换回平面）—— 这是我们**想要**的；
#   ② **压回侧向生长**（表示层约束）—— 这是**人为**的。
# ⇒ 必须扫 `N_proj` 把两者分开：`N_proj` 越大（投影越稀）⇒ ② 越弱。
#
# ## 判据（先写死）
#   S-1 `f_flat`(400) 随 `N_proj` **单调降**（投影越稀，面越守不住）
#   S-2 `v_a/v_w` 随 `N_proj` **单调降**（② 越弱）
#   S-3 存在 `N_proj*` 使 `f_flat ≥ 0.05` **且** `v_a/v_w ≥ 3`
#       ⇒ 该点可作为"保面为主、压回次要"的工作点
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
echo "=== facet-proj 扫描  $(date '+%F %T')"
for NP in 5 10 40 100; do
  TAG="fp${NP}"
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  facet_proj=$NP  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 --laths 1 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj "$NP" \
    --steps 400 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
    --tag "$TAG" --out _exp/_bk_mb > "_w2_r70_${TAG}.log" 2>&1 &
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
done
wait
echo "=== 完成 $(date '+%F %T')"
