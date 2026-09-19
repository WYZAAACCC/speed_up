#!/bin/bash
# =============================================================================
# 探针：搞清 PETSc 的 -snes_test_jacobian 到底能吐出哪些矩阵/数值
# =============================================================================
# 目的：设计 T1 的新判据。需要知道能否拿到
#   (a) 解析雅可比 J 本身   (b) 有限差分雅可比 Jfd   (c) 逐个 (行,列) 的差值
# 只有拿到 J 与 Jfd，才能算**逐列归一化**的相对误差 —— 那才是对"缺项"敏感的判据。
#
# 用 phase_field-opt（原版 MOOSE），不受自建 app 编译影响。
# 用 MOOSE 自己 PetscJacobianTester 的**快速求解器设置**：
#   -snes_type ksponly -ksp_type preonly -pc_type none -snes_convergence_test skip
# 这让它不做非线性迭代、只做**初始态一次**装配 —— 实测比默认快两个数量级。
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BASE="${BASE:-/root/work/prod_merged}"
MOOSE=/root/moose/modules/phase_field/phase_field-opt
OUT=/root/work/t1probe
rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"

cp "$BASE/N.i" .
for f in columnar_seeds.csv aniso_block.i; do
  [ -f "$BASE/$f" ] && cp "$BASE/$f" .
done

FAST=(-snes_test_jacobian -snes_force_iteration
      -snes_type ksponly -ksp_type preonly -pc_type none
      -snes_convergence_test skip
      Outputs/exodus=false Executioner/end_time=4e-7)

echo "=== 探针 1：默认 view，看输出格式 ==="
timeout 1800 "$MOOSE" -i N.i "${FAST[@]}" -snes_test_jacobian_view > v1.log 2>&1 || true
echo "  退出码 $?  日志 $(wc -l < v1.log) 行"
echo "  --- PETSc 打印的比值行 ---"
grep -a "J - Jfd\|Norm of matrix\|norm of matrix" v1.log | head -5
echo "  --- view 的行格式（前 3 行）---"
grep -a "^row " v1.log | head -3 | cut -c1-200
echo "  --- 有多少行有差异 ---"
grep -ac "^row " v1.log || echo 0

echo
echo "=== 探针 2：display 选项 ==="
timeout 1800 "$MOOSE" -i N.i "${FAST[@]}" \
    -snes_test_jacobian_display -snes_test_jacobian_display_threshold 1e-12 \
    > v2.log 2>&1 || true
echo "  退出码 $?  日志 $(wc -l < v2.log) 行"
grep -a "J - Jfd\|Jfd\|Jacobian" v2.log | head -8

echo
echo "=== 探针 3：能不能 dump 解析雅可比 J ==="
for opt in "-ksp_view_mat" "-snes_view" ; do
  timeout 900 "$MOOSE" -i N.i "${FAST[@]}" -pc_type lu $opt > "v3_$(echo $opt|tr -d '-').log" 2>&1 || true
  echo "  $opt -> $(wc -l < v3_$(echo $opt|tr -d '-').log) 行"
done

echo
echo "=== 探针 4：误差阈值控制（PETSc 的 -snes_test_jacobian 是 h 还是阈值？）==="
timeout 900 "$MOOSE" -i N.i "${FAST[@]}" -snes_test_jacobian 1e-3 > v4a.log 2>&1 || true
grep -a "J - Jfd" v4a.log | head -3

echo
echo "跑完了。日志在 $OUT"
