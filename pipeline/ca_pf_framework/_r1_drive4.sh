#!/bin/bash
# ★★★ 统一队列 v4 —— 取代 `_r1_drive3.sh`（**必须杀掉旧的，否则两个队列会同时抢槽位 → OOM**）
#
# 优先级依据（本轮新证据）
# ------------------------
# 1. **实验 3 必须重做**（`R1_PROBLEM_LEDGER.md` B-1c）：
#    现有 `mid192_ns4` 止于 step 180、**无任何结束/报错字样**（外部杀死 = 那次 WSL 崩溃），
#    且 step 124/140/176/180 打出 `⚠G-2分量2`（4 步被碎片绑架）。
#    更关键：速率比**随窗口漂移**（B-1b，`mid250_ns4` 的 `ΔW:ΔL` 漂 56%），
#    而现有算例**停在漂移未停的瞬态段** ⇒ 实验 3 的 PASS 不成立。
#    ⇒ `mid192_ns4b`（R24 标准单核、跑到 700 步、`--every 5` 多存点）**最高优先**。
# 2. 然后才是实验 7 的自协调臂，按 `E_min`（模型自己的配对能量）排序：
#    `e7c`(V5–V6, 4.19e-4 最相容) → `e7d`(V3–V4, 2.32e-3) → `e7b`(全 12 变体)。
#
# 槽位纪律
# --------
# WSL 只有 ~22 GB 可用，一个 N=192 进程峰值 4–8 GB ⇒ **最多 3 个并发**。
# 本队列串行执行，且每次启动前都等到**活跃 `_r1_exp.py` ≤ 2**。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive4.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

nactive () { pgrep -c -f '_r1_exp\.py' 2>/dev/null | tr -d '\n'; }

wait_slot () {          # 等到活跃算例 ≤ 2（留一个槽给它自己）
  while true; do
    n=$(nactive); [ -z "$n" ] && n=0
    [ "$n" -le 2 ] && return 0
    sleep 60
  done
}

waitfor () {
  while true; do
    n=0
    for d in "$@"; do
      c=$(pgrep -c -f "_r1_exp.py --out _exp/$d" 2>/dev/null)
      [ -z "$c" ] && c=0
      n=$((n + c))
    done
    [ "$n" = "0" ] && return 0
    sleep 60
  done
}

# run <名字> <额外参数...>
run () {
  local NAME="$1"; shift
  wait_slot
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 50 \
      --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
      --norm-smooth 4 --max-hours 3.5 \
      "$@" > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME ：$* （pid=$!）"
}

analyze () {            # 跑完后自动出**窗口分辨**的各向异性读数
  local NAME="$1"
  waitfor "$NAME"
  log "$NAME 结束 —— 自动分析"
  $PY -u _r1_aniso.py "$NAME" >> "$LOG" 2>&1
}

s1 () {                 # 自协调臂：跑完出 S-1
  local NAME="$1"
  waitfor "$NAME"
  log "$NAME 结束"
  local SNAP
  SNAP=$(ls -1 "_exp/$NAME"/snap_*.npz 2>/dev/null | tail -1)
  if [ -n "$SNAP" ]; then
    log "--- S-1 判定（$NAME，$SNAP）---"
    $PY -u _r1_selfac.py --snap "$SNAP" --nrand 24 --workers 4 >> "$LOG" 2>&1
  else
    log "⚠ $NAME 没有快照，跳过 S-1"
  fi
}

log "==== 队列 v4 开始（活跃 _r1_exp = $(nactive)）===="

# ① 实验 3 重做：单核 `mid`，R24 标准（种子×1 = 与既有 mid192_ns4 同配置），跑到 700 步
run mid192_ns4b --case mid
analyze mid192_ns4b
log "--- 实验 3 重做完成，下一步：实验 7 自协调臂 ---"

# ② 实验 7 自协调臂（按 E_min 从最相容到补充）
run e7c_badpair --case mid --nseed 6 --layout line_w --line-gap-nm 1500 \
    --variants 5,6 --shuffle-variants 1
s1  e7c_badpair
run e7d_pair34  --case mid --nseed 6 --layout line_w --line-gap-nm 1500 \
    --variants 3,4 --shuffle-variants 1
s1  e7d_pair34
log "--- 启动 e7b（全 12 变体随机分配）---"
run e7b_selfac12 --case mid --nseed 6 --layout line_w --line-gap-nm 1500 \
    --variants 1,2,3,4,5,6,7,8,9,10,11,12 --shuffle-variants 7
s1  e7b_selfac12
log "==== 队列 v4 全部完成 ===="
