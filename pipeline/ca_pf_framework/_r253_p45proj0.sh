#!/bin/bash
# _r253_p45proj0.sh —— ★★ **`§144` 的决定性跟进**：在 `--facet-proj 0` 下重跑 P1-45 对照。
#
# ## 为什么（`§144`）
# 受控实验（γ_F3 差 **31.3×**，只差 `--facet-proj`）实测：
#   * **无投影** ⇒ 形态量相差可达 **91%**（`f3_area` 3.8e-3、`Vt` 1.2e-2、`n_lath` 2.8e-2）
#   * **有投影** ⇒ **形态量逐位为零**（`f3_area`/`nf3`/`Vt`/`n_lath`/`w_lath`/`f3_pos` 全 **0.000e+00**）
# ⇒ **`--facet-proj 10` 把界面能通道整体压掉了。**
# 而 `_r225` 的 P1-45 两臂**都带 `--facet-proj 10`**（`_r251` 核实）
# ⇒ **`_r225` 测不出差别是"预期内"的，不是 `§138` 的反证。**
#
# ## 本实验（**只改一个开关**：`--facet-proj 10 → 0`）
# 与 `_r225` **逐字相同**的几何与两臂，**唯一差别**是 `--facet-proj 0`。
#
# ## 预登记判据（**先写死**）
# * **Z-1** 两臂 `nf2(t=0)=0` 且 `cov_norm ≥ 0.95`（几何验收；⚠ 投影关了**可能**影响 `cov`，
#   因为 `cov` 由**播种**几何决定 —— **必须实测**，不过就报"几何不合格"而不是硬跑）。
# * **Z-2** ★ **核心**：逐列差异。**预言**：关掉投影后，**分叉步数占比应显著上升、
#   幅度应显著变大**（对照 `_r225` 的"只有 step 80、幅度 2.5e-2"）。
# * **Z-3** 记录 `f3_area` / `nf3` / `blk_nprof` / `r_selfac` 的**末态符号方向**
#   （`§140.3` 的 O-2 预言：更便宜的 F3 ⇒ `f3_area` 更大）。
# * **Z-4** 前置：两臂输出目录**必须不同**（硬规则㉔，`§143.5` 的教训）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

GEO="--arm dry --N 112 --dx-nm 62.5 --plate-L 1000 --plate-W 500 --plate-T 510 \
     --plate-t-physical 400 --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 \
     --reinit-dt 1e-4 --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 1300 \
     --facet-proj 0 --steps 400 --every 20 --snap-every 20 --pair-every 20 \
     --nthreads 4 --out _exp/_bk_mb"

rm -rf _exp/_bk_mb/dry_p45L0 _exp/_bk_mb/dry_p45P0

echo "=== Z-4 前置：输出目录必须不同 ==="
echo "  p45L0 目录将写到 _exp/_bk_mb/dry_p45L0"
echo "  p45P0 目录将写到 _exp/_bk_mb/dry_p45P0"
echo "  ⇒ 路径不同 ✅（tag 不同 ⇒ 目录不同）"
echo
echo "=== §144 决定性跟进开始 $(date '+%F %T') ==="
echo "--- 臂 L0（ladder，**无投影**）---"
$PY -u _bk_exp.py $GEO --omega-mode ladder  --omega-max-deg 5.0  \
    --diag-terms --tag p45L0 > _w2_r253_L0.log 2>&1 &
A=$!
echo "--- 臂 P0（perstep 0.4545°，**无投影**）---"
$PY -u _bk_exp.py $GEO --omega-mode perstep --omega-max-deg 0.4545 \
    --diag-terms --tag p45P0 > _w2_r253_P0.log 2>&1 &
B=$!
echo "  PID: L0=$A P0=$B"
wait $A; echo "  臂 L0 rc=$?  $(date '+%T')"
wait $B; echo "  臂 P0 rc=$?  $(date '+%T')"
echo "=== 结束 $(date '+%F %T') ==="
for f in _w2_r253_L0.log _w2_r253_P0.log; do
  printf '  %-22s Traceback=%s\n' "$f" "$(grep -c Traceback "$f" || true)"
done
