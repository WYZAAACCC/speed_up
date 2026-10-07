#!/bin/bash
# _r1_drive9.sh --- 队列 v4 的**修正版**：实验 7 的臂必须显式给 `--kv`
#
# 依据（本轮抓到的真 bug）
# ----------------------
# `_r1_exp.py:425` 的 `--kv` **默认 1**，而 `:515` 是 `K0 = a.kv`，
# `K0` 就是 `measure(g, K0, ...)` 与种子定标所测的**目标变体**。
# 但 v4 里 `e7c`（`--variants 5,6`）与 `e7d`（`--variants 3,4`）**没给 `--kv`**
#   ⇒ `K0 = 1` ⇒ **变体 1 从未被播种** ⇒ 实测 `胞=0`、`L/W/T` 全 **nan**。
# 实测证据（`_exp/e7c_badpair/log.txt`）：
#   「变体序列 [5, 6, 6, 6, 5, 5]」但「种子实测 … **胞=0**」且轴那一行印的是「变体 V1」。
# 影响面：
#   * **受影响**：`e7c_badpair`（变体 5,6）、`e7d_pair34`（变体 3,4）
#     ⇒ 几何/`fill_cal`/各向异性**全部作废**（NaN）；
#   * **不受影响**：`e7_selfac`（变体 1,2 —— 恰好含 1）、`e7b_selfac12`（全 12 个）；
#   * ✅ **快照 `region` 不受影响** ⇒ **S-1（e7c 的首要用途，量具的负对照）照常成立**。
# 修法：`e7c` 用 `--kv 5`、`e7d` 用 `--kv 3`（取该臂**第一个**变体即可，两者对称）。
#
# 取代关系：**杀掉 v4**（它会在 e7c 跑完后以同样缺 `--kv` 的方式跑 e7d）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive9.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

nactive () { pgrep -c -f '_r1_exp\.py' 2>/dev/null | tr -d '\n'; }
wait_slot () {
  while true; do
    n=$(nactive); [ -z "$n" ] && n=0
    [ "$n" -le 1 ] && return 0
    sleep 60
  done
}

run () {   # run <名字> <kv> <variants> <shuffle>
  local NAME="$1" KV="$2" VAR="$3" SH="$4"
  wait_slot
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" --case mid \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 25 \
      --nseed 6 --layout line_w --line-gap-nm 1500 \
      --variants "$VAR" --shuffle-variants "$SH" --kv "$KV" \
      --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
      --norm-smooth 4 --reinit-band 6.0 --max-hours 2.6 \
      > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME（kv=$KV, variants=$VAR, shuffle=$SH）pid=$!"
}

s1 () {    # 跑完出 S-1（会自动改道到修正量具 `_r1_selfac2.py`）
  local NAME="$1"
  while pgrep -f "_r1_exp.py --out _exp/$NAME" > /dev/null 2>&1; do sleep 120; done
  log "$NAME 结束"
  local SNAP
  SNAP=$(ls -1 "_exp/$NAME"/snap_*.npz 2>/dev/null | tail -1)
  if [ -n "$SNAP" ]; then
    log "--- S-1 判定（$NAME，$SNAP）---"
    $PY -u _r1_selfac.py --snap "$SNAP" --N 192 --nrand 24 --workers 4 >> "$LOG" 2>&1
  else
    log "⚠ $NAME 没有快照，跳过 S-1"
  fi
}

log "==== 实验 7 队列 v9（修正 `--kv`）开始，活跃 _r1_exp = $(nactive) ===="
run e7c_badpair 5 "5,6" 1
s1  e7c_badpair
run e7d_pair34  3 "3,4" 1
s1  e7d_pair34
run e7b_selfac12 1 "1,2,3,4,5,6,7,8,9,10,11,12" 7
s1  e7b_selfac12
log "==== 实验 7 队列 v9 全部完成 ===="
