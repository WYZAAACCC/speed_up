#!/bin/bash
# _r1_drive7.sh --- 队列 v7：**把 m 效应与 Δx 效应分开**所需的最小补算（2 个）
#
# 依据（台账 B-1f / B-1g）
# ----------------------
# B-1f 已确立 `norm_smooth=4` 与 Δx 耦合（干净对照 8.72σ；漂移曲线配对 z=+21.4），
# 但**机制未查明**：已排除"平滑长度标度"假说（匹配对反而差得更大、符号相反）。
# 想把 **m 效应** 与 **Δx 效应** 分开，需要"固定 Δx 下的 m-扫描"：
#   * Δx=250 的 m 家族**完整**（seed×2）：m=0/1/2/4 ⇒ ΔW:ΔL = 0.617/0.307/0.167/0.112
#   * Δx=125 的 m 家族**不可用**：`mid192_ns1` 无 meta、`mid192_ns2` 仅 12 行、
#     `mid192_ns4` 被外部杀死（止于 step 172）
# ⇒ **补 2 个即可**（m=4 已有 = `mid192_s2_ns4`）：
#     本队列跑 Δx=125 + seed_scale=2 + N=192 的 **m=0** 与 **m=2**
# ⇒ 三点（m=0/2/4，同为 seed×2）即可判断两条 m-趋势线**平行**（Δx 是纯偏移）
#   还是**发散**（两效应耦合）。
#
# 判读口径（预先写死）
# ------------------
#   记 Δx=250 的 m-趋势为 A(m)、Δx=125 的为 B(m)（均为 seed×2）。
#   ① B(0)/A(0) ≈ B(2)/A(2) ≈ B(4)/A(4)（比值一致）⇒ **纯偏移**，机制与 m 无关；
#   ② 比值随 m **单调变**⇒ **两效应耦合**，须一起标定；
#   ③ 若 B(0)、B(2) 的有效窗口与 A 侧差异过大 ⇒ 报"未分辨"，不下结论。
#
# 为什么**不**立刻并发跑（而是等 v6 退出）
# ----------------------------------------
# 实测：3 个 N=192 并发会把 swap 推到 ~78%、进程进 `D` 状态（近乎卡死那次的配置）。
# 当前 mid192_ns4b + a3_facet00 已占 ~14 GB，再加一个 ~7 GB 就越线。
# ⇒ 等 v6（A-3 两臂）**完全退出**后再串行跑，既安全又不与 v4/v6 抢槽位。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive7.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "等 v6（A-3 两臂）退出……"
while pgrep -f 'bash _r1_drive6\.sh' > /dev/null 2>&1; do sleep 120; done
log "v6 已退出，开始补算（活跃 _r1_exp = $(pgrep -c -f '_r1_exp\.py' 2>/dev/null)）"

run () {   # run <名字> <norm-smooth>
  local NAME="$1" NS="$2"
  mkdir -p "_exp/$NAME"
  setsid nohup $PY -u _r1_exp.py --out "_exp/$NAME" --case mid \
      --N 192 --dx-nm 125.0 --steps 700 --every 5 --snap-every 50 \
      --nseed 1 --seed-scale 2 --beta-h 3.5 --beta-w 2.3 --adv proj2 \
      --nthreads 4 --norm-smooth "$NS" --reinit-band 6.0 --max-hours 3.5 \
      > "_exp/$NAME/run.log" 2>&1 < /dev/null &
  log "启动 $NAME（Δx=125, seed×2, N=192, norm_smooth=$NS）pid=$!"
  while pgrep -f "_r1_exp.py --out _exp/$NAME" > /dev/null 2>&1; do sleep 120; done
  log "$NAME 结束"
  $PY -u _r1_aniso.py "$NAME" >> "$LOG" 2>&1
}

run m125_s2_ns0 0      # 与 Δx=250 的 mid250_base 对应
run m125_s2_ns2 2      # 与 Δx=250 的 mid250_ns2   对应
log "==== 完成。判读：三点（m=0/2/4，seed×2）判断两条 m-趋势线平行还是发散 ===="
