#!/bin/bash
# _r318_edvar.sh —— ★★ **框架级单变量实验**：σ 到底响应不响应"变体配置"？
#
# ## 问题（objective 第 (2) 部分："检查协调框架是否完善"）
# `ed_v = Σ_p e0v_eng[v,p]·σ_p + sext_e0[v]` 是**自项**，**没有显式变体-变体相互作用**；
# 相互作用只经**共享 σ** 间接发生（标准平均场）。
# **⇒ 关键：σ 响应不响应变体配置？**
#   * 响应 ⇒ `ed` 编码变体间相互作用 ⇒ 自协调**可能**自发出现；
#   * 不响应 ⇒ `ed` 无法区分变体 ⇒ 解释 `§146`/`§148` 的"中性"。
#
# ## 设计（**严格单变量：只换"第二个变体"**）
# 几何**逐字相同**（N=96 / `plate-L 1600` / `1,1,1,x,x,x` / `--multi-block` / `facet-proj 10` /
# 60 步 / `--diag-edv`），**只改 `x`** ⇒ 只改变体对的**本征应变失配** `‖Δε‖`：
#
# | 臂 | `--laths` | 变体对 | `‖ε⁰₁ − ε⁰_w‖_F` | 相对基准 |
# |---|---|---|---|---|
# | **`mb2fp10EDV`**（已有基准）| `1,1,1,3,3,3` | V1–V3 | **0.123728** | 1.00× |
# | **`edNear`** | `1,1,1,2,2,2` | V1–V2 | **0.025990** | **0.21×** |
# | **`edFar`** | `1,1,1,5,5,5` | V1–V5 | **0.242277** | **1.96×** |
#
# **⇒ 三臂的 `‖Δε‖` 跨 9.3 倍，而其它一切相同。**
#
# ## 判据（**先写死**）
# * **P-1** 三臂的 `nf2(t=0)=0`、`cov_norm ≥ 0.95`（几何合格；否则报"不适用"）。
# * **P-2 ★ 核心**：三臂在**相同 step** 上的 `ed` **离散度**（极差/标准差）。
#   * **预言**：若 σ 响应变体配置 ⇒ 离散度随 `‖Δε‖` **单调增**；
#   * **若三臂离散度都与 `‖Δε‖` 无关** ⇒ **σ 不由变体配置主导**
#     ⇒ 这就**从框架层**解释了"为什么没有自协调"。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

# 从已有的 mb2fp10EDV 重建命令（保证其它参数逐字相同）
"$PY" -u _r178_repro.py mb2fp10 --emit > _w2_r318_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r318_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

run() {   # run <laths> <tag>
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 60/')
  case "$CMD" in *"--diag-edv"*) ;; *) CMD="$CMD --diag-edv" ;; esac
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  echo "  --- $TAG : --laths $LAT ---"
  printf '%s' "$CMD" | grep -o -- '--laths [0-9,]*' | sed 's/^/      /'
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" || echo "      ❌ laths 没换成功"
  eval "$CMD" > "_w2_r318_${TAG}_run.log" 2>&1 &
  echo "      启动 PID=$! $(date '+%T')"
}

echo "=== 框架级单变量实验（只换变体）$(date '+%F %T') ==="
run "1,1,1,2,2,2" edNear
run "1,1,1,5,5,5" edFar
wait
echo "=== 跑完 $(date '+%F %T') ==="
for f in _w2_r318_edNear_run.log _w2_r318_edFar_run.log; do
  printf '  %-32s Traceback=%s\n' "$f" "$(grep -c Traceback "$f" || true)"
done
