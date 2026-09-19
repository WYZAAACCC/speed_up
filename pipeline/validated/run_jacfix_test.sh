#!/bin/bash
# =============================================================================
# T1b：ACGrGrPolyJ 的雅可比补全 —— 有限差分前后对照
# =============================================================================
#
# 判据（沿用 T1）：||J − Jfd||_F / ||J||_F 显著下降，并向 1e-5 靠拢。
#
# 方法学（两条都要遵守，否则对照无效）：
#   1. **两个算例用同一个二进制**（gb_jac-opt），只差输入里的核类型。
#      若 baseline 用 phase_field-opt、fixed 用 gb_jac-opt，
#      差异就无法归因到核。
#   2. 两个算例的 .i **只差 make_jacfix.py 那 8 处**（type + coupled_variables）。
#
# ⚠ `-snes_test_jacobian` 在每个牛顿迭代都做一次有限差分，非常慢
#   （实测 24×12 跑 20 分钟还没过一个时间步）。所以这里**不等它跑完**：
#   取**第一次**打印出来的 ratio —— 那正是初始态雅可比的差异，与缺项直接相关。
#   用 `timeout` 兜底，跑完就 kill。
#
# 用法：
#   bash run_jacfix_test.sh
#   NX=24 NY=12 TMO=2400 bash run_jacfix_test.sh
# =============================================================================
set -eo pipefail

BASE="${BASE:-/root/work/prod_merged}"   # 提供基础 .i / columnar_seeds.csv / aniso_block.i
SRCI="${SRCI:-N.i}"                       # 基础输入的文件名
ROOT="${ROOT:-/root/work/jacfix}"
NX="${NX:-24}"
NY="${NY:-12}"
TMO="${TMO:-2400}"                        # 每个算例最多跑 40 分钟
MOOSE=/root/projects/gb_jac/gb_jac-opt
MKFIX=/mnt/f/speed_up/pipeline/validated/make_jacfix.py

[ -x "$MOOSE" ] || { echo "错误：找不到 $MOOSE，先跑 pipeline/app/build_app.sh" >&2; exit 1; }
[ -f "$BASE/$SRCI" ] || { echo "错误：$BASE/$SRCI 不存在" >&2; exit 1; }

# ⚠ 基础输入**不能已经含 ACGrGrPolyJ** —— 否则前后两档是同一个东西，对照无意义。
if grep -q "type = ACGrGrPolyJ" "$BASE/$SRCI"; then
  echo "错误：$BASE/$SRCI 里已经有 ACGrGrPolyJ，不能当 baseline。" >&2
  echo "      请用未打补丁的 stage1_meltpool_d.i。" >&2
  exit 1
fi
# ⚠ 也不能带已知的其它雅可比缺陷 —— 否则测到的是"两个缺陷合起来"的效果，
#   归因不干净（本项目已栽过一次：只比序列的末几项与首几项，位置错位）。
if grep -q "coupled_variables" <(sed -n '/\[coupled_parsed\]/,/\[\]/p' "$BASE/$SRCI"); then
  echo "  （baseline 的 [coupled_parsed] 已声明 coupled_variables —— 1.1 缺陷已修，干净）"
else
  echo "⚠ 警告：baseline 的 [coupled_parsed] 没声明 coupled_variables，"
  echo "         它还带 1.1 缺陷，前后对照会把两个缺陷混在一起。" >&2
fi

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

rm -rf "$ROOT"; mkdir -p "$ROOT"

# --- 准备两个算例 ---
for TAG in base fixed; do
  D="$ROOT/$TAG"; mkdir -p "$D"; cd "$D"
  cp "$BASE/$SRCI" N.i
  # ⚠ 不能写 `[ -f x ] && cp x .` —— `set -e` 下文件不存在时整条 list 返回 1 会直接退出。
  for f in columnar_seeds.csv aniso_block.i; do
    if [ -f "$BASE/$f" ]; then cp "$BASE/$f" .; fi
  done
  if [ "$TAG" = fixed ]; then
    python3 "$MKFIX" --src N.i --out N.fixed.i | sed 's/^/    /'
    mv N.fixed.i N.i
  fi
