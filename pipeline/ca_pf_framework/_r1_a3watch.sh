#!/bin/bash
# _r1_a3watch.sh --- 等 A-3 两个臂**先启动、再结束**，然后自动出**配对**判决
#
# ⚠ 记账（本脚本第一版的 bug）：原来的等待循环是
#     `while pgrep -f "...--out _exp/$d" >/dev/null; do sleep 120; done`
#   但 `$d` **还没启动**时 `pgrep` 也返回非零 ⇒ 循环**立刻退出**、直接宣布"结束"
#   ⇒ 在**空数据**上跑分析（实测两臂都报"✗ 无数据"）。
#   根因：**没区分"还没开始"与"已经结束"**。
#   ⇒ 修法：先 `wait_start`（等进程出现**或** `series.csv` 出现），再 `wait_end`。
#
# 另：`_r1_c5chk.py` **不接受命令行臂名**（它跑内置 ARMS 列表）⇒ 这里改为
#     跑它并用 grep 把两臂的行筛出来。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1a3watch.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

A=a3_facet00
B=a3_facet04

running () { pgrep -f "_r1_exp.py --out _exp/$1" > /dev/null 2>&1; }

wait_start () {   # 等它**开始**：进程出现，或 series.csv 出现
  local n=0
  while true; do
    if running "$1" || [ -f "_exp/$1/series.csv" ]; then return 0; fi
    n=$((n + 1))
    if [ $((n % 30)) = 0 ]; then log "  …仍在等 $1 启动（已等 $((n/2)) 分钟）"; fi
    sleep 120
  done
}

wait_end () {     # 等它**结束**（此时肯定已经启动过）
  while running "$1"; do sleep 120; done
}

for d in "$A" "$B"; do
  log "等 $d **启动**……"
  wait_start "$d"
  log "$d 已启动，等它结束……"
  wait_end "$d"
  log "$d 结束"
done

log "==== A-3 配对判决 ===="
log "--- (1) 配对的 ΔW:ΔL 漂移曲线（0.4 若漂移更小 ⇒ 尖点界面能在起作用）---"
$PY -u _r1_dxcurve.py "$A" "$B" >> "$LOG" 2>&1
log "--- (2) 两臂 fill_cal 轨迹（0.4 若更高 ⇒ 出现平坦惯习面）---"
$PY -u _r1_c5chk.py 2>&1 | grep -E "臂|$A|$B|参考值" >> "$LOG"
log "--- (3) 逐臂有效窗口读数 ---"
$PY -u _r1_aniso.py "$A" "$B" >> "$LOG" 2>&1
log "==== 完成。判读：① aspect 漂移是否变小；② fill_cal 是否抬高 ===="
