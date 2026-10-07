#!/bin/bash
# ★★★ 队列 v5 —— **A-3（惯习面 facet）对照实验**
#
# 为什么要有它（本轮查清的事实链）
# --------------------------------
# 1. `_r1_exp.py` 的 `KW` **从来没有**传 `facet_lam` ⇒ 所有 R1 算例走的是
#    `aniso=0.4` 的普通 Herring 形式：刚度 `γ0[1+2Λ−3Λ sin²θ]` = 惯习面 1.8γ0、θ=90° 0.6γ0，
#    比值只有 3:1，**没有奇异面** ⇒ 面长不平（A-3：`fill_cal`≈0.5 ≈ 椭球 0.524）。
# 2. 引擎里**已经有**为这个问题写的机制 `herring_stiffness_cusp`（P3），
#    其 docstring 给出的定量理由与**本轮 B-1b 独立量到的漂移是同一个机制**：
#    「孤立单核长跑 aspect 3.49 → 2.23，而法向厚度反而长了 2.4×
#      ⇒ 各向同性 γ 的 Gibbs–Thomson 把薄饼拉圆了」。
#    cusp 形式让惯习面**同时**最低能（γ→γ0(1+Λε_c)）与最刚（刚度→γ0Λ/ε_c，很大）。
# 3. 生效性已验证：`_r1_stiffunit.py` 直接调 `_stiff_of`，
#    k=1 时 facet_lam 0→0.4 让刚度从 0.090–0.270 变到 **0.150–1.349**（4 倍）✅
#    ⚠ 端到端 6 步冒烟**看不见**效果（`stk·κ/Δf`≈0.2%，而读数是**胞量化**的）
#      ⇒ 本队列用**薄板（κ 大）+ 700 步长跑 + `fill_cal`/长时程 aspect** 来测。
#
# 优先级：A-3 属于「单个」阶段（形状质量），**排在实验 7（块）之前**。
# 槽位纪律：等 v4 队列**完全退出**后再开始，避免两个队列抢槽位 ⇒ OOM。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
set +e
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r1drive5.log
: > "$LOG"
log () { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

nactive () { pgrep -c -f '_r1_exp\.py' 2>/dev/null | tr -d '\n'; }

wait_slot () {
  while true; do
    n=$(nactive); [ -z "$n" ] && n=0
    [ "$n" -le 2 ] && return 0
    sleep 60
  done
}

log "等 v4 队列（pid $(pgrep -f '_r1_drive4.sh' | head -1)）退出……"
while pgrep -f '_r1_drive4\.sh' > /dev/null 2>&1; do sleep 120; done
log "v4 已退出，A-3 对照开始（活跃 _r1_exp = $(nactive)）"

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
  log "$NAME 结束 —— 自动分析"
  $PY -u _r1_aniso.py "$NAME" >> "$LOG" 2>&1
  $PY -u _r1_c5chk.py "$NAME" >> "$LOG" 2>&1
}

# ★ 成对跑：只差 `--facet-lam` 一个变量
run a3_facet00 0.0
analyze a3_facet00
run a3_facet04 0.4
analyze a3_facet04

log "==== A-3 对照完成：比较 a3_facet00 vs a3_facet04 的 fill_cal 与长时程 aspect ===="
