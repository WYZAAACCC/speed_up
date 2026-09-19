#!/bin/bash
# =============================================================================
# T14 诊断：AMR 段错误的**真正原因**是不是「硬编码 elementid 后处理」
# =============================================================================
# 缘起
# ----
# 仓库现有结论是「**分裂式 CH（SplitCHParsed/SplitCHWRes）+ AMR ⇒ 段错误**」，
# 依据是 `front1d.i`（崩）与 `grain_growth_circle.i`（不崩）的对照。
#
# ⚠ **但那个对照有混淆**：两个算例在**维度、物理、材料、后处理**上全都不同。
#   本轮逐项比对后发现一个**更可疑且更具体**的差异：
#
#     front1d.i            : 有两个 `ElementalVariableValue`，**硬编码 `elementid = 4 / 155`**
#     grain_growth_circle.i: 只有 `NodalExtremeValue`，**没有任何 elementid**
#
#   而已解出的崩溃符号是
#       libMesh::PetscVector<double>::get(std::vector<unsigned long> const&, double*) const
#   —— 这正是「**按 DOF 列表取解值**」的路径。`ElementalVariableValue` 就是干这个的。
#
#   机制也说得通：AMR 加密后，`elementid = 155` 可能变成**非活动的父单元**，
#   其 DOF 已不在解向量里 ⇒ `PetscVector::get` **越界** ⇒ 段错误。
#
# 本脚本的判决性实验（一次只改一个因素）
# --------------------------------------
#   A  `front1d.i` + AMR                                  ← 复现基线（应崩）
#   B  `front1d.i` **去掉两个 elementid 后处理** + AMR      ← **关键**：若不崩，假设成立
#   C  同 B 但**不开 AMR**                                 ← 对照：证明 B 的改动本身没问题
#
# 判读
# ----
#   A 崩 + B 不崩  ⇒ **崩溃是 elementid 后处理造成的，与 SplitCH 无关**
#                    ⇒ AMR 可用（只要别用硬编码单元号），Phase 2.3 可以继续
#   A 崩 + B 也崩  ⇒ 原结论成立，确实是 SplitCH 的问题，再回去深挖
#
# 用法： bash run_t14_diag.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/t14diag}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
NX="${NX:-160}"
END="${END:-2.0e-3}"          # 短：只要越过第一次 AMR 就够（原崩溃在第 11 步）
TMO="${TMO:-900}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

ADAPT='[Adaptivity]
  marker = marker
  interval = 1
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

python3 - "$ROOT" "$SRC" "$ADAPT" <<'PY'
import os, re, sys
root, src, adapt = sys.argv[1], sys.argv[2], sys.argv[3]
t0 = open(src, encoding="utf-8").read()

# --- 变体 B/C：删掉两个带 elementid 的后处理（连同其块）---
def strip_elementid(t):
    # 逐个把含 elementid 的 [name] ... [] 块整个删掉
    out, n = t, 0
    while True:
        m = re.search(r"\n[ \t]*\[(\w+)\]\n(?:(?!\n[ \t]*\[).)*?elementid(?:(?!\n[ \t]*\[\]).)*?\n[ \t]*\[\]\n",
                      out, re.S)
        if not m:
            break
        out = out[:m.start()] + "\n" + out[m.end():]
        n += 1
    return out, n

noeid, n = strip_elementid(t0)
assert n == 2, f"预期删 2 个 elementid 后处理，实际删了 {n} 个 —— 源文件变过了？"
print(f"  变体 B/C：删掉 {n} 个带 elementid 的后处理")

# --- 写入四个文件：A = 原样 + AMR；B = 去 elementid + AMR；C = 去 elementid，无 AMR
NE_PP = """  # 【诊断用】AMR 有没有真的生效，**只看这个**（见 AGENTS.md 3.x：
  # 老式 Adaptivity 写法会「跑完不报错但一个单元都没动」）
  [num_elem]
    type = NumElements
    execute_on = 'initial timestep_end'
  []
"""

def add_numelem(t):
    i = t.rindex("[]", 0, t.index("[Executioner]"))   # [Postprocessors] 块的结尾
    return t[:i] + NE_PP + t[i:]

def with_adapt(t):
    # 在 [Outputs] 之前插 [Adaptivity]
    i = t.index("[Outputs]")
    return t[:i] + adapt + "\n" + t[i:]

t0 = add_numelem(t0)
noeid = add_numelem(noeid)
open(os.path.join(root, "A.i"), "w", encoding="utf-8").write(with_adapt(t0))
open(os.path.join(root, "B.i"), "w", encoding="utf-8").write(with_adapt(noeid))
open(os.path.join(root, "C.i"), "w", encoding="utf-8").write(noeid)
print("  写出 A.i / B.i / C.i（都加了 NumElements 后处理）")
PY

run() {   # run <标签> <文件>
  local TAG="$1" F="$2"
  local D="$ROOT/$TAG"; mkdir -p "$D"; cd "$D"
  local S=$(date +%s)
  local RC=0
  timeout "$TMO" "$MOOSE" -i "$ROOT/$F" Mesh/nx="$NX" Executioner/end_time="$END" \
      > run.log 2>&1 || RC=$?
  local EL=$(( $(date +%s) - S ))
  printf "  %-4s rc=%-3s %4ss  " "$TAG" "$RC" "$EL"
  if [ $RC -ne 0 ]; then
    echo -n "❌ 非零退出  "
    sed "s/\x1b\[[0-9;]*m//g" "$D/run.log" | grep -a -m1 -i "segmentation\|signal\|ERROR" | head -1 | cut -c1-70
  else
    echo "✅ 正常跑完"
  fi
  # 单元数变化
  local CSV
  CSV=$(ls "$D"/*.csv 2>/dev/null | head -1)
  if [ -n "$CSV" ] && [ -f "$CSV" ]; then
    python3 - "$CSV" <<'PY'
import csv, sys
r = list(csv.DictReader(open(sys.argv[1])))
k = [c for c in r[0] if "num_elem" in c or c == "n_elem"]
if k and len(r) > 1:
    print(f"       单元数 {r[0][k[0]]} -> {r[-1][k[0]]}"
          f"   ({'AMR 生效' if r[0][k[0]] != r[-1][k[0]] else 'AMR **没生效**'})")
PY
  fi
  cd "$ROOT"
}

echo
echo "=== A：原样 + AMR（复现基线）==="
run A A.i
echo "=== B：**去掉 elementid 后处理** + AMR（关键）==="
run B B.i
echo "=== C：去掉 elementid、不开 AMR（对照）==="
run C C.i

echo
echo "=== 判读 ==="
echo "  A 崩 + B 不崩 ⇒ **崩溃源于硬编码 elementid 后处理，与 SplitCH 无关**"
echo "                   ⇒ AMR 可用（别用硬编码单元号）"
echo "  A 崩 + B 也崩 ⇒ 原结论成立，是 SplitCH 的问题"
