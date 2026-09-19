#!/bin/bash
# =============================================================================
# 二分第三层：把 align4 **内联**进 L2b，去掉一层 material_property_names 嵌套
# =============================================================================
#
# 前两层的结论：
#   只关 κ   -> 0.02081（没变）
#   只关 γ   -> 0.02082（没变）
#   只关 L   -> 3.10796e-06（改善 6700×）
#   只关 L2a -> 0.0199971（降 4%）
#   只关 L2b -> 1.58712e-04（改善 131×）   <- 主导
#
# L2b 的链是三层的：
#     gdir_p/gdir_q (ParsedMaterial, 数据)
#        -> align4_prop  (DerivativeParsedMaterial, material_property_names='gdir_p gdir_q')
#        -> L2b          (DerivativeParsedMaterial, material_property_names='align4')
#        -> L_aniso      (DerivativeParsedMaterial, material_property_names='L2a L2b')
# 而 L2a 只有一层（显式表达式）。
#
# **假设**：非 AD 的 chain rule 在**多层** material_property_names 嵌套下
# 不能正确传播二阶导。检验法：把 align4 的表达式原文**内联**进 L2b，
# 把嵌套从三层降到两层（L2a/L2b -> L）。若比值大幅下降 => 假设成立。
#
# ⚠ 这同时可能就是**修法**。若成立，改 `frozen/gen_aniso_nonad.py` 即可。
#
# 用法： bash inline_align4.sh
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
D="${D:-/root/work/jacfix2/inline}"
MOOSE=/root/projects/gb_jac/gb_jac-opt
CACHE=/root/work/jacfix/fixed/.jitcache

rm -rf "$D"; mkdir -p "$D"; cd "$D"
cp "$SRC" N.i
cp /root/work/jacfix/base/columnar_seeds.csv .
[ -d "$CACHE" ] && cp -r "$CACHE" .jitcache || true

python3 - <<'PY'
import re
s = open("N.i", encoding="utf-8").read()

m = re.search(r"\[align4_prop\](.*?)\n  \[\]", s, re.S)
assert m, "找不到 [align4_prop]"
al = re.search(r"expression = '(.*?)'\s*\n", m.group(1), re.S)
assert al, "align4_prop 里找不到 expression"
align4_expr = al.group(1)

m2 = re.search(r"\[L2b\](.*?)\n  \[\]", s, re.S)
assert m2, "找不到 [L2b]"
blk = m2.group(0)
assert "material_property_names = 'align4'" in blk, "L2b 的 material_property_names 不是 'align4'"

# ⚠ 不能把 material_property_names 整行删掉：内联后的表达式里仍然出现
#   gdir_p / gdir_q（它们是纯数据的 ParsedMaterial），必须继续声明，
#   否则 MOOSE 报 `Unknown identifier` 直接 MPI_Abort。
#   实测踩过：第一次写成 `blk.replace("material_property_names = 'align4'\n", "")`。
new_blk = blk.replace("material_property_names = 'align4'",
                      "material_property_names = 'gdir_p gdir_q'")
new_blk = re.sub(r"expression = '.*?'\s*\n",
                 "expression = '1+0.7*(2*(" + align4_expr + ")-1)'\n", new_blk, flags=re.S)
s = s.replace(blk, new_blk)
open("N.i", "w", encoding="utf-8").write(s)
print("已内联 align4 进 L2b（expression 长度 %d）" % len(align4_expr))
PY
echo "--- 复核：L2b 不应再有 material_property_names ---"
awk "/\[L2b\]/,/^  \[\]/" N.i | grep -cE "material_property_names" || echo "  0 处 ✓"
echo

echo "=== 跑 ==="
timeout 2400 "$MOOSE" -i N.i Mesh/gen/nx=24 Mesh/gen/ny=12 \
    -pc_type lu -pc_factor_mat_solver_type mumps \
    -snes_test_jacobian > jac.log 2>&1 || true
echo
echo "=== 结果 ==="
printf "  %-14s %s\n" "配置" "||J-Jfd||/||J||"
printf "  %s\n" "----------------------------------------"
printf "  %-14s %s\n" "全开（生产）"   "2.08202e-02"
printf "  %-14s %s\n" "只关 L2b"       "1.58712e-04"
printf "  %-14s %s\n" "两个都关"       "3.10796e-06"
V=$(grep -aoE "Jfd\|\|_F/\|\|J\|\|_F = [0-9.eE+-]+" jac.log 2>/dev/null | head -1 | grep -oE "[0-9.eE+-]+$")
printf "  %-14s %s\n" "**align4 内联**" "${V:-（没出）}"
echo
echo "判读：若内联后比值大幅下降 => 三层 material_property_names 嵌套是根因，"
echo "      且**内联就是修法**（改 frozen/gen_aniso_nonad.py 的 L2b 定义）。"
