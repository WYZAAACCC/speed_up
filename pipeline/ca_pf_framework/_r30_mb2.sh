#!/bin/bash
# _r30_mb2.sh —— ★ R31/R33 **MB-2 / MB-3 自协调变体选择实验**（目标第 (2) 项，P-SA-1）
#
# 物理问题（`BLOCK_SELFAC.md §7.1`）：
#   引擎在**新核选变体**时用 `argmax_k ed[k]`（弹性能变化最小，Du 2017）。
#   这个规则**会不会**把组织导向**自协调**的变体组合？
#
# 两臂（配对：**唯一差别是变体选择规则**）：
#   mb2 = `--var-rule ed`     （弹性驱动选择）
#   mb3 = `--var-rule random` （均匀随机）—— 负对照
#
# 装置：`--laths 1,1,2,2,3,3,4,4,5,5,6,6` = 12 个场 = **6 变体 × 2 场**
#   * t=0 只播第 1 片（变体 1）；
#   * 之后每次 `--eng-cadence 60` 步，引擎从 `--nuc-init 30` 个随机位点里
#     激活一个核 —— 或走 `fresh`（按 `--var-rule` **选变体**），
#     或走 `stack`（同变体、新场）。两条通道都开着。
#   * `along_per_variant` 由驱动在 `--nuc-init>0` 时**自动打开**
#     ⇒ 新核按**该场自己的长轴**播长条（P1-17 的修复）。
#
# 判据（预先登记，跑之前就定；由 `_r30_mbverdict.py --mode selfac` 判）：
#   P-SA-1a 两臂末态 **`r_selfac`**：ed 臂应**显著低于** random 臂
#   P-SA-1b 两臂末态 **`E_el_J`**：ed 臂应更低
#   P-SA-1c `n_var_sig` 与 `n_habit`：ed 臂的**变体数**应更少（更集中）
#   ⚠ 三条都是**双向**的：ed 臂若**不**更低/更少 ⇒ P-SA-1 被否证，如实写。
#   ⚠ 必须在**同一 f 区间**上比（两臂的核数由同一 `eng-cadence` 决定 ⇒ 可比）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

COMMON="--arm eng --N 96 --dx-nm 125 \
  --laths 1,1,2,2,3,3,4,4,5,5,6,6 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --eng-r-nm 320 --eng-t-nm 510 --eng-elong 3.0 --nuc-overlap-nm 0 \
  --eng-cadence 60 --nuc-init 30 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 900 --every 20 --snap-every 100 --pair-every 20 --nthreads 3"

"$PY" -u _bk_exp.py $COMMON --var-rule ed --tag mb2 --out _exp/_bk_mb > _w2_r31_mb2.log 2>&1 &
P1=$!
"$PY" -u _bk_exp.py $COMMON --var-rule random --tag mb3 --out _exp/_bk_mb > _w2_r31_mb3.log 2>&1 &
P2=$!
echo "已启动：mb2(ed) pid=$P1   mb3(random) pid=$P2"
wait $P1; echo "mb2 结束 rc=$?"
wait $P2; echo "mb3 结束 rc=$?"
echo "=== R31 MB-2/MB-3 DONE $(date '+%F %T') ==="
