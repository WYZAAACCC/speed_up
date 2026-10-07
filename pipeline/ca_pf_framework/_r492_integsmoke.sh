#!/usr/bin/env bash
# R492 —— **三个新开关的集成冒烟**（任务(2) ①②③ 第一次**一起**跑）。
#
# ## 为什么必须做这一步
#   `--qs-clock`（①）、`--nuc-supercrit`（②）、`--nuc-sites-refill`（③）
#   **各自**都过了自己的验收（`_r478` / `_r479` / `_r484`），
#   但**从来没有一起跑过**。集成缺陷（例：②在 `nucleate()` 里调 `elastic_driving()`，
#   而①正把 T 钉住）只有在真跑里才暴露。**在起任务(5) 的大算例之前必须先过这一关。**
#
# ## 预登记判据（**先写死**）
#   I1【不崩】日志里**不得**有 `Traceback` / `Error`；CSV 行数 > 0。
#   I2【钟在走】日志里必须出现 `[qs] 档` 行 ⇒ 温度档确实在推进。
#   I3【形核真的发生】日志里必须出现 `引擎形核` 行（③的补货在真跑里生效）。
#   I4【t_s 由温度定】CSV 的 `t_s` 单调，且 `t_s·q` ≤ `T_start − T_end`。
#   I5【负对照】把三个开关全关跑同一配置 ⇒ **不得**出现 `[qs] 档`（证明读数不是噪声）。
#   I6【多核】两臂都用 `--nthreads 16`（顺带验证 R488 的结论在真跑里成立）。
#
# ⚠ 短跑：只求"集成能不能跑通"，不求物理结论。**不产生任何物理判据。**
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=16
STEPS=700
LATHS="1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6"
COMMON="--N 64 --dx-nm 62.5 --every 20 --snap-every 99999 --phi-band-every 99999 \
 --pair-every 0 --norm-smooth 0 --nthreads $NT --laths $LATHS \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 4 --nuc-fresh-every 4 \
 --alpha-km 0.041739 --T-end 298.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
 --steps $STEPS --out $OUT"

run_arm () {
  local TAG="$1"; shift
  echo "=============================================================="
  echo "== 臂 $TAG   $(date '+%F %T')"
  echo "=============================================================="
  local T0=$(date +%s)
  $PY -u _bk_exp.py $COMMON "$@" --tag "$TAG" > "_w2_r492_${TAG}.log" 2>&1
  local RC=$?
  local T1=$(date +%s)
  echo "臂 $TAG 退出码=$RC  用时 $((T1-T0)) s"
}

# A：三个开关全开
run_arm r492on  --qs-clock 1 --nuc-supercrit 1 --nuc-sites-refill 1 &
PA=$!
# C：三个开关全关（负对照）
run_arm r492off &
PC=$!
wait $PA; RA=$?
wait $PC; RC=$?
echo "两臂结束：on=$RA  off=$RC   $(date '+%F %T')"
echo
echo "== 判决 =="
$PY -u _r492_integverdict.py
