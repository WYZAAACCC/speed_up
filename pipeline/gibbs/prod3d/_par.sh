#!/bin/bash
# =============================================================================
# 并行跑多个**互不干扰**的算例，把 CPU 吃满（用户要求：机器经常没跑满）
# =============================================================================
# 每个算例：独立目录 /root/work/<name>、独立 .jitcache、独立 run.log ⇒ 互不干扰。
# 用法：
#   bash _par.sh <listfile>
#   listfile 每行：  <name>|<input 的绝对路径>|<CLI 参数（可空）>
# 说明：
#   · 每个进程是**单线程 MPI**（1 rank），所以并发数 ≈ 核数就能吃满；
#     本机 20 核 ⇒ 建议 ≤ 8~10 个并发（给别的活留余量，且内存每个 ~0.7 GB）。
#   · 跑完自动把 run.log / case_out.csv / profile CSV 拉回 F 盘。
#   · 结束后打印每个算例的 rc / 收敛 / 未收敛计数。
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

LIST=${1:?需要 list 文件}
MAXJOB=${MAXJOB:-8}
WALL=${WALL:-2400}
BIN=${BIN:-/root/projects/gibbs/gibbs-opt}
DEST_ROOT=/mnt/f/speed_up/pipeline/gibbs/prod3d
SEED=/root/work/jitcache_seed

launch_one() {
  IFS='|' read -r name input args <<< "$1"
  R="/root/work/par_$name"
  rm -rf "$R"; mkdir -p "$R"; cd "$R" || return 1
  sed 's/\r$//' "$input" > case.i
  grep -q 'columnar_seeds.csv' case.i 2>/dev/null && \
    cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv . 2>/dev/null
  # ★ 关键：每个算例**独立**的 JIT 缓存哈希，避免并发互相踩
  cp -r "$SEED/." .jitcache/ 2>/dev/null || true
  echo "[$name] 开跑：$R"
  timeout "$WALL" "$BIN" -i case.i $args -w > run.log 2>&1
  RC=$?
  mkdir -p "$DEST_ROOT/results_par_$name"
  cp -f run.log case.i "$DEST_ROOT/results_par_$name/" 2>/dev/null
  cp -f case_out.csv case_out_profile_*.csv "$DEST_ROOT/results_par_$name/" 2>/dev/null
  echo "[$name] rc=$RC  converged=$(grep -c 'Solve Converged' run.log)  didnot=$(grep -c 'Did NOT' run.log)"
}

export -f launch_one
export WALL BIN SEED DEST_ROOT

N=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in \#*) continue;; esac
  launch_one "$line" &
  N=$((N+1))
  while [ "$(jobs -rp | wc -l)" -ge "$MAXJOB" ]; do sleep 5; done
done < "$LIST"
wait
echo "=== 全部完成（$N 个） ==="