done

# --- 跑 ---
# ⚠ 必须把预条件子覆盖成 **LU/MUMPS**，不能用生产输入里的 ASM/ILU。
#   原因（实测）：PETSc 做 `-snes_test_jacobian` 时要先 `MatComputeOperator`
#   把预条件后的矩阵显式化，ASM/ILU 下这一步极慢 —— 24x12 的算例跑到第一个
#   时间步都出不来 ratio。项目自己的参考脚本 repro_coupled_variables.py
#   用的就是 `-pc_type lu -pc_factor_mat_solver_type mumps`，
#   覆盖成同一套，量出来的数才和文档里的 7.9e-3 可直接比。
PC_OVERRIDE=(-pc_type lu -pc_factor_mat_solver_type mumps)

for TAG in base fixed; do
  D="$ROOT/$TAG"; cd "$D"
  echo "=== [$TAG] 网格 ${NX}x${NY}，最多 $((TMO/60)) 分钟 ==="
  set +e
  timeout "$TMO" "$MOOSE" -i N.i \
      Mesh/gen/nx="$NX" Mesh/gen/ny="$NY" \
      "${PC_OVERRIDE[@]}" \
      -snes_test_jacobian > jac.log 2>&1
  RC=$?
  set -e
  if [ "$RC" = 124 ]; then echo "  （timeout 到点，按预期；取已打印的第一次 ratio）"; fi

  R=$(grep -aE "Norm of matrix ratio" jac.log | head -1 || true)
  NMC=$(grep -ac "Missing coupled variables" jac.log || true)
  echo "  首次 FD ratio : ${R:-（没打印出来）}"
  echo "  Missing coupled variables : $NMC"
  echo
done

# --- 汇总 ---
# ⚠ grep 的字符串是 `J - Jfd`，**不是** PETSc 文档里的 "Norm of matrix ratio"。
#   PETSc 实际打印：`||J - Jfd||_F/||J||_F = 0.0208, ||J - Jfd||_F = 0.00606`。
#   第一版按文档写了 "Norm of matrix ratio"，一条都没匹配到，
#   差点得出"FD 没打印出来"的错误结论。仓库里的 jacobian_test.sh 用的是对的。
echo "======================================================================"
echo "汇总"
echo "======================================================================"
python3 - "$ROOT" <<'PY'
import re, sys, os
root = sys.argv[1]
def ratio(tag):
    p = os.path.join(root, tag, "jac.log")
    if not os.path.exists(p): return None
    for ln in open(p, encoding="utf-8", errors="replace"):
        m = re.search(r"Jfd\|\|_F/\|\|J\|\|_F = ([0-9.eE+-]+)", ln)
        if m: return float(m.group(1))
    return None
b, f = ratio("base"), ratio("fixed")
print(f"  baseline (ACGrGrPoly ) : {b if b is None else '%.6e' % b}")
print(f"  fixed    (ACGrGrPolyJ) : {f if f is None else '%.6e' % f}")
if b and f:
    print(f"  下降倍数               : {b/f:.4f}x")
    print(f"  是否达到 1e-5          : {'✅ 是' if f <= 1e-5 else '❌ 否'}")
    print()
    if abs(b - f) / max(b, 1e-300) < 1e-5:
        print("  ⚠ 两档**几乎相同** —— 说明缺项在这个配置下很小。")
        print("    这**不等于**核没生效：看两份日志的牛顿序列（第 1 次迭代的 |R|）")
        print("    会差最后一位（实测 base 1.964899e-03 / fixed 1.964898e-03）。")
        print("    缺项小 ⇒ 2e-2 这个 FD 误差**另有来源**，不是 ACGrGrPoly。")
PY
echo
echo "原始日志：$ROOT/base/jac.log  $ROOT/fixed/jac.log"
