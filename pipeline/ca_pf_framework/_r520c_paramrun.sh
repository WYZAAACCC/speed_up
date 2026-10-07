#!/usr/bin/env bash
# R520c —— 「短跑定参数」**第三版**：去掉 `--multi-block`，让**形核自己建块**。
#
# ## 前两版为什么崩（**同一处，且是一条真缺陷**）
#   `ValueError: elongated seed exceeds domain: elong*R=5e-07 um > margin -9.9e-06 um`
#   追到 `_bk_exp.py:838`（`--multi-block` 的逐块播种）：块心 `_cb = c0 + _xi·u`，
#   其中 `_xi = (_b − (nb−1)/2)·_gap_blk`。
#
#   | 量 | 值 | 出处 |
#   |---|---|---|
#   | `_gap_blk` **默认** | **2.0 µm** | `_bk_exp.py:716`（`--block-gap-nm ≤ 0` 时） |
#   | `nb` | **12**（= 变体数，每变体一块） | `--multi-block` 的分组 |
#   | ⇒ 块心跨度 | `11 × 2 µm = 22 µm` | 远超 `L_box = 4 µm` |
#
#   **★★ 而驱动的**边界守卫**（`_bk_exp.py:1015`）算的是**
#       `margin = 0.5·L − 0.5·plate_L − 0.5·gap`      ← **只算了 1 个 gap**
#   而真实跨度需要 `(nb−1)` 个 gap ⇒ **它算出 `margin = +500 nm`（"没问题"），
#   实际却是 −40 nm**（`seed_plate` 里才炸）。
#   **⇒ 这是一条"守卫没守住"的缺陷**（本仓 `AGENTS.md §3.4` 的同类：
#     "写守卫时要反向测一次"）。**本轮只登记，不改**（改 guard 要单独做与回归）。
#
# ## 第三版：不用 `--multi-block`
#   让**形核机制自己建块**（`--nuc-block-target 8` + `--nuc-fresh-every 6`）——
#   这本来就是 C3/C6 要问的"涌现"路径，比预播种更贴题。
#   ⚠ 代价：`blk_nprof`/`nblk_sig` 可能为空列（abA 就是），
#     ⇒ 判据 P4 若因此拿不到数，**按"未取证"记**，不硬判。
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
  --steps 4000 --tag r520param --out $OUT \
  > _w2_r520_param.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
$PY -u _r520_paramverdict.py
