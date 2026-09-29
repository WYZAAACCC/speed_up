#!/bin/bash
# ★★★ 实验 7 的**自协调臂队列 v3** —— 按 `E_min`（模型自己的配对能量）**重排优先级**
#
# 依据（第 24 轮，`_r1_pairemin.py`）：
#   同 packet 的 6 对按**模型真正最小化的量** `E_min(ncmp)`：
#     V5–V6  4.19e-4  ← **最相容**
#     V3–V4  2.32e-3
#     V9–V10 3.58e-3
#     V7–V8  3.94e-3
#     V11–V12 5.95e-3
#     V1–V2  1.63e-2  ← **最不相容**
#   ⇒ 正在跑的 `e7`（V1–V2）是**失配最大**的一对 ⇒ 弹性能会**惩罚它们共存**
#     ⇒ 它很可能**看不到**自协调。而 **`e7c`（V5–V6）才是最该先跑的那一只**。
#   ⇒ 本队列把 **`e7c` 提到 `e7b` 之前**。
#
# ⚠ 不重跑 `e7`（已在跑，且它是"高失配"的对照臂，本身有价值）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive3.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

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

run () {   # run <名字> <variants> <shuffle-seed>
  local NAME="$1" VAR="$2" SEED="$3"
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" --case mid \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 25 \
      --nseed 6 --layout line_w --line-gap-nm 1500 \
      --variants "$VAR" --shuffle-variants "$SEED" \
      --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
      --reinit-band 6.0 --max-hours 2.6 --norm-smooth 4 \
      > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME（variants=$VAR, seed=$SEED）pid=$!"
}

s1 () {   # s1 <名字>  —— 跑完出 S-1
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

log "等 e7_selfac / equi192_ns4 结束（释放槽位）"
waitfor e7_selfac equi192_ns4
log "槽位已释放"

# ★ 顺序（按 E_min 从"最该看"到"补充"）：
run e7c_badpair "5,6" 1                    # 最相容对（V5–V6）—— **优先**
s1  e7c_badpair
run e7d_pair34  "3,4" 1                    # 次相容（V3–V4）
s1  e7d_pair34
log "--- 启动 e7b（全 12 变体随机分配，packet 混合）---"
run e7b_selfac12 "1,2,3,4,5,6,7,8,9,10,11,12" 7
s1  e7b_selfac12
log "全部完成"
