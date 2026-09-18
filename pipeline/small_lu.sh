#!/bin/bash
# 拿真实矩阵，不再估算量级。
#
# 消融已锁定：病态在「L 依赖序参量」这条路径上（v1 关2b 收敛、v2 L各向同性收敛、
# v3 只关 kappa/gamma 仍卡）。但机制还没钉死 —— 因为量级估算显示
# dL/dgr_j * kappa * |grad eta| 与主导对角同量级，不足以单独解释 SUBPC_ERROR。
#
# 本实验在**小网格（20x8，约 1800 dof）**上做三件事：
#   1) MUMPS 直接解      —— 若奇异，PETSc 直接报零主元行号
#   2) -snes_test_jacobian —— 装配雅可比 vs 有限差分，判断"对不对"
#   3) 对比 v0(完整D) 与 v1(关2b) —— 差异只在 L 是否依赖 align4
# 小网格下 MUMPS 是秒级的，且有限差分可行（全尺寸做不了）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_small

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
for f in stage1_meltpool_c.i stage1_meltpool_d.i make_variants.py columnar_seeds.csv; do
  sed 's/\r$//' "/mnt/f/speed_up/pipeline/$f" > "$f"
done
python3 make_variants.py || exit 1

# 小网格 + 直接解 + 雅可比自检
python3 - <<'PY'
import re
for tag, src in (("C", "stage1_meltpool_c.i"), ("v0", "v0.i"), ("v1", "v1.i")):
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"^    nx = .*$", "    nx = 20", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", "    ny = 8", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 8", s, flags=re.M)
    # MUMPS 直接解 + 雅可比自检
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
               s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$",
               "  petsc_options_value = 'lu mumps 1'", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = S{tag}")
    s = s.replace("file_base = stage1c", f"file_base = S{tag}")
    open(f"S{tag}.i", "w", encoding="utf-8").write(s)
    print(f"  S{tag}.i")
PY

for t in C v0 v1; do
  mkdir -p "S$t"; cp "S$t.i" columnar_seeds.csv "S$t"/
done

echo "=== 并行跑 C / v0 / v1（小网格 + MUMPS + 雅可比自检）==="
for t in C v0 v1; do
  ( cd "$D/S$t" && setsid --wait "$MOOSE" -i "S$t.i" > run.log 2>&1; echo "  S$t rc=$?" ) &
done
wait

for t in C v0 v1; do
  echo "######## S$t ########"
  printf "  收敛步=%s\n" "$(grep -ac 'Solve Converged' /root/work/s1d_small/S$t/run.log)"
  echo "  雅可比自检 ||J-Jfd||/||J||:"
  grep -a -E "J - Jfd|Jacobian test|norm of matrix" /root/work/s1d_small/S$t/run.log | head -4 | sed 's/^/    /'
  echo "  牛顿:"
  grep -a "Nonlinear |R|" /root/work/s1d_small/S$t/run.log | head -6 | sed 's/^/    /'
  echo "  零主元/奇异/报错:"
  grep -a -m4 -E "zero pivot|Singular|zeros on the diagonal|ERROR|FACTOR|out of memory" \
    /root/work/s1d_small/S$t/run.log | sed 's/^/    /'
done
