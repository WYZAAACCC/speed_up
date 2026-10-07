#!/bin/bash
# _r143_threads.sh —— **`advance` 多核并行的正确性 + 加速比**（目标第 (1) 项明确要求）。
#
# ## 判据
# **T-1 逐位一致**：`--nthreads 1 / 2 / 4 / 8` 的 `series.csv` 必须**逐位相同**
#   （除 `wall_s` 这类纯计时列）。
#   ⇒ 这是本仓库对"并行不改变物理"的一贯判据（`windowB_par.ParCtx` 的 docstring 也这么声称）。
# **T-2 加速比**：报实测 `wall_s` 中位数之比（只作**参考**，本机是 DRAM 瓶颈）。
#
# ## 为什么要重验（目标原文）
# 「**advance 有没有正确多核并行**」——本会话此前**没有**独立复核过这一条；
# 而 R143 之前的所有算例用的都是 `--nthreads 2/3/4`，若并行改变了数值，
# 那么**所有**结果都要打折。⇒ 必须**逐位**验，不能只看"看起来对"。
#
# 配置：N=64（小盒、便宜）、`--laths 1,1,1`、20 步、`--pair-every 20`、
#       **`--facet-proj 5`**（顺带把**投影路径**也纳入并行的覆盖面），`--reinit-dt 1e-4`。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

run() {   # run <nt>
  local NT="$1"
  rm -rf "_exp/_bk_thr/dry_t${NT}"
  $PY -u _bk_exp.py --arm dry --N 64 --dx-nm 62.5 \
    --plate-L 1200 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
    --laths 1,1,1 --gap-nm 0 \
    --facet-proj 5 \
    --steps 20 --every 5 --snap-every 20 --pair-every 5 \
    --nthreads "$NT" --tag "t${NT}" --out _exp/_bk_thr > "_w2_r143_t${NT}.log" 2>&1
  echo "  done nt=$NT rc=$?"
}

echo "=== R143 线程数逐位测试开始 $(date '+%F %T')"
# **串行**跑，避免相互争 DRAM 影响 wall_s 的可比性（正确性不受影响，但计时会）
run 1
run 2
run 4
run 8
echo "=== R143 结束 $(date '+%F %T')"
