#!/bin/bash
# _r223_geoscan.sh —— 为 **P1-45 的受控对照**找**小 M** 的合格几何。
#
# ## 为什么必须小 M
# `§130.2`：**M=12 时 `ladder(5°)` 与 `perstep(0.4545°)` 恒等**（因 `5/11 = 0.4545`）
# ⇒ 在归档的 6 块几何上**两种参数化没有差别**，做不出对照。
# ⇒ 必须用 **M=2/4/6**：`§129.2` 实测 M=4 时 ladder 的 F3 γ ∈ {0.1407, **0.2771**}
#   （后者 **1.108×γ₀，倒挂**），而 `perstep(0.4545°)` 恒为 **0.0540**（0.216×γ₀）
#   ⇒ **块内界面能差 5.1 倍**，对照有强分辨力。
#
# ## 验收判据（`§99` 规程⑧，**两条都要过**）
# * **B-1** 块间 `nf2(t=0) == 0`（"真正分离"）
# * **B-2** 块内 `cov_norm ≥ 0.95`（播种阶段没把 F3 播坏）
#
# ⚠ `cov_norm` 只由**播种几何**决定（与 `ω` 无关）⇒ 两种模式共用同一次几何检查。
# ⚠ 用 `--steps 1` 跑：只看 **t=0 自检**，不必演化 ⇒ 每个候选十几秒。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

cand() {   # cand <tag> <laths> <N> <L> <W> <T> <gap>
  local TAG="$1" LAT="$2" NN="$3" LL="$4" WW="$5" TT="$6" GAP="$7"
  rm -rf "_exp/_bk_geo/dry_$TAG"
  $PY -u _bk_exp.py --arm dry --N "$NN" --dx-nm 62.5 \
    --plate-L "$LL" --plate-W "$WW" --plate-T "$TT" --plate-t-physical 400 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths "$LAT" --multi-block --block-gap-nm "$GAP" \
    --facet-proj 10 --steps 1 --every 1 --snap-every 1 --pair-every 0 \
    --nthreads 2 --tag "$TAG" --out _exp/_bk_geo > "_w2_r223_${TAG}.log" 2>&1
  local RC=$?
  local COV NF2 NC
  COV=$(grep -o 'cov_norm` = [0-9.]*' "_w2_r223_${TAG}.log" | tail -1 | grep -o '[0-9.]*$')
  NF2=$(grep -o '的 t=0 的两块异变体接触面 = \*\*[0-9]*\*\*' "_w2_r223_${TAG}.log" \
        | grep -o '[0-9]*' | tail -1)
  NC=$(grep -o 'n_occ` = [0-9]*/[0-9]*' "_w2_r223_${TAG}.log" | tail -1)
  printf '  %-8s rc=%-3s cov_norm=%-8s nf2(t=0)=%-8s %s\n' \
    "$TAG" "$RC" "${COV:-?}" "${NF2:-?}" "${NC:-}"
}

echo "=== 小 M 几何扫描开始 $(date '+%F %T') ==="
echo "  格式：tag rc cov_norm nf2(t=0) n_occ"
echo
echo "--- M=4：2 块 × 2 根（\`1,1,3,3\`）---"
cand m4a "1,1,3,3" 112 1000 500 510 1300 &
cand m4b "1,1,3,3" 112  800 600 635 1200 &
cand m4c "1,1,3,3" 128 1000 600 635 1300 &
cand m4d "1,1,3,3" 112  600 400 510 1000 &
wait
echo
echo "--- M=6：3 块 × 2 根（\`1,1,3,3,5,5\`）---"
cand m6a "1,1,3,3,5,5" 112 1000 500 510 1300 &
cand m6b "1,1,3,3,5,5" 112  800 600 635 1200 &
cand m6c "1,1,3,3,5,5" 128 1000 600 635 1300 &
cand m6d "1,1,3,3,5,5" 112  900 450 510 1100 &
wait
echo
echo "--- M=2：1 块 × 2 根（\`1,1\`，块间判据平凡）---"
cand m2a "1,1" 96 800 600 510 0 &
cand m2b "1,1" 112 1000 500 510 0 &
wait
echo "=== 结束 $(date '+%F %T') ==="
