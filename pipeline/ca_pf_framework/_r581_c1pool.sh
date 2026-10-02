#!/bin/bash
# _r581_c1pool.sh --- ★★ 用 `--eng-seed` 把多个 seed 的位点**合并**，
#   解决 C1「统计均匀」那一半**功效极低**的问题（单臂只有 4–5 个位点）。
#
# ## 为什么这是**合法**的合并（不是凑数）
# `_nuc_place_initial` 在 **`nuc_cfg` 时（t=0）** 就一次性撒下 `n_init` 个位点，
# 用的是 `np.random.default_rng(seed)`。**不同 seed ⇒ 同一分布的不同抽样。**
# 盒子的几何（`L`、`pad`、`nreg`）**逐臂相同** ⇒ 12 个 seed 的位点
# **是同一个均匀分布的 12 组独立样本** ⇒ **合并后的检验功效显著提高**。
# ⚠ 记账：合并检验的是「**生成器**是不是均匀」，**不是**"某一次运行"是不是均匀。
#   对 C1 的表述（"位点…统计上均匀"）来说，这正是要问的那个问题。
#
# ## 为什么可以跑得极快
# 位点在 **t=0** 就定好了 ⇒ **不需要跑演化**。`--steps 2` 足够让 `nuc_dbg.json` 落盘。
#
# ## 判据（预先写死）
# 用 `_r581_c1uni.py` 的同一套判据（KS / χ² 八分体 / 最近邻 vs CSR），
# 但**样本量从 4–5 提到 ~70** ⇒ 功效从"极低"升到"可用"。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_pool"
CORES="${R581P_CORES:-12-15}"
SEEDS="${R581P_SEEDS:-11 12 13 14 15 16 17 18 19 20 21 22}"
COMMON="--N 64 --dx-nm 62.5 --steps 2 --every 1 --snap-every 99999 \
  --pair-every 0 --norm-smooth 0 --nthreads 4 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 3 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis"

echo '=== R581：多 seed 合并位点（C1 功效）==='
for s in $SEEDS; do
  tag="s$s"
  d="$ROOT/dry_$tag"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  taskset -c "$CORES" $PY -u _bk_exp.py $COMMON --out "$ROOT" --tag "$tag" \
      --eng-seed "$s" > "_w2_r581_pool_${tag}.log" 2>&1
  n=$(grep -c '^Traceback' "_w2_r581_pool_${tag}.log" || true)
  printf '   seed=%-4s exit=%s Traceback=%s\n' "$s" "$?" "$n"
done

$PY _r581_c1pool.py "$ROOT" $SEEDS
echo "=== R581 C1POOL DONE $(date '+%F %T') ==="
