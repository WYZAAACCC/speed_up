#!/usr/bin/env bash
# R539 —— **按 N11 取证结论改 `B`**：`--nuc-block-target 8 → 5`。
#
# ## 依据（`R525_TASK5_PARAM_FINDINGS.md §4` 的取证链，全部实测）
#   `--nfsv-diag 1` 的读数证明：
#     * 全盒非空场只有 **18/120（15%）**，而**那一个变体**的场已被用光
#       ⇒ 瓶颈是「**每变体配额**」，**不是**全盒容量；
#     * `occ_min = 404` 胞 ⇒ **碎点占场假设被否**；
#     * 上游真卡点是 **`fresh_blocked = 17`**（建不成新块）
#       ⇒ 需求全压在一个块上 ⇒ 把变体 V1 的 10 个场吃光 ⇒ 第 11 根没处放 ⇒ 拒。
#     * `supercrit = 5` ⇒ **物理只给了 ~5 个超临界位点**，而目标是 **8 块**。
#
# ## 本跑的**唯一改动**
#   `--nuc-block-target 8 → 5`（其余与 `_r535diag` **逐字相同**，含 `--nfsv-diag 1`）。
#   ⇒ **单变量**。逻辑：`B` 是**输入**（框架 `limitations()` 第 1 条明写"块的数目没有律"），
#     而**超临界位点数是物理给的**（实测 5）⇒ 让 `B` 服从物理，
#     需求就不再压在单块上。
#
# ## 预登记判据（**先写死，再跑**）
# | # | 判据 | 对照（`_r529` / `_r535diag`） |
# |---|---|---|
# | **Q1** | `nfsv_nofield` **≤ 5** | 21 |
# | **Q2** | 事件数 / 目标 **≥ 0.70** | 18/40 = 0.45 |
# | **Q3** | `fresh_blocked` **≤ 8** | 17 |
# | **Q4** | C3 仍成立：`blk_nprof == blk_laths` 且 `nblk_sig ≥ 2` | `_r529` PASS |
# | **Q5 正对照** | 本跑与 `_r529` 的差异**只应来自 `B`** | `--nfsv-diag`/`--pair-every`/`--nthreads` 已证**不改物理** |
# ⚠ 若 Q1 不过 ⇒ **"让 B 服从物理"这条建议被否**，照实记，不得宣称闭环。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

OUT=_exp/_bk_mb
LATHS=$(/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
print(','.join(str(v) for v in range(1, 13) for _ in range(10)))
PYEOF
)

$PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --every 20 --snap-every 200 --phi-band-every 200 \
  --pair-every 100 --norm-smooth 0 --nthreads 4 --laths "$LATHS" \
  --plate-L 1000 --plate-W 500 --plate-T 510 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack \
  --nuc-law athermal --nuc-init 6 \
  --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 \
  --alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
  --nfsv-diag 1 \
  --steps 4000 --tag r539b5 --out $OUT \
  > _w2_r539_b5.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
$PY -u _r540_b5verdict.py
