#!/bin/bash
# _r225_p45cmp.sh —— ★ **P1-45 的受控对照**：`ladder` vs `perstep`（`§136.4` 的待办）。
#
# ## 为什么现在能做（此前做不了）
# `§130.2`：**M=12 时 `ladder(5°)` 与 `perstep(5/11°)` 恒等** ⇒ 归档的 6 块几何上
# 两种参数化**没有差别**，做不出对照。
# `_r223_geoscan.sh` 刚找到一个 **M=6 且两条验收判据都过**的几何：
#   **m6a**：`1,1,3,3,5,5` / N=112 / L=1000 / W=500 / T=510 / gap=1300
#   ⇒ `cov_norm` = **1.054**（≥0.95 ✅）、**`nf2(t=0)` = 0**（✅ 真正分离）、`n_occ` = 6/6
#
# ## 两臂（**单变量**：只差 `--omega-mode` + `--omega-max-deg` 这一对）
# | 臂 | 参数 | M=6 时的 F3 θ（|i−j|=1 / 5）| F3 γ（/γ₀=0.25）|
# |---|---|---|---|
# | **`p45L`** | `--omega-mode ladder --omega-max-deg 5.0`（**归档行为**）| 1.000° / 5.000° | 0.0979 / **0.2771**（0.392× / **1.108×**）|
# | **`p45P`** | `--omega-mode perstep --omega-max-deg 0.4545` | 0.4545° / 2.2725° | 0.0540 / ~0.172（0.216× / ~0.69×）|
# ⇒ **块内界面能相差 1.6–1.8 倍**（远者更多），且 **P 臂与 M 无关**。
#
# ## 预登记判据（**先写死**）
# * **O-1** 两臂 `nf2(t=0) = 0` 且 `cov_norm ≥ 0.95`（接线/几何合格）。
# * **O-2** ★ **核心**：`§138.3` 证明 F3（同变体）上 `Δed ≡ 0`
#   ⇒ **块内界面运动完全由界面能控制** ⇒ **把 F3 变便宜（P 臂）应产生可测差别**：
#   预期 **P 臂的 `f3_area` 更大**（块内界面更"站得住"）。
#   **若两臂无差别 ⇒ `§138.3` 的推论不成立**（那是一个重要的反证）。
# * **O-3** `blk_nprof` 应全程 == M = 6（块结构不被破坏）。
# * **O-4** 记录三类面积占比（`f1_area`/`f2_area`/`f3_area`）与 `§135.7` 的三项量级。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

GEO="--arm dry --N 112 --dx-nm 62.5 --plate-L 1000 --plate-W 500 --plate-T 510 \
     --plate-t-physical 400 --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 \
     --reinit-dt 1e-4 --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 1300 \
     --facet-proj 10 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
     --nthreads 4 --out _exp/_bk_mb"

echo "=== P1-45 受控对照开始 $(date '+%F %T') ==="
echo "  几何 = m6a（`_r223` 验收：cov_norm 1.054 / nf2(t=0)=0）"
echo
echo "--- 臂 L（ladder，归档行为）$(date '+%T') ---"
$PY -u _bk_exp.py $GEO --omega-mode ladder --omega-max-deg 5.0 \
    --diag-terms --tag p45L > _w2_r225_p45L.log 2>&1 &
PL=$!
echo "--- 臂 P（perstep 0.4545°）$(date '+%T') ---"
$PY -u _bk_exp.py $GEO --omega-mode perstep --omega-max-deg 0.4545 \
    --diag-terms --tag p45P > _w2_r225_p45P.log 2>&1 &
PP=$!
echo "  PID: L=$PL P=$PP（**并行**）"
wait $PL; echo "  臂 L 退出码 $?  $(date '+%T')"
wait $PP; echo "  臂 P 退出码 $?  $(date '+%T')"
echo "=== 结束 $(date '+%F %T') ==="
