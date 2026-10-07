#!/bin/bash
# _r139_swapcmp2.sh —— 选支受控对照 **v2**：换更大的盒子（消掉撞壁）。
#
# ## 为什么要重跑（`_r134` 的判决）
#
# R132 在 **N=96（6 µm 盒）** 上跑出来的结果是：
#   * **S-1 PASS**（`cov_norm = 0.985`，块内界面质量两臂相同）；
#   * **S-3 FAIL**：对调臂 `box_touch_core = 1`（**撞壁**）——
#     它的 `blk_alen_nm` 末态 **5630 nm**，而盒只有 **6000 nm** ⇒ **末态受盒壁限制**；
#   * ⇒ **S-2（形态学结论变不变）在"两臂末态条件不同"的情况下不可判读。**
#     已观察到的强信号（对调臂 `a` 增长 +3728 vs 对照 +1354 nm）**不能当结论**。
#
# ## v2 的修法（**只改盒子，其余不动**）
#   `N=96 → 128`（**6 µm → 8 µm**），板条/间距/步数/投影全不变
#   ⇒ 块沿 `a` 的余量从 ~370 nm 提到 ~2000 nm，**不会撞壁**。
#   ⚠ **两臂都要重跑**（`mb2fp10` 是 N=96 的，不能当 N=128 的对照）。
#
# ## 预算（`§7.2c` 标度律，nreg=7）
#   RSS ≈ 227×(128³×7/1e6) ≈ **3.3 GB/臂**；≈ **7.5 s/步** ⇒ 600 步 ≈ **75 min/臂**
#   两臂并发 ≈ 6.6 GB ✓
#
# ## 预登记判据（与 v1 相同，只有 `S-1` 的基线因盒/分辨率不变而沿用）
#   **S-0** 两臂 `nf2(t=0)==0`、`nblk_sig==2`、`blk_laths==3/3`
#   **S-1** 两臂 `cov(t=0) ≥ 1.025`（= `cov_base(1600)×0.95`）
#   **S-2** 形态学：`blk_span/alen/wlen` 的**增长方向**与**末态差**
#   **S-3** 两臂 `box_touch_core == 0` **全程**（v1 就是死在这一条 ⇒ 必须过）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

run() {   # run <tag> <extra...>
  local TAG="$1"; shift
  rm -rf "_exp/_bk_mb/dry_$TAG"
  echo "--- $TAG  extra='$*'  $(date '+%T')"
  $PY -u _bk_exp.py --arm dry --N 128 --dx-nm 62.5 \
    --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 2500 \
    --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --facet-proj 10 \
    --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 4 \
    --tag "$TAG" --out _exp/_bk_mb "$@" > "_w2_r139_${TAG}.log" 2>&1
  echo "--- $TAG DONE rc=$? $(date '+%T')"
}

echo "=== R139 选支对照 v2 开始 $(date '+%F %T')"
run swN128      --rank1-swap none      &
run swINV128    --rank1-swap invariant &
wait
echo "=== R139 结束 $(date '+%F %T')"
