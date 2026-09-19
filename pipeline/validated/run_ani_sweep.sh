#!/bin/bash
# =============================================================================
# `A_ani`（四重生长选择强度）的敏感性扫描
# =============================================================================
# ## 为什么扫它
#
# `A_ani` 的物理对应量是**固液界面的立方向异性**。MD（Kavousi et al.,
# MSMSE 28 (2020) 015006，DOI 10.1088/1361-651X/ab580c）给纯 Ti：
#     δ₁ = 0.021(5)      单参数拟合 δ = 0.0047
# 而本项目用 **0.7** —— 大 33~150 倍。
# ⇒ 问题：**0.7 是不是白给的？把它降到物理量级，择优还在不在？**
#
# ## 判据（⚠ 两个观测量，必须分清）
#
#   * `align_mean`        —— **全域**平均，**不可用**：未熔化的基体占 ~92%，
#                            会把任何择优稀释到 0.5 附近（实测就是 0.4998）。
#   * `align_melt`（本脚本加）—— 只统计 **block 1（初始熔池区域）**。
#                            生产输入用 `ParsedSubdomainMeshGenerator` 把
#                            t=0 的熔池标成 block 1，且**不随时间移动**
#                            ⇒ 这就是"发生凝固的那块地方" ✓
#
#   成功判据见脚本末尾的判读分支。
#
# ## ⚠ 必须声明的限制
#
# 小网格上 `dx ≫ ξ`（86×30 时 dx=5 µm、ξ=2 µm ⇒ ξ/dx=0.4；默认 54×19 更粗）
# ⇒ **界面的细节没被解析**。所以这是一个**受控对比**
# （所有档同网格同时间，"A_ani 有没有影响"是可信的），**不是**定量织构预测。
#
# ⚠ 用户约束：只做 smoke test。每档有硬超时。
#
# 用法： ANI_LIST="0 0.02 0.7" bash run_ani_sweep.sh
# =============================================================================
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ROOT="${ROOT:-/root/work/ani}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
ANI_LIST="${ANI_LIST:-0 0.02 0.7}"
NX="${NX:-54}"; NY="${NY:-19}"
END="${END:-3.0e-5}"
TMO="${TMO:-600}"
SEED="${SEED:-/root/work/jitcache_seed}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

for A in $ANI_LIST; do
  D="$ROOT/a$A"; mkdir -p "$D"; cd "$D"

  # ⚠ 必须复制 JIT 缓存种子。生产输入的 parsed 表达式巨大，不预热的话
  #   **光 setup 就要 >260 s**（实测：TMO=260 时 `run.log` 停在 "Setting Up…"、
  #   0 个时间步）。本脚本第一版就漏了这一步。
  #   注意：每个 A 的 `L` 表达式不同 ⇒ 那一项仍要重编，但其余材料可复用。
  if [ -d "$SEED" ]; then
    mkdir -p .jitcache; cp -rn "$SEED"/. .jitcache/ 2>/dev/null || true
  fi

  # ---- 走生产链，只改 A_ani ----
  cp "$REPO/frozen/gen_aniso_nonad.py" "$REPO/frozen/splice_aniso_nonad.py" .
  cp "$REPO/columnar_seeds.csv" .
  cp "$REPO/stage1_meltpool_c.i" .
  source /root/miniconda3/etc/profile.d/conda.sh
  conda activate ml
  python3 gen_aniso_nonad.py --op-num 8 --A-ani "$A" --out aniso_block.i > gen.log 2>&1 \
    || { echo "A=$A gen 失败"; tail -3 gen.log; continue; }
  python3 splice_aniso_nonad.py >> gen.log 2>&1 || { echo "A=$A splice 失败"; continue; }
  conda activate moose
  python3 "$HERE/make_jacfix.py"  --src stage1_meltpool_d.i --out d.jac --diff >> gen.log 2>&1 \
    || { echo "A=$A jacfix 失败"; continue; }
  mv d.jac stage1_meltpool_d.i
  python3 "$HERE/make_jacchain.py" --src stage1_meltpool_d.i --out d.jc >> gen.log 2>&1 \
    || { echo "A=$A jacchain 失败"; continue; }
  mv d.jc stage1_meltpool_d.i

  # ---- 确认 A 真的改到了 + 加「只统计熔池区域」的对齐度 ----
  python3 "$HERE/_ani_patch.py" "$A"

  echo "  --- A_ani = $A：跑（${NX}x${NY}，end_time=${END}，最多 ${TMO}s）---"
  S=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i stage1_meltpool_d.i Mesh/gen/nx=$NX Mesh/gen/ny=$NY \
      Executioner/end_time=$END > run.log 2>&1 || RC=$?
  echo "    rc=$RC  墙钟 $(( $(date +%s) - S ))s"
  cd "$ROOT"
done

echo
echo "=== 结果 ==="
python3 "$HERE/_ani_report.py" "$ROOT" "$ANI_LIST"
