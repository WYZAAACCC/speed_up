#!/bin/bash
# =============================================================================
# 二分第二层：L 的 η 依赖缺陷在 L2a 还是 L2b？
# =============================================================================
#
# 第一层二分的结论：只关掉 `L` 的 η 依赖 ⇒ FD 比值 2.08202e-02 → 3.10796e-06。
# 而 `L = L2a × L2b`，两者都依赖 η：
#   L2a  : 逐对取向差加权（2a），coupled_variables = 'T gr0..gr7'
#   L2b  : 热梯度对齐因子（2b），material_property_names = 'align4'，align4 又是一个 ratio
#
# 本脚本分别只关一半：
#   iso_L2a : L2a 只留 T（L2b 保持 η 依赖）
#   iso_L2b : L2b ≡ 1    （L2a 保持 η 依赖）
#
# 判读：哪个变体把比值拉回 ~1e-5 以下，缺陷就在哪一半的链里。
#
# 用法： bash bisect_L.sh
# =============================================================================
set -eo pipefail

# ⚠ 必须激活 conda：本机 MOOSE 的 libMesh/PETSc/WASP 全来自 conda 的 moose-dev 包，
#   而且 **ParsedMaterial 的 LLVM JIT 需要 mpicxx**。不激活会看到
#   `mpicxx: not found` 并**静默退回解释执行**（数值相同，但慢很多）。
#   实测踩过：内联变体改了表达式、JIT 缓存失效，才暴露出来。
# 注意不用 `set -u` —— conda 的 activate 会引用未定义的 $CONDA_BUILD。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

SRC="${SRC:-/root/work/jacfix/base/N.i}"
ROOT="${ROOT:-/root/work/jacfix2}"
MOOSE=/root/projects/gb_jac/gb_jac-opt
CACHE=/root/work/jacfix/fixed/.jitcache

L2A_ISO='(4.0/3.0)*232*exp(-3.234/(8.617e-5*T))/4.0e-6'

for TAG in iso_L2a iso_L2b; do
  D="$ROOT/$TAG"; rm -rf "$D"; mkdir -p "$D"; cd "$D"
  cp "$SRC" N.i
  cp /root/work/jacfix/base/columnar_seeds.csv .
  [ -d "$CACHE" ] && cp -r "$CACHE" .jitcache || true

  python3 - "$TAG" "$L2A_ISO" <<'PY'
import re, sys
tag, l2a_iso = sys.argv[1], sys.argv[2]
lines = open("N.i", encoding="utf-8").read().split("\n")

def block_of(i):
    for j in range(i, max(0, i - 40), -1):
        m = re.match(r"\s*\[(\w+)\]", lines[j])
        if m:
            return m.group(1)
    return ""

n = 0
for i, ln in enumerate(lines):
    if not ln.lstrip().startswith("expression = "):
        continue
    name = block_of(i)
    if name == "L2a" and tag == "iso_L2a":
        lines[i] = "    expression = '" + l2a_iso + "'"; n += 1
    elif name == "L2b" and tag == "iso_L2b":
        lines[i] = "    expression = '1'"; n += 1
open("N.i", "w", encoding="utf-8").write("\n".join(lines))
print(f"  [{tag}] 替换 {n} 处")
PY
done

echo
echo "=== 并行跑 ==="
for TAG in iso_L2a iso_L2b; do
  ( cd "$ROOT/$TAG" && timeout 2400 "$MOOSE" -i N.i \
      Mesh/gen/nx=24 Mesh/gen/ny=12 \
      -pc_type lu -pc_factor_mat_solver_type mumps \
      -snes_test_jacobian > jac.log 2>&1 ) &
done
wait

echo
echo "=== 结果 ==="
printf "  %-10s %-18s %s\n" "变体" "||J-Jfd||/||J||" "说明"
printf "  %s\n" "--------------------------------------------------------------------"
printf "  %-10s %-18s %s\n" "(全开)" "2.08202e-02" "L2a/L2b 都依赖 η"
printf "  %-10s %-18s %s\n" "iso_L"  "3.10796e-06" "两者都关"
for TAG in iso_L2a iso_L2b; do
  V=$(grep -aoE "Jfd\|\|_F/\|\|J\|\|_F = [0-9.eE+-]+" "$ROOT/$TAG/jac.log" 2>/dev/null | head -1 | grep -oE "[0-9.eE+-]+$")
  case $TAG in
    iso_L2a) DESC="只关 L2a（2a 逐对加权）";;
    iso_L2b) DESC="只关 L2b（2b 热梯度对齐）";;
  esac
  printf "  %-10s %-18s %s\n" "$TAG" "${V:-（没出）}" "$DESC"
done
