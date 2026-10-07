#!/usr/bin/env bash
# R482 —— **任务(2) ③（位点持续可用）的验收**。
#
# ## 病灶（本脚本要证伪的东西）
#   `windowB_surface._nuc_place_initial` 在 t=0 一次撒 `n = --nuc-init` 个位点，
#   而 `nucleate()` 里 `sites.pop(i)` **用过即移除** ⇒ 池子耗尽后
#   `if sites and n_fresh > 0` 直接不成立 ⇒ **再也形不了核**，
#   而 athermal 律 `n(T) = α_KM(M_s − T)` **还在继续要求新核**
#   ⇒ 「**定律要核、池子没有**」的**静默**缺口。
#
# ## 单变量对照（**只差一个开关**）
#   A：`--nuc-sites-refill 0`（归档行为；池子用尽即止）
#   B：`--nuc-sites-refill 1`（见底时按同一分布继续抽）
#   其余**逐字相同**，`--nuc-init 2` 故意给一个**很小的池子** ⇒ 很快见底。
#
# ## 预登记判据（**先写死**）
#   V1【病灶存在（负对照）】A 臂的形核事件数**必须明显少于** `n(T_end)`
#       （即"池子空了就停"确实发生）。若 A 臂也跑到 `n(T_end)` ⇒ **病灶不存在**
#       ⇒ 本任务无必要，必须照实记。
#   V2【修复有效】B 臂的形核事件数**必须 > A 臂**，且达到 `min(n(T_end), nv)` 附近
#       （判据：≥ 0.9 × min(n(T_end), nv)）。
#   V3【对照有效性】两臂的**命令行只差 `--nuc-sites-refill`**（由脚本结构保证）
#       且两臂的 `nv`、`α_KM`、`T_end`、步数**必须相同**。
#   V4【默认路径不变】由 `_r30_regress.sh` 把关（另跑）。
#
# ⚠ 全部小盒子；**不与 abA 抢资源**。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=3
STEPS=1200
# 24 个场、6 个变体、每变体 4 个场 ⇒ 尽量**不要**让 `nfsv_nofield` 先成为瓶颈，
# 这样测到的差别才归因于**位点池**。
LATHS="1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6"
COMMON="--N 64 --dx-nm 62.5 --every 20 --snap-every 99999 --phi-band-every 99999 \
 --pair-every 0 --norm-smooth 0 --nthreads $NT --laths $LATHS \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 2 --nuc-fresh-every 4 \
 --alpha-km 0.041739 --T-end 298.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
 --steps $STEPS --out $OUT"

run_arm () {
  local TAG="$1" REF="$2"
  echo "=============================================================="
  echo "== 臂 $TAG  (--nuc-sites-refill $REF)   $(date '+%F %T')"
  echo "=============================================================="
  $PY -u _bk_exp.py $COMMON --nuc-sites-refill "$REF" --tag "$TAG" \
      > "_w2_r482_${TAG}.log" 2>&1
  echo "臂 $TAG 退出码=$?  $(date '+%F %T')"
}

run_arm r482A 0 &
PA=$!
run_arm r482B 1 &
PB=$!
wait $PA; RA=$?
wait $PB; RB=$?
echo "两臂结束：A=$RA B=$RB  $(date '+%F %T')"
echo
echo "== 判决 =="
$PY -u _r482_refillverdict.py
