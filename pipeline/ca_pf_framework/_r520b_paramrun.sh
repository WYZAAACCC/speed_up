#!/usr/bin/env bash
# R520b —— 「短跑定参数」**第二版**（第一版被一个**我漏掉的几何约束**打回）。
#
# ## 第一版为什么崩（**真实约束，不是 bug**）
#   `ValueError: elongated seed exceeds domain: elong*R=5e-07 um > margin -9.9e-06 um`
#   追到 `_bk_exp.py:838`（`--multi-block` 的逐根播种）：
#       `_off = (_j − (len(_fs)−1)/2) · (T + gap)`  ⇒ 9 根 × 510 nm = **4.59 µm**
#   而 `L_box = 4 µm` ⇒ **栈放不下**，第一根的块心算出来是 **−40 nm**（负）⇒ 边界守卫触发。
#
# ## ★★ 这是一条**我此前没列进五约束的第六约束**
#
#       **⑥ 堆叠必须装得下：`n · t ≤ L_box`**
#
#   | `t` = 510 nm | `n` 上限 | 用 C-2 的 `n = α_KM·575` 反推需要的 `L_box` |
#   |---|---|---|
#   | L=4 µm | **7.8** | — |
#   | L=7 µm（**abA 的盒子**） | 13.7 | — |
#   | **α_KM=0.0417 ⇒ n=24** | — | 需 `L ≥ 12.2 µm` ❌ **abA 的 7 µm 装不下** |
#   | **α_KM=0.011 ⇒ n=6.3** | — | 需 `L ≥ 3.2 µm` ✅ |
#
#   **⇒ 这是 `α_KM = 0.011` 的第**三**条独立支持**（前两条：块厚带、C3 与带的交集）。
#   **⇒ 也解释了 abA 为什么堆不起来：它的盒子（7 µm）按 C-2 需要 12.2 µm。**
#
# ## 第二版配置（**修正后**）
#   `--laths` 改成 **12 变体 × 6 场 = 72**（栈高 6×510 nm = **3.06 µm** < 4 µm ✅）
#   其余与第一版相同（椭球、α_KM=0.011、B=8、qs 钟、超临界、位点补货、`--multi-block`）
#
# ## 预登记判据（**沿用第一版 P1–P6**，不改）
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
LATHS=$(/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
print(','.join(str(v) for v in range(1, 13) for _ in range(6)))
PYEOF
)
echo "  --laths = $LATHS"
echo "  栈高检查：6 × 510 nm = 3060 nm < L=4000 nm ⇒ ✅ 装得下"

$PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --every 20 --snap-every 200 --phi-band-every 200 \
  --pair-every 0 --norm-smooth 0 --nthreads 16 --laths "$LATHS" \
  --plate-L 1000 --plate-W 500 --plate-T 510 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-fresh-every 6 \
  --nuc-block-target 8 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 \
  --alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
  --multi-block --steps 4000 --tag r520param --out $OUT \
  > _w2_r520_param.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
$PY -u _r520_paramverdict.py
