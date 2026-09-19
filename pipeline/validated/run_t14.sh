#!/bin/bash
# =============================================================================
# T14 / Phase 2.3：AMR 加密对守恒与解的影响
# =============================================================================
# 审计原文：
#   「2.3 AMR：只在前两阶段通过后测试 AMR。分别测试**只加密**、
#     **加密+粗化**、**关闭状态材料重投影**的情况。
#     守恒、速度、晶界过剩和材料属性变化必须**分开记录**。」
#   「T14 | AMR 加密 | 平面/圆晶粒 | 守恒 ≤1e-8，速度和 Γ 变化 ≤5%」
#
# 【为什么用 1D 平界面做守恒】
#   守恒要有**守恒量**才测得出来。圆晶粒算例没有守恒量
#   （∫gr0 dA 本来就随晶粒收缩而变），所以守恒那一项用 1D 静界面算例
#   （它有 `total_c` 后处理，均匀网格下实测漂移 0.000e+00，是个干净的基准）。
#
# 【仓库已有的先验】记忆里记着「AMR 才破坏守恒」—— 所以这是个有风险的测试，
#   不是走过场。本脚本的判据就是去看它到底破没破、破多少。
#
# 【三组对照】（审计要求分开测）
#   uniform : 均匀网格（基准）
#   refine  : 只加密（不给 coarsen）
#   both    : 加密 + 粗化
#   noreproj: 加密 + 粗化 + 关掉状态材料重投影（disable_stateful_material_reprojection）
#
# 用法： bash run_t14.sh
# =============================================================================
set +u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/t14}"
T_END="${T_END:-2.0e-2}"
KC="${KC:-1.0e-14}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$ROOT"; mkdir -p "$ROOT"

# --- 基准算例 ---
python3 "$HERE/make_1d_static.py" --out "$ROOT/base.i" --kc "$KC" --t-end "$T_END" \
    > "$ROOT/gen.log" 2>&1 || { echo "生成失败"; tail -5 "$ROOT/gen.log"; exit 1; }

# --- AMR 块（追加到输入末尾）---
ADAPT_REFINE_ONLY='
[Adaptivity]
  marker = marker
  # 只加密、不粗化
  max_h_level = 2
  [Indicators]
    [jump]
      type = GradientJumpIndicator
      variable = eta
    []
  []
  [Markers]
    [marker]
      type = ErrorFractionMarker
      indicator = jump
      refine = 0.7
      coarsen = 0
    []
  []
[]
'

ADAPT_BOTH='
[Adaptivity]
  marker = marker
  max_h_level = 2
  [Indicators]
    [jump]
      type = GradientJumpIndicator
      variable = eta
    []
  []
  [Markers]
    [marker]
      type = ErrorFractionMarker
      indicator = jump
      refine = 0.7
      coarsen = 0.1
    []
  []
[]
'

gen() {   # gen <名字> <adpativity 块或空>
  local tag=$1 block=$2
  local D="$ROOT/$tag"; mkdir -p "$D"
  cp "$ROOT/base.i" "$D/case.i"
  if [ -n "$block" ]; then
    printf '%s\n' "$block" >> "$D/case.i"
  fi
  # 每 5 步做一次自适应（MOOSE 默认是每步，太贵）
  # ⚠ 判据不能用 `"interval" not in t` —— 输入里有 `time_step_interval`，
  #   会误判成"已经有了"从而根本不加（实测踩过）。
  if [ -n "$block" ]; then
    python3 - "$D/case.i" <<'PY'
import sys, re
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
if "[Adaptivity]" in t and not re.search(r"^\s*interval\s*=", t, re.M):
    t = t.replace("  marker = marker", "  marker = marker\n  interval = 5", 1)
open(p, "w", encoding="utf-8", newline="").write(t)
PY
  fi
  rm -f "$D"/*_out.csv "$D"/*.e 2>/dev/null
}

gen uniform ""
gen refine  "$ADAPT_REFINE_ONLY"
gen both    "$ADAPT_BOTH"
gen noreproj "$ADAPT_BOTH"

# noreproj 额外关掉状态材料重投影
python3 - "$ROOT/noreproj/case.i" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace("  marker = marker",
              "  marker = marker\n"
              "  # 关闭状态材料重投影（审计要求单独测的一项）\n"
              "  disable_stateful_material_reprojection = true", 1)
open(p, "w", encoding="utf-8", newline="").write(t)
PY

echo "三个变体已生成（uniform / refine / both / noreproj）"
echo

for tag in uniform refine both noreproj; do
  D="$ROOT/$tag"
  echo "=== 跑 [$tag] ==="
  RC=0
  ( cd "$D" && timeout 2400 "$MOOSE" -i case.i > run.log 2>&1 ) || RC=$?
  echo "    退出码=$RC  警告=$(sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -ac 'Missing coupled')"
  if [ $RC -ne 0 ]; then
    sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -A4 -m1 "ERROR" | head -6
  fi
done

echo
echo "=== 对比 ==="
python3 - "$ROOT" <<'PY'
import csv, os, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/validated")
try:
    from robust_csv import read_rows
except Exception:
    def read_rows(p): return list(csv.DictReader(open(p)))

root = sys.argv[1]
THEORY = 0.9 / (0.9 + 2 * 0.264)
print("  %-10s %-12s %-14s %-12s %-14s" %
      ("变体", "末态 t", "守恒漂移", "k_eff", "与理论偏差"))
print("  " + "-" * 66)
base = None
for tag in ("uniform", "refine", "both", "noreproj"):
    f = os.path.join(root, tag, "case_out.csv")
    if not os.path.exists(f):
        print("  %-10s （没跑出来）" % tag); continue
    r = read_rows(f)
    if not r:
        print("  %-10s （空）" % tag); continue
    tot = [float(x["total_c"]) for x in r if x.get("total_c")]
    drift = abs(tot[-1] - tot[0]) / abs(tot[0]) if tot and tot[0] else 0.0
    keff = float(r[-1]["c_solid"]) / float(r[-1]["c_max"])
    rel = abs(keff - THEORY) / THEORY
    if base is None:
        base = keff
    print("  %-10s %-12s %-14.3e %-12.8f %-14s"
          % (tag, r[-1]["time"], drift, keff,
             "%+.3f%%" % ((keff - THEORY) / THEORY * 100)))
print()
print("  审计判据：守恒漂移 ≤ 1e-8；速度与 Γ 变化 ≤ 5%")
PY
