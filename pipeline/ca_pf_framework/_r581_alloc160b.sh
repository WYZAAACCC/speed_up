#!/bin/bash
# _r581_alloc160b.sh --- ★★★★★★★ **A4 判决实验（安全版）**：N=160、**一次只跑一臂**、带**进程级硬闸**
#
# ## 为什么重跑（R185 的教训）
# 上一版三臂串行**没做错**，但它与 `BK6`/`BK7` 并发 ⇒ 加上 `TUNED` 自己的 **16.9 GB**
# ⇒ `available` 掉到 **411 MB**、swap 6.6 GB ⇒ **必须停**。
# **⇒ 本版：① 现在 `BK6`/`BK7` **已完成** ⇒ 机器 23 GB 全空；② 加**进程级 RSS 硬闸**：
#   **某臂 RSS > 19 GB 立即杀它并记账**（**不等系统级看门狗**，P39）。
#
# ## 设计（**单变量：只差 MALLOC 环境变量**）
# | 臂 | MMAP_THRESHOLD | TRIM_THRESHOLD | ARENA_MAX | 角色 |
# |---|---|---|---|---|
# | **TUNED** | 65536 | 65536 | 2 | **= 仓库 134 个脚本的现状** |
# | **★ ARENA** | — | — | **2** | **★ 用户要采用的** |
# | **PLAIN** | — | — | — | 参考 |
#
# ## 判据（与 R184 写死的**同一条**）
# | 观察 | 判决 |
# |---|---|
# | **ARENA 峰值 ≤ TUNED × 1.05** | **✅ 安全 ⇒ 改那 124 个脚本** |
# | **1.05–1.10×** | **⚠ 边缘 ⇒ 带余量再改 + 记账** |
# | **> 1.10×** | **❌ 危险区 ⇒ 不改，回来请示** |
# | **TUNED/ARENA 步速 ≥ 1.3×** | **✅ 收益复现** |
# | **< 1.05×** | **❌ N=160 上无收益 ⇒ 不改** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_alloc160"
LOG=_w2_r581_alloc160b.log
RSS_HARD_MB=19000          # ★ 进程级硬闸
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

BASE="--N 160 --dx-nm 62.5 --steps 30 --every 5 --snap-every 30 --pair-every 50 \
 --norm-smooth 0 --phi-band-every 200 --eng-cadence 30 --nthreads 4 \
 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 \
 --reinit-band 6.0 --nuc-overlap-nm 62.5 --eps0-mode einsum --ed-pair gather \
 --k-loop act --act-mode bincount --argmin2-mode copyto --grad-mode sliced \
 --pf-phi onfly --h-chunk 4 --extend-mode near --eps0-tile 4 \
 --argmin2-reuse 1 --ufv-c 1 --bbox-mode axis"
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

# ★ 进程级硬闸：后台每 10 s 查一次，超阈就杀
guard() {  # $1=tag
  local tag="$1"
  while pgrep -f "_bk_exp.py.*--tag $tag" >/dev/null 2>&1; do
    for p in $(pgrep -f "_bk_exp.py.*--tag $tag" 2>/dev/null); do
      r=$(awk '/VmRSS/{printf "%d", $2/1024}' "/proc/$p/status" 2>/dev/null)
      if [ -n "${r:-}" ] && [ "$r" -gt "$RSS_HARD_MB" ]; then
        echo "[$(date '+%F %T')] 🚨 **RSS 硬闸**：$tag pid=$p RSS=${r}MB > ${RSS_HARD_MB}MB ⇒ **杀它**" | tee -a "$LOG"
        kill -9 "$p" 2>/dev/null
      fi
    done
    sleep 10
  done
}

run() {  # $1=tag $2=mode
  local tag="$1" mode="$2" avail
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  say "起 $tag（$mode）；available=${avail} MB；硬闸 ${RSS_HARD_MB} MB"
  if [ "$avail" -lt 16000 ]; then
    say "  ⚠ available < 16 GB ⇒ **跳过 $tag**（不许硬上）"
    return 3
  fi
  local t0 t1
  t0=$(date +%s)
  guard "$tag" &
  local gpid=$!
  case "$mode" in
    TUNED) MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160b_${tag}.log" 2> "_w2_r581_alloc160b_${tag}.time" ;;
    ARENA) MALLOC_ARENA_MAX=2 \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160b_${tag}.log" 2> "_w2_r581_alloc160b_${tag}.time" ;;
    *)     env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
             /usr/bin/time -v taskset -c 0-7 $PY -u _bk_exp.py $BASE \
             --out "$ROOT" --tag "$tag" --laths "$laths" > "_w2_r581_alloc160b_${tag}.log" 2> "_w2_r581_alloc160b_${tag}.time" ;;
  esac
  local rc=$?
  t1=$(date +%s)
  kill "$gpid" 2>/dev/null
  say "  $tag 结束：exit=$rc，墙钟 $((t1-t0)) s，Traceback=$(grep -c '^Traceback' "_w2_r581_alloc160b_${tag}.log" 2>/dev/null || echo 0)"
  sleep 8
}

say "=== R581-R185c：A4 判决实验（安全版，一次一臂，硬闸 ${RSS_HARD_MB} MB）==="
run TUNED TUNED
run ARENA ARENA
run PLAIN PLAIN
say "=== 三臂跑完；判决见本脚本尾部（下次读）==="
say ">>> 读法：python _r581_ab160b_read.py"
