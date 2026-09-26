#!/bin/bash
# 2D 求解器诊断：MUMPS（直接解）vs ASM/ILU+位移
# 判别逻辑：
#   MUMPS 过  ⇒ 物理/雅可比正确，问题只在预条件子 ⇒ 用位移或标度修
#   MUMPS 也挂 ⇒ 雅可比/方程有问题 ⇒ 回到代码查
set +u
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_2d}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
cd "$ROOT"
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv . 2>/dev/null

# --- 变体 A: MUMPS ---
python3 - <<'PY'
t = open("gibbs2d.i", encoding="utf-8", newline="").read()
old_i = "  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'"
old_v = "  petsc_options_value = 'asm      31                  preonly       ilu          1'"
assert old_i in t and old_v in t, "找不到 petsc 选项行"
a = t.replace(old_i, "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'") \
     .replace(old_v, "  petsc_options_value = 'lu       mumps'")
open("gibbs2d_mumps.i", "w", encoding="utf-8", newline="").write(a)

b = t.replace(old_i, "  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap -sub_pc_factor_shift_type'") \
     .replace(old_v, "  petsc_options_value = 'asm      31                  preonly       ilu          1                nonzero'")
open("gibbs2d_shift.i", "w", encoding="utf-8", newline="").write(b)
print("变体已生成: gibbs2d_mumps.i, gibbs2d_shift.i")
PY

for v in mumps shift; do
  echo "=================================================="
  echo " 变体 $v"
  echo "=================================================="
  timeout 1800 "$MOOSE" -i "gibbs2d_$v.i" Mesh/gen/nx=86 Mesh/gen/ny=30 \
      Executioner/end_time=2.0e-6 Outputs/exo/enable=false \
      Outputs/checkpoint/enable=false > "run_$v.log" 2>&1
  echo "rc=$?"
  nj=$(sed "s/\x1b\[[0-9;]*m//g" "run_$v.log" | grep -c 'JIT compile failed')
  nd=$(sed "s/\x1b\[[0-9;]*m//g" "run_$v.log" | grep -c 'DIVERGED')
  nc=$(sed "s/\x1b\[[0-9;]*m//g" "run_$v.log" | grep -c 'Solve Converged')
  echo "JIT失败=$nj  DIVERGED=$nd  SolveConverged=$nc"
  echo "--- 最后一个时间步 ---"
  sed "s/\x1b\[[0-9;]*m//g" "run_$v.log" | grep -E '^Time Step' | tail -2
  echo "--- 错误 ---"
  sed "s/\x1b\[[0-9;]*m//g" "run_$v.log" | grep -A4 -m1 '\*\*\* ERROR' | head -8
  cp -f "run_$v.log" "gibbs2d_$v.i" "$SAVE/" 2>/dev/null
done