#!/usr/bin/env bash
# R498 —— "纯溶解档早退"（`--qs-shrink-cap`）的**A/B 等价性检验**。
#
# ## 背景（**我原来的建议被 `_r497` 推翻了**）
#   `_r496` 我建议"方案 B：钟从 369 K 起步、跳过 20 个纯等待档"。
#   `_r497_stageinert.py` 只读归档数据实测：**档 1 里初始板条溶掉 97.3%**
#   （0.2495 → 0.006836 µm³）⇒ **那些档不是"惰性"，是"纯溶解"** ⇒
#   **跳过它们会让初始板条活下来 ⇒ 末态多一根 ⇒ 不等价。**
#
# ## 正确的优化（本脚本要验的）
#   纯溶解**没有不动点** ⇒ 收敛判据永远不满足 ⇒ 每档都撞 `--qs-max-relax`
#   ⇒ 白烧 20×400 步。**照跑但不必跑到收敛** ⇒ `--qs-shrink-cap N`：
#   若本档 V **连续 N 步单调减少**（纯溶解）就提前降 T。
#
# ## 单变量对照
#   D：`--qs-shrink-cap 0`（参考，= 关闭优化）
#   E：`--qs-shrink-cap 20`（优化）
#   F：`--qs-shrink-cap 1`（**过度激进**，用作**判据的负对照**）
#   其余**逐字相同**（含 `--qs-max-relax 100`、`--T-end 340`、`--nthreads 16`）。
#
# ## 预登记判据（**先写死**）
#   E1【都到终点】D 与 E 的**末温**都必须 == `T_end`（340 K）。
#   E2【确实省了】E 的步数必须 **≤ 0.6 × D 的步数**。
#   E3【末态等价（核心）】D 与 E 的末态必须一致：
#        · 在用场数 `nreg_used` **相同**；
#        · `nslab_n` **相同**（聚合板条数）；
#        · `Vt` 的相对差 **≤ 10%**。
#   E4【负对照：判据必须能失败】F（cap=1）与 D 比，**必须**出现 E3 中至少一项不满足
#        （否则说明 E3 太松、分不出好坏 ⇒ E3 的 PASS 不算数）。
#
# ⚠ 全部小盒子（N=64）；`abA` 仍在跑，会抢核。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=8
STEPS=2600
LATHS="1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6"
COMMON="--N 64 --dx-nm 62.5 --every 10 --snap-every 99999 --phi-band-every 99999 \
 --pair-every 0 --norm-smooth 0 --nthreads $NT --laths $LATHS \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 4 --nuc-fresh-every 4 \
 --alpha-km 0.041739 --T-end 340.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
 --qs-clock 1 --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-max-relax 100 --steps $STEPS --out $OUT"

run_arm () {
  local TAG="$1"; shift
  echo "== 臂 $TAG   $(date '+%F %T')"
  local T0=$(date +%s)
  $PY -u _bk_exp.py $COMMON "$@" --tag "$TAG" > "_w2_r498_${TAG}.log" 2>&1
  echo "臂 $TAG 退出码=$?  用时 $(( $(date +%s) - T0 )) s"
}

run_arm r498D --qs-shrink-cap 0  &
PD=$!
run_arm r498E --qs-shrink-cap 20 &
PE=$!
run_arm r498F --qs-shrink-cap 1  &
PF=$!
wait $PD; wait $PE; wait $PF
echo "三臂结束 $(date '+%F %T')"
echo
$PY -u _r498_shrinkverdict.py
