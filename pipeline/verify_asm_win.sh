#!/bin/bash
# 【复测】全尺寸下 ASM 是否真的大幅快于 MUMPS。
#
# 动机：B7 的初步对比显示 ASM 的线性求解比 MUMPS 快约 36 倍，
# 与缩小算例（215×75，MUMPS 反而快 1.6 倍）的结论**相反**。
# 差异太大会改变生产配置，必须干净复测。
#
# 本次设计（**尽量排除争用与配置差异**）：
#   * 同一份输入，只差 petsc_options
#   * end_time 只要 2 步（dt=1e-7 起步），够量单次雅可比 + 单次线性求解
#   * **串行跑**（一个跑完再跑另一个），彻底排除并发争用
#   * 报：墙钟、雅可比均值、以及**推算的线性求解耗时**
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/verify_asm
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_nonad.i base.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

def mk(name, iname, ivalue, tag):
    s = base
    s = re.sub(r"^    nx = .*$", "    nx = 430", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", "    ny = 150", s, flags=re.M)
    s = re.sub(r"^  petsc_options_iname = .*$", f"  petsc_options_iname = '{iname}'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", f"  petsc_options_value = '{ivalue}'", s, flags=re.M)
    s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 2.5e-7", s, flags=re.M)   # 2 步
    s = re.sub(r"^  dtmax = .*$", "  dtmax = 4e-6", s, flags=re.M)
    s = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)
    s = s.replace("file_base = Cnonad", f"file_base = {tag}")
    s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n  print_linear_residuals = false\n[]\n", s)
    open(name, "w", encoding="utf-8").write(s)
    print(f"  {name}")

mk("asm.i",  "-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
   "asm 31 preonly ilu 1", "A")
mk("mumps.i","-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type",
   "lu mumps nonzero", "M")
PY

for T in asm mumps; do mkdir -p "$T"; cp "$T.i" columnar_seeds.csv "$T"/; done

echo
echo "=== 串行跑（先 ASM 后 MUMPS，排除争用）==="
for T in asm mumps; do
  echo "--- $T 开始 $(date +%H:%M:%S) ---"
  cd "$D/$T" || continue
  T0=$(date +%s)
  setsid --wait "$MOOSE" -i "$T.i" > run.log 2>&1
  RC=$?
  T1=$(date +%s)
  echo "  $T rc=$RC 墙钟=$((T1-T0))s"
  cd "$D" || exit 1
done

echo
echo "================ 干净复测结果 ================"
for T in asm mumps; do
  L="$D/$T/run.log"
  [ -f "$L" ] || continue
  W=$(sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Finished Executing[^]]*\] \[ *[0-9.]+ s\]' | grep -oE '[0-9.]+' | head -1)
  NJ=$(grep -ac 'Nonlinear |R|' "$L")
  JN=$(grep -ac 'Computing Jacobian' "$L")
  JS=$(sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aoE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1;n++} END{if(n>0)printf "%.1f", s/n; else print 0}')
  echo "--- $T ---"
  echo "  墙钟 = ${W} s   牛顿迭代 = $NJ   雅可比次数 = $JN   雅可比均值 = ${JS} s"
  awk -v w="$W" -v nj="$NJ" -v js="$JS" 'BEGIN{
    if (nj>0 && w>0 && js>0) {
      tot = w/nj;  lin = tot - js;
      printf "  每次牛顿迭代 = %.1f s  =  雅可比 %.1f s + 【线性求解 %.1f s】\n", tot, js, lin;
    }
  }'
  echo "  收敛步 = $(grep -ac 'Solve Converged' "$L")"
  grep -a 'Nonlinear |R|' "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -3 | sed 's/^/    /'
done
echo
echo "  【关键判据】比较两者的"线性求解"耗时。若 ASM 快数倍以上，"
echo "             则生产配置应从 MPI+MUMPS 改为 MPI+ASM（内存也只有一半）。"
