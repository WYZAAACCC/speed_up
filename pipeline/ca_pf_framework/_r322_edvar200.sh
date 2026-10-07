#!/bin/bash
# _r322_edvar200.sh —— ★ `§164.5` 的**待办**：把框架级单变量实验的时间窗**延到 200 步**。
#
# ## 为什么必须延（`§164.5` 自己写的边界）
# `§164` 的结论（"σ 不由变体配置主导"）**只在 step 20–60 上测过**，
# 而那时**板条尚未充分接触**（`§145.2`：F2 胞数 step 40 才 ~9 个、step 80 才上百）
# ⇒ **σ 可能还没"看见"彼此**。
# **⇒ 若在 200 步上（板条已充分接触）离散度**开始**随 `‖Δε‖` 增大
#    ⇒ `§164` 的结论**只在早期成立**，必须记账；
#    ⇒ 若仍无关 ⇒ `§164` **加强**。**
#
# ## 设计（与 `_r318` 逐字相同，**只把 `--steps 60` 改成 200**）
# | 臂 | `--laths` | 变体对 | `‖ε⁰₁−ε⁰_w‖` |
# |---|---|---|---|
# | `near200` | `1,1,1,2,2,2` | V1–V2 | 0.025990（0.21×）|
# | `mid200`  | `1,1,1,3,3,3` | V1–V3 | 0.123728（1.00×）|
# | `far200`  | `1,1,1,5,5,5` | V1–V5 | 0.242277（1.96×）|
#
# ## 判据（**先写死**）
# * **Q-1** 三臂几何验收 `nf2(t=0)=0` 且 `cov_norm ≥ 0.95`（不过则报"不适用"）。
# * **Q-2 ★** 在 **step 100/120/…/200** 上，"极差/标准差是否随 `‖Δε‖` 单调增"。
#   **预言**：若 `§164` 稳健 ⇒ **仍不单调**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py mb2fp10 --emit > _w2_r322_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r322_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

run() {   # run <laths> <tag>
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 200/')
  case "$CMD" in *"--diag-edv"*) ;; *) CMD="$CMD --diag-edv" ;; esac
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  echo "  --- $TAG : $(printf '%s' "$CMD" | grep -o -- '--laths [0-9,]*')  $(printf '%s' "$CMD" | grep -o -- '--steps [0-9]*') ---"
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" && \
  printf '%s' "$CMD" | grep -q -- '--steps 200' || echo "      ❌ 参数替换失败"
  eval "$CMD" > "_w2_r322_${TAG}_run.log" 2>&1 &
  echo "      启动 PID=$! $(date '+%T')"
}

echo "=== §164 时间窗延长实验（200 步）$(date '+%F %T') ==="
run "1,1,1,2,2,2" near200
run "1,1,1,3,3,3" mid200
run "1,1,1,5,5,5" far200
wait
echo "=== 跑完 $(date '+%F %T') ==="
for t in near200 mid200 far200; do
  f="_w2_r322_${t}_run.log"
  printf '  %-10s Traceback=%s  末步=%s\n' "$t" "$(grep -c Traceback "$f" || true)" \
    "$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')"
done
