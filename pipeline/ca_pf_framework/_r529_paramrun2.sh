#!/usr/bin/env bash
# R529 —— 「短跑定参数」**第四版**：把 `_r520c` 读出来的三条修正全用上。
#
# ## 相对 `_r520c` 改了什么（每一条都有实测依据）
# | # | 改动 | 依据 |
# |---|---|---|
# | ① | **去掉 `--nuc-fresh-every`**（让 N8 自动取 `K = n(T_end) = 5`） | `_r520c` 用 `K=6` ⇒ 实测只建 **4 块**（目标 8）；`R525 §5` 的闭式 `K = n(T_end)` |
# | ② | `--laths` 从 `12×6=72` 抬到 **`12×10=120`**（m=2n，给变体碰撞留 2 倍余量） | `_r520c` 实测 `nfsv_nofield = **22**`（= 100% 的拒绝），即"同变体空场"用尽；变体数固定 12（`_r526`）⇒ 只能抬 m |
# | ③ | **`--pair-every 100`**（原来 0） | `_blk_exp.py:271` 明写 `_blk_cols` **只在 `--pair-every` 命中时调用** ⇒ 0 会让 `blk_nprof`/`nblk_sig` 成空列 ⇒ 判据 P4/P6 **无从判起**（`_r520c` 的 P4/P6 FAIL 是**我自己配置造成的**，不是引擎缺口） |
#
# ## 保持不变（有意）
# `--N 64 --dx-nm 62.5`（4 µm）、`--plate-L 1000 --plate-W 500 --plate-T 510`、
# `--gamma0 0.25 --beta-h 6.477 --grow-stack`、`--nuc-law athermal --nuc-init 6`、
# `--nuc-block-target 8 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1`、
# `--qs-clock 1 --qs-max-relax 100`、`--alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6`。
# **⇒ ① ② ③ 之外逐字不动 ⇒ 差异可归因到这三条。**
#
# ## 预算（**实测，不是估的**）
# `_r520c` 的准静态钟在 **T 到 T_end 且本档收敛**时**提前结束于 step 601**
# （预算 4000，实际用 601；日志原话：「★ 准静态钟：T 已到 T_end 且本档收敛 ⇒
#  提前结束于 step 601」）⇒ **只用预算的 15%**。
# ⇒ 本轮同样预期 ~600 步；`--pair-every 100` 只多 6 次连通标注，代价可忽略。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
# `--laths` = 12 变体 × 10 场 = 120（变体数固定 12，见 `_r526_variantcount.py`）
LATHS=$(/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
print(','.join(str(v) for v in range(1, 13) for _ in range(10)))
PYEOF
)

$PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --every 20 --snap-every 200 --phi-band-every 200 \
  --pair-every 100 --norm-smooth 0 --nthreads 16 --laths "$LATHS" \
  --plate-L 1000 --plate-W 500 --plate-T 510 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack \
  --nuc-law athermal --nuc-init 6 \
  --nuc-block-target 8 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 \
  --alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
  --steps 4000 --tag r529param --out $OUT \
  > _w2_r529_param.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
$PY -u _r520_paramverdict.py dry_r529param _w2_r529_param.log
