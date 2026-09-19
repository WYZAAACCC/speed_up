#!/bin/bash
# =============================================================================
# 二分定位：FD 误差来自 κ / γ / L 中哪一个的 η 依赖？
# =============================================================================
#
# 背景：把 κ、γ、L 三者的 η 依赖**同时**去掉后，
#       ||J−Jfd||/||J|| 从 2.08e-2 掉到 1.6e-9（7 个数量级）。
#       ⇒ 缺的导数在这三者的 η 依赖链里。本脚本逐个去掉，定位到具体是哪一个。
#
# 三个变体（都基于**裸 ACGrGrPoly** 的输入，保证结构可比）：
#   iso_k : 只把 [kappa_aniso] 变常数
#   iso_g : 只把 [gamma_aniso] 变常数
#   iso_L : 只把 L 变 η 无关（L2b≡1，L2a 只留 T）
#
# 用法： bash bisect_materials.sh
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
CACHE=/root/work/jacfix/fixed/.jitcache          # 热 JIT 缓存，省 ~4 分钟

for TAG in iso_k iso_g iso_L; do
  D="$ROOT/$TAG"; rm -rf "$D"; mkdir -p "$D"; cd "$D"
  cp "$SRC" N.i
  cp /root/work/jacfix/base/columnar_seeds.csv .
  [ -d "$CACHE" ] && cp -r "$CACHE" .jitcache || true

  python3 - "$TAG" <<'PY'
import re, sys
tag = sys.argv[1]
lines = open("N.i", encoding="utf-8").read().split("\n")

def block_of(i):
    for j in range(i, max(0, i - 40), -1):
        m = re.match(r"\s*\[(\w+)\]", lines[j])
        if m:
            return m.group(1)
    return ""

want_k = tag in ("iso_k",)
want_g = tag in ("iso_g",)
want_L = tag in ("iso_L",)
n = 0
for i, ln in enumerate(lines):
    name = block_of(i) if ln.lstrip().startswith("expression = ") else ""
    if name == "kappa_aniso" and want_k:
        lines[i] = "    expression = '1.799943021e-06'"; n += 1
    elif name == "gamma_aniso" and want_g:
        lines[i] = "    expression = '1.499918283'"; n += 1
    elif name == "L2b" and want_L:
        lines[i] = "    expression = '1'"; n += 1
    elif name == "L2a" and want_L:
        lines[i] = "    expression = '(4.0/3.0)*232*exp(-3.234/(8.617e-5*T))/4.0e-6'"; n += 1
open("N.i", "w", encoding="utf-8").write("\n".join(lines))
print(f"  [{tag}] 替换 {n} 处")
PY
done

echo
echo "=== 并行跑三个 ==="
for TAG in iso_k iso_g iso_L; do
  ( cd "$ROOT/$TAG" && timeout 2400 "$MOOSE" -i N.i \
      Mesh/gen/nx=24 Mesh/gen/ny=12 \
      -pc_type lu -pc_factor_mat_solver_type mumps \
      -snes_test_jacobian > jac.log 2>&1 ) &
done
wait

echo
echo "=== 结果 ==="
printf "  %-10s %-18s %s\n" "变体" "||J-Jfd||/||J||" "说明"
printf "  %s\n" "------------------------------------------------------------------"
printf "  %-10s %-18s %s\n" "（全开）" "2.08202e-02" "κ/γ/L 都依赖 η"
printf "  %-10s %-18s %s\n" "（全关）" "1.64731e-09" "κ/γ/L 都不依赖 η"
for TAG in iso_k iso_g iso_L; do
  V=$(grep -aoE "Jfd\|\|_F/\|\|J\|\|_F = [0-9.eE+-]+" "$ROOT/$TAG/jac.log" 2>/dev/null | head -1 | grep -oE "[0-9.eE+-]+$")
  case $TAG in
    iso_k) DESC="只关 κ 的 η 依赖";;
    iso_g) DESC="只关 γ 的 η 依赖";;
    iso_L) DESC="只关 L 的 η 依赖";;
  esac
  printf "  %-10s %-18s %s\n" "$TAG" "${V:-（没出）}" "$DESC"
done
echo
echo "判读：**哪一个变体把比值拉回 ~1e-9，缺的导数就在那一个的材料链里。**"
