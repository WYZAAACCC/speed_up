#!/usr/bin/env bash
# R535 —— **N11 取证跑**：`nfsv_nofield` 到底是"场不够"还是"碎点占场"？
#
# ## 为什么要这一跑
# `nfsv_nofield` 让 40 次形核尝试里 21–22 次被拒（P2/P3 FAIL，见 `R525 §4）。
# 我已有一个假设（**变体碰撞、场不够**）被自己的 A/B **否掉**：
#   `--laths 12×6=72` ⇒ `nfsv_nofield = 22`
#   `--laths 12×10=120`（`nv` **+67%**）⇒ `nfsv_nofield = 21`
# ⇒ **不再猜**：打开 `--nfsv-diag 1`，在**拒绝现场**记录
#   同变体场总数 / 其中被判非空的个数 / 那些场的**胞数分布** / 全盒非空场总数。
#
# ## 配置相对 `_r529_paramrun2.sh` 的三处差异（**必须逐条记账**）
# | # | 项 | `_r529` | 本跑 | 会不会影响物理？ |
# |---|---|---|---|---|
# | ① | `--nfsv-diag` | 无（=0） | **1** | **不会** —— 只在**拒绝路径**上多算诊断，**不碰任何判据** |
# | ② | `--pair-every` | 100 | **0** | **不会** —— 只决定**要不要算块列**（`_bk_exp.py:271`），不参与求解 |
# | ③ | `--nthreads` | 16 | **4** | **不会** —— `R531_THREADSCALE.md §4` **实测逐位相同**（`Vt` 相对差 `0.000e+00`） |
# ⇒ **三条都只碰"测量/调度"，不碰物理** ⇒ **正对照**：本跑的 `nfsv_nofield`
#   与末态 `Vt` 应当与 `_r529` **一致**（`_r536_diagread.py` 的 C1 就是查这个）。
# ⚠ 第一版我在文件头写的是"与 `_r529` 逐字相同，只加 `--nfsv-diag 1`" —— **那句话不准确**
#   （还差 ②③ 两处）。**照实改过来**，并把"为什么 ②③ 不影响物理"写清。
#   这正是本仓 §3.3 教训 21 那条：**"隔离是否成立"要看"只差这一个差异"**。
#
# `--nthreads 4`：按 `R531_THREADSCALE.md` 实测（真实负载上 4 线程比 16 线程**快 12%**）。
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
  --pair-every 0 --norm-smooth 0 --nthreads 4 --laths "$LATHS" \
  --plate-L 1000 --plate-W 500 --plate-T 510 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack \
  --nuc-law athermal --nuc-init 6 \
  --nuc-block-target 8 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 \
  --alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
  --nfsv-diag 1 \
  --steps 4000 --tag r535diag --out $OUT \
  > _w2_r535_diag.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
$PY -u _r536_diagread.py
