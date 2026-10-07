#!/bin/bash
# ★★★ 队列 v6 —— **A-3（惯习面 facet）对照**，插到实验 7 的 `e7d`/`e7b` 之前
#
# 为什么要插队（用户的阶段要求）
# ------------------------------
# 用户明确：**先单个 → 再多核 → 最后块**。
# A-3（单核长出来的板**有没有平坦惯习面**）属于**单个**阶段的形状质量，
# 而 `e7d`/`e7b` 是实验 7（块级自协调）。原队列 v5 却要等 v4 **全部**跑完
# （含 e7d/e7b）才动 A-3 ⇒ **顺序与阶段要求相反**。
# 本队列把 A-3 提前：只要**有 1 个空槽**就开跑，与 `mid192_ns4b` 并行。
#
# 取代关系：**已杀掉 v5**（否则两个队列会重复跑同一对 A-3 臂）。
# 与 v4 的共存：v4 的 `wait_slot` 要求活跃 ≤2 ⇒ 最坏情形是 3 个并发
#   （mid192_ns4b + 1 个 A-3 + 1 个 e7*），实测内存 = 13.7 GB 可用，够。
#
# 依据与证据（见 `R1_PROBLEM_LEDGER.md` A-2/A-3）：
#  * `_r1_exp.py` 的 `KW` **从未传 `facet_lam`** ⇒ 既有算例全走 `aniso=0.4`
#    的普通 Herring（惯习面 1.8γ0 / θ=90° 0.6γ0，仅 3:1，**无奇异面**）。
#  * 引擎早有为 A-3 写的 `herring_stiffness_cusp`；`_r1_stiffunit.py` 已证
#    该分支**生效**（刚度 0.09–0.27 → **0.15–1.35**，4 倍）。
#  * 但端到端 6 步冒烟**看不见**（`stk·κ/Δf`≈0.2%，读数是胞量化的）
#    ⇒ 本队列用**薄板 + 700 步长跑 + `fill_cal`/长时程 aspect** 来测。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive6.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

nactive () { pgrep -c -f '_r1_exp\.py' 2>/dev/null | tr -d '\n'; }

wait_slot () {          # 只要 ≤1 就开（与 mid192_ns4b 并行）
  while true; do
    n=$(nactive); [ -z "$n" ] && n=0
    [ "$n" -le 1 ] && return 0
    sleep 60
  done
}

run () {   # run <名字> <facet-lam>
  local NAME="$1" FL="$2"
  wait_slot
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" --case mid \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 50 \
      --nseed 1 --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
      --norm-smooth 4 --reinit-band 6.0 --max-hours 3.5 \
      --facet-lam "$FL" > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME（facet_lam=$FL, 单核 mid, N=192, 700 步）pid=$!"
}

analyze () {
  local NAME="$1"
  while pgrep -f "_r1_exp.py --out _exp/$NAME" > /dev/null 2>&1; do sleep 60; done
  log "$NAME 结束 —— 自动分析（有效窗口口径）"
  $PY -u _r1_aniso.py "$NAME" >> "$LOG" 2>&1
}

log "==== A-3 对照队列 v6 开始（活跃 _r1_exp = $(nactive)）===="
run a3_facet00 0.0
analyze a3_facet00
run a3_facet04 0.4
analyze a3_facet04
log "==== A-3 对照完成：比较 a3_facet00 vs a3_facet04 的 fill_cal 与长时程 aspect ===="
