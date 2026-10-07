#!/bin/bash
# _r132_swapcmp.sh —— **选支规则的受控对照**（用户裁定 C）。
#
# ## 对照设计（**只差一个因素**）
#
# | 臂 | `--rank1-swap` | 其余 |
# |---|---|---|
# | **`dry_mb2fp10`（已有，R75）** | **`none`**（弹性能极小 = `NPF`） | N=96 / Δx=62.5 / 6 µm 盒 / `--laths 1,1,1,3,3,3` / `--multi-block --block-gap-nm 2500` / L=1600 W=700 T=635 / `--facet-proj 10` / 600 步 / `--pair-every 20` |
# | **`dry_swapinv`（本脚本）** | **`invariant`** | **逐项相同** |
#
# ## 受影响变体（**算出来的**，不是写死的）
# `--rank1-swap invariant` 自己打印：
#   正对照（合成 IPS）**PASS**；受影响 = **`[1, 3, 8]`**（`rB(n*)/rB(a)` = **22.7×**）
# ⇒ R75 的两个块是 **V1（块0）与 V3（块1）** ⇒ **两块都被对调**（整构型一致改变）。
#
# ## ★ 预登记判据（**先写死再看数**）
#
# | # | 判据 | 若成立说明 |
# |---|---|---|
# | **S-0** | 两臂 **t=0** 的 `nf2`、`nblk_sig`、`blk_nprof`、`blk_laths` 都合法（`nf2=0`、`nblk_sig=2`、`nblk_prof=3/3`） | 两臂的播种几何**都可用**（对调会改变板条形状 ⇒ **必须重查**，不能假设） |
# | **S-1** | 两臂的 `cov(t=0)` 都 ≥ 该 `L` 的基线×0.95（`cov_base(1600)=1.079`） | 块内界面在**两臂**都完整 |
# | **S-2** | **形态学结论是否改变**：`f_flat` 终态、`blk_span_nm`/`blk_alen_nm`/`blk_wlen_nm` 的增长方向、`blk_nprof` | **不变** ⇒ 已有形态学结论全部有效，只是**晶体学归属**要改；**变了** ⇒ 更大的发现，需重做相关结论 |
# | **S-3** | `box_touch_core == 0` 全程 | 不撞壁 |
#
# ⚠ **记账**
#   * 对调 `n*`↔`a` **会改变种子的形状**（厚 635 沿**新的** `n*`、长 1600 沿**新的** `a`）
#     ⇒ `nf2(t=0)` 等几何量**必须重查**（S-0），**不得**假设与对照臂相同。
#   * `w` 不变（`cross(a,n) = −cross(n,a)` ⇒ 同一条线）。
#   * `--rank1-swap none` 是默认 ⇒ 归档路径**逐位不变**（由 `_r30_regress.sh` 把关）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_mb/dry_swapinv
echo "=== R132 选支受控对照开始 $(date '+%F %T')"
$PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1,3,3,3 --multi-block --block-gap-nm 2500 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --rank1-swap invariant \
  --facet-proj 10 \
  --steps 600 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag swapinv --out _exp/_bk_mb > _w2_r132_swapinv.log 2>&1
echo "=== R132 结束 rc=$? $(date '+%F %T')"
