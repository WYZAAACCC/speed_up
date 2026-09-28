#!/bin/bash
# ★ 重启后的自走驱动（第 2 版）：等 e7/equi192 → 判定 + S-1 → 启动 e7b → S-1
#   ⚠ 第 1 版死在 `_r1_analyze.py` 的 `bfv` NameError 上（已修）+ WSL 服务异常。
#     本版把每一步的输出都写文件，并在每段之间 `set +e`，避免一处失败整条链断掉。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive2.log
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

log "等 e7_selfac / equi192_ns4"
waitfor e7_selfac equi192_ns4
log "两者结束"

log "--- 逐快照分量序列 ---"
$PY -u _r1_snapinfo.py --series _exp/e7_selfac --kv 1 --shape mid >> "$LOG" 2>&1
$PY -u _r1_snapinfo.py --series _exp/equi192_ns4 --kv 1 --shape equi >> "$LOG" 2>&1

log "--- 块/形状判定 ---"
$PY -u _r1_analyze.py _exp/e7_selfac _exp/equi192_ns4 --skip 3 --block >> "$LOG" 2>&1

log "--- S-1 自协调判定（e7 末态，随机对照 24 次）---"
SNAP=$(ls -1 _exp/e7_selfac/snap_*.npz | tail -1)
log "用快照 $SNAP"
$PY -u _r1_selfac.py --snap "$SNAP" --nrand 24 --workers 4 >> "$LOG" 2>&1

log "--- 启动 e7b（全 12 变体随机分配）---"
setsid nohup $PY -u _r1_exp.py --out _exp/e7b_selfac12 --case mid \
    --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 25 \
    --nseed 6 --layout line_w --line-gap-nm 1500 \
    --variants "1,2,3,4,5,6,7,8,9,10,11,12" --shuffle-variants 7 \
    --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
    --reinit-band 6.0 --max-hours 2.6 --norm-smooth 4 \
    > _exp/e7b_selfac12/run.log 2>&1 < /dev/null &
log "e7b pid=$!"

waitfor e7b_selfac12
log "e7b 结束"
SNAP=$(ls -1 _exp/e7b_selfac12/snap_*.npz | tail -1)
$PY -u _r1_selfac.py --snap "$SNAP" --nrand 24 --workers 8 >> "$LOG" 2>&1
log "全部完成"
