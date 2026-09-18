#!/bin/bash
# 雅可比修好之后（跨序参量项不再缺失），预条件子崩了 —— 这很常见：
# **正确的**雅可比比缺项的雅可比更稠密、更刚，ILU/ASM 反而扛不住。
# 这是纯求解器工程问题，不是物理/代码错误。
#
# 依次试 4 种配置，每种只跑 2 步（end_time=1e-6），看哪种能收敛：
#   S1 hypre boomeramg   —— 椭圆型问题的标准解法，内存省
#   S2 hypre + ASM 混合  —— 块内 AMG、块间加性 Schwarz
#   S3 MUMPS 直接解      —— 决定性：若奇异，PETSc 会报零主元行号
#   S4 ASM+ILU 多重叠    —— 加强版 ILU
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
cd /root/work/s1d_w || exit 1

mk() {  # $1=名字  $2=petsc_options_iname  $3=petsc_options_value
python3 - "$1" "$2" "$3" <<'PY'
import re, sys
name, iname, ivalue = sys.argv[1], sys.argv[2], sys.argv[3]
s = open("try3.i", encoding="utf-8").read()      # try3.i 已含 show_var_residual_norms + 材料极值
s = re.sub(r"^  petsc_options_iname = .*$", f"  petsc_options_iname = '{iname}'", s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", f"  petsc_options_value = '{ivalue}'", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
open(f"{name}.i", "w", encoding="utf-8").write(s)
PY
}

mk s1_hypre "-pc_type -pc_hypre_type -ksp_gmres_restart" "hypre boomeramg 31"
mk s2_hybrid "-pc_type -pc_hypre_type -ksp_gmres_restart -sub_pc_type -pc_asm_overlap" "asm boomeramg 31 hypre 2"
mk s3_lu "-pc_type -pc_factor_mat_solver_type" "lu mumps"
mk s4_asm "-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap -sub_pc_factor_levels" "asm 31 preonly ilu 3 1"

for t in s1_hypre s2_hybrid s3_lu s4_asm; do
  echo "################ $t ################"
  grep -m1 "petsc_options_value" "$t.i"
  timeout 1200 "$MOOSE" -i "$t.i" > "$t.log" 2>&1
  echo "  退出码 $?"
  printf "  收敛步数="; grep -ac "Solve Converged" "$t.log"
  echo "  线性求解状态（去重计数）:"
  grep -a "Linear solve" "$t.log" | sed 's/^ *//' | sort | uniq -c | sort -rn | head -4 | sed 's/^/    /'
  echo "  第 1 次牛顿的逐变量残差:"
  grep -a -A12 "individual variables" "$t.log" | head -13 | sed 's/^/    /'
  echo "  报错/零主元:"
  grep -a -m3 -E '\*\*\* ERROR|zero pivot|Singular|SUBPC|DIVERGED' "$t.log" | sed 's/^/    /'
  echo
done
