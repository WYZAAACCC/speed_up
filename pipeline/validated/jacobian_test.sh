#!/bin/bash
# =============================================================================
# T1（验收矩阵）：溶质雅可比有限差分核对
# =============================================================================
#
# 判据（02_TEST_MATRIX.md T1）：有限差分相对误差 <= 1e-5，且日志中无
#                              `Missing coupled variables`
#
# 做法：在**小网格**的验证算例上跑 `-snes_test_jacobian`。
#   PETSc 会把组装出来的雅可比 J 与残差的有限差分 Jfd 比较，打印
#     ||J - Jfd||_F / ||J||_F
#   这个量衡量的是"雅可比里少没少项"，与解本身无关。
#
# ⚠ 为什么要用**小网格**：JIT 编译那几条巨型 parsed 表达式要 ~120 s
#   （实测 `--check-input` 就要 119.6 s），加上全尺寸装配，直接在生产网格上
#   跑 FD 核对会很贵。小网格不影响这条测试的有效性——缺项是**结构性**的，
#   不随网格变。
#
# 用法：
#   bash jacobian_test.sh <算例目录> <标签>
#   bash jacobian_test.sh /root/work/valid before
# =============================================================================
set -e

D="${1:?用法: jacobian_test.sh <算例目录> <标签>}"
TAG="${2:?缺少标签，例如 before / after}"
NX="${NX:-24}"
NY="${NY:-12}"
END="${END:-4e-7}"          # 2 个时间步：够触发一次完整装配，又不至于慢
TOL="${TOL:-1e-5}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
# ⚠ 【2026-09-20 修复】这里原来硬编码 MOOSE 自带的 `phase_field-opt`。
#   但**任何走完 jacfix 的生产输入都含自建核 `ACGrGrPolyJ`**，
#   用自带二进制会直接报 `'ACGrGrPolyJ' is not a registered object` 而中止
#   —— 也就是说本脚本对生产输入**一直是坏的**，而日志里那句话很容易
#   被当成"算例的问题"。自建 `gb_jac-opt` 是超集，对两种算例都安全 ⇒ 改成默认它。
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"

OUT="$D/jacobian_${TAG}"
rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
cp "$D/N.i" .
# ⚠ 必须带上 seeds 文件：PolycrystalVoronoi::precomputeGrainStructure 会读它，
#   缺了直接 mooseError（本项目已在这里栽过一次）。
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$D/$f" ] && cp "$D/$f" . || true
done

echo "=== T1 雅可比核对 [$TAG] ==="
echo "  算例：$D/N.i"
echo "  网格：${NX} x ${NY}（命令行覆盖；生成文件本身未动）"
echo "  时间：end_time = $END"
echo "  判据：||J - Jfd||/||J|| <= $TOL"
echo

set +e
$MOOSE -i N.i \
    Mesh/gen/nx="$NX" Mesh/gen/ny="$NY" \
    Executioner/end_time="$END" \
    -snes_test_jacobian "$TOL" > jacobian.log 2>&1
RC=$?
set -e

# --- 确认命令行覆盖真的生效（本项目踩过"以为改了其实没改"的坑）---
echo "--- 网格是否真的被改小 ---"
grep -aE "n_nodes|n_elem|Number of nodes|Number of elements" jacobian.log | head -4 || true
grep -aE "^\s+nx = |^\s+ny = " jacobian.log | head -4 || true
echo

# --- 判据 1：有限差分相对误差 ---
echo "--- 判据 1：雅可比 vs 有限差分 ---"
JD=$(grep -aE "Norm of matrix ratio|norm of matrix ratio|J - Jfd" jacobian.log | head -5 || true)
if [ -n "$JD" ]; then
  echo "$JD"
else
  echo "  （未找到 PETSc 的差异输出——检查 jacobian.log）"
fi
echo

# --- 判据 2：不得出现 Missing coupled variables ---
echo "--- 判据 2：Missing coupled variables ---"
NMC=$(grep -ac "Missing coupled variables" jacobian.log || true)
if [ "$NMC" -eq 0 ]; then
  echo "  OK：0 条"
else
  echo "  失败：$NMC 条告警"
  grep -a "Missing coupled variables" jacobian.log | sort -u | head -10
fi
echo

echo "--- MOOSE 退出码：$RC ---"
tail -5 jacobian.log
echo
echo "原始日志：$OUT/jacobian.log"
