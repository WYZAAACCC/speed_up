#!/bin/bash
# 【规划输入 2】决定生产用哪个求解器：MUMPS（精确 LU，慢但二次收敛）
#                     vs ASM/ILU（快，但残差卡 7e-7 地板）
#
# 为什么必须测：M2 证明 MUMPS 让非 AD 版二次收敛到 4.0e-10，而 ASM 只能到 7e-7。
# 但 MUMPS 全尺寸可能要 30+ 小时。**如果两者的解在物理上无差别**，就可以用快的 ASM。
#
# 判据：同一算例（215x75，非AD，到 end_time=4e-5）两种求解器跑完，
#       逐场比较最终解。若 max|Δgr_i| ~ 1e-7 量级 -> 地板无害 -> 用 ASM 生产。
#                                  若出现 O(0.1) 的差异 -> 地板有害 -> 必须 MUMPS。
#
# 注意 M2 当时的 time_step_interval=20 导致只存了初值，所以两个都重跑。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/slv_cmp
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_nonad.i base.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

def mk(name, pc_iname, pc_ivalue, nl_abs, tag):
    s = base
    s = re.sub(r"^  petsc_options_iname = .*$", f"  petsc_options_iname = '{pc_iname}'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", f"  petsc_options_value = '{pc_ivalue}'", s, flags=re.M)
    s = re.sub(r"^  nl_abs_tol = .*$", f"  nl_abs_tol = {nl_abs}", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 25", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$",   "  end_time = 4e-5", s, flags=re.M)
    s = re.sub(r"^  dtmax = .*$",      "  dtmax = 4e-6", s, flags=re.M)
    s = re.sub(r"^    dt = .*$",       "    dt = 1e-6", s, flags=re.M)
    s = re.sub(r"(time_step_interval = )\d+", r"\g<1>1", s)
    s = s.replace("file_base = Cnonad", f"file_base = {tag}")
    open(name, "w", encoding="utf-8").write(s)
    print(f"  {name}: pc='{pc_iname.split()[0]}' nl_abs_tol={nl_abs}")

# A = 精确 LU；B = 生产候选（ASM+ILU）；C = ASM 但苛求残差（看地板到底在哪）
mk("A.i", "-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type",
   "lu mumps nonzero", "1e-9", "A")
mk("B.i", "-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
   "asm 31 preonly ilu 1", "1e-6", "B")
PY

for T in A B; do mkdir -p "$T"; cp "$T.i" columnar_seeds.csv "$T"/; done

echo "=== 并行启动 A(MUMPS 精确) / B(ASM 生产候选) ==="
date
for T in A B; do
  ( cd "$T" && setsid --wait "$MOOSE" -i "$T.i" > run.log 2>&1; echo "$T rc=$?" >> "$D/rc.txt" ) &
done
wait
date

echo
echo "################ 求解器对比 ################"
for T in A B; do
  L="$D/$T/run.log"
  echo "--- $T ---"
  echo "  收敛步 = $(grep -ac 'Solve Converged' "$L")   线性失败 = $(grep -ac 'DIVERGED' "$L")"
  echo "  牛顿末 5 次:"
  grep -a 'Nonlinear |R|' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -5 | sed 's/^/    /'
  echo "  末 3 个时间步:"
  grep -a '^Time Step' "$L" | tail -3 | sed 's/^/    /'
  echo "  耗时:"
  grep -a -E 'Finished Solving|Finished Executing' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -1 | sed 's/^/    /'
  echo "  报错:"
  grep -a -m2 -E '\*\*\* ERROR|Aborting' "$L" | sed 's/^/    /'
done
echo
echo "  --- rc ---"; cat "$D/rc.txt" 2>/dev/null | sed 's/^/    /'
