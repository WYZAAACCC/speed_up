#!/bin/bash
# _r1_drive8.sh --- 取代 v7：**A-3 基线臂重做（修复 nhist 后）** + m/Δx 分离补算
#
# 为什么必须重做 `a3_facet00`（台账 A-1b 的修 bug 记录）
# -----------------------------------------------------
# 我给快照加的 `nhist` 第一版选带条件写成 `|∇φ| > 0.2`，而 `phi` 是**符号距离函数**
# ⇒ `|∇φ| ≈ 1` **在整个域上都成立** ⇒ 选中的是 **95% 的盒子**（实测 6.71e6/7.08e6）
# ⇒ 直方图统计的是"**扩展场的梯度方向**"，**不是界面法向**。
# 已改成 `|phi| < 1.5·Δx` 并验证：带内胞数 **0.38%**、分布呈应有的双峰。
# 但 `a3_facet00` 是在修复**之前**启动的 ⇒ 它的 `nhist` **全部无效**
# ⇒ **A-3 的 facet 判决要求两臂同版本** ⇒ 基线臂必须重做。
# （`a3_facet04` 是修复**之后**启动的 ⇒ 正常；A-3 的几何/`fill_cal` 产出不受影响。）
#
# 顺序：先 A-3 基线重做（在目标实验的关键路径上），再 m/Δx 分离补算
# -----------------------------------------------------------------
# 两者都在 v6 退出后串行跑；**不并发**（实测 3 个 N=192 并发会把 swap 推到 ~78%、
# 进程进 `D` 状态 ⇒ 近似卡死）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive8.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "等 v6（A-3 两臂）退出……"
while pgrep -f 'bash _r1_drive6\.sh' > /dev/null 2>&1; do sleep 120; done
log "v6 已退出（活跃 _r1_exp = $(pgrep -c -f '_r1_exp\.py' 2>/dev/null)）"

run_and_wait () {   # run_and_wait <名字> <额外参数...>
  local NAME="$1"; shift
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" --case mid \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 50 \
      --nseed 1 --beta-h 3.5 --beta-w 2.3 --adv proj2 --nthreads 4 \
      --norm-smooth 4 --reinit-band 6.0 --max-hours 3.5 \
      "$@" > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME ：$* （pid=$!）"
  while pgrep -f "_r1_exp.py --out _exp/$NAME" > /dev/null 2>&1; do sleep 120; done
  log "$NAME 结束"
  $PY -u _r1_aniso.py "$NAME" >> "$LOG" 2>&1
}

# ① A-3 基线臂重做（修复 nhist 后）—— 与已跑完的 a3_facet04 同版本、可比
run_and_wait a3_facet00 --facet-lam 0.0

# ② A-3 两臂都齐了 ⇒ 立刻出 facet 判决 + 单变量审计
log "---- A-3 facet 判决（修复版）----"
$PY -u _r1_facetjudge.py a3_facet00 a3_facet04 >> "$LOG" 2>&1
$PY -u _r1_a3meta.py a3_facet00 a3_facet04 >> "$LOG" 2>&1

# ③ m/Δx 分离补算（原 v7 的任务）
run_and_wait m125_s2_ns0 --seed-scale 2 --norm-smooth 0
run_and_wait m125_s2_ns2 --seed-scale 2 --norm-smooth 2
log "==== 全部完成：A-3 facet 判决 + m/Δx 三点分离 ===="
