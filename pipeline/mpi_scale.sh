#!/bin/bash
# 【性能关键路径】MPI 扩展性测试 —— 从未测过的方向。
#
# 动机：
#   * 全尺寸单进程 MUMPS 约 30 分钟/步 -> 165 步 ≈ 80+ 小时/条轨迹，不可行
#   * 机器有 20 逻辑核，当前只用 3 个
#   * **MUMPS 本身是并行直接解**（MUMPS = MUltifrontal Massively Parallel Solver），
#     `mpiexec -n N` 会让它用并行多波前分解 —— 而分解正是瓶颈
#   * 此前测过 "AD + MPI -n 8 更慢"，但那是 **AD**；非 AD 的 MPI 从未测过
#
# 在 215x75 上测（内存安全，~500 MB/进程），2 个时间步，关掉 Exodus 避免 I/O 干扰。
# 测 n = 1 / 2 / 4 / 8，报每个配置的**墙钟时间**与**每次雅可比的耗时**。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/mpi_scale
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

echo "=== MPI 可用性 ==="
which mpiexec mpirun 2>/dev/null | head -2
mpiexec --version 2>&1 | head -2

cp /root/work/s1d_full/C_nonad.i base.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("base.i", encoding="utf-8").read()
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type'",
           s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps nonzero'", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 1.6e-5", s, flags=re.M)
s = re.sub(r"^  dtmax = .*$", "  dtmax = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$", "    dt = 4e-6", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
# 关掉 Exodus：本测试只测计算，不测 I/O
s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n  print_linear_residuals = false\n[]\n", s)
open("mpi.i", "w", encoding="utf-8").write(s)
print("  已生成 mpi.i：end_time=1.6e-5, dt=4e-6, 无 Exodus 输出")
PY

for N in 1 2 4 8; do
  mkdir -p "n$N"; cp mpi.i columnar_seeds.csv "n$N"/
done

echo
echo "=== 依次测 n=1,2,4,8（串行跑，避免互相干扰）==="
for N in 1 2 4 8; do
  echo "--- n=$N 开始 $(date +%H:%M:%S) ---"
  cd "$D/n$N" || continue
  if [ "$N" = "1" ]; then
    T0=$(date +%s)
    setsid --wait "$MOOSE" -i mpi.i > run.log 2>&1
    RC=$?
  else
    T0=$(date +%s)
    setsid --wait mpiexec -n $N "$MOOSE" -i mpi.i > run.log 2>&1
    RC=$?
  fi
  T1=$(date +%s)
  echo "  n=$N rc=$RC 墙钟=$((T1-T0))s"
  echo "    雅可比耗时: $(grep -a -oE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' run.log | sed 's/\x1b\[[0-9;]*m//g' | sed 's/.*\[ *//' | tr '\n' ' ')"
  echo "    收敛步: $(grep -ac 'Solve Converged' run.log)  内存峰值: $(grep -a -oE '\[ *[0-9]+ MB\]' run.log | tr -d '[] MB' | sort -n | tail -1) MB"
  cd "$D" || exit 1
done

echo
echo "================ MPI 扩展性汇总 ================"
printf "  %-6s %-10s %-14s %s\n" "n" "墙钟(s)" "相对加速" "雅可比均值(s)"
BASE=0
for N in 1 2 4 8; do
  L="$D/n$N/run.log"
  [ -f "$L" ] || continue
  J=$(grep -a -oE 'Computing Jacobian[^[]*\[ *[0-9.]+ s\]' "$L" | sed 's/.*\[ *//;s/ s\]//' | awk '{s+=$1; n++} END{if(n>0) printf "%.1f", s/n}')
  W=$(grep -aoE 'Finished Executing[^]]*\] \[[^]]*\]' "$L" | head -1 | grep -oE '[0-9.]+' | head -1)
  [ -z "$W" ] && W="?"
  [ "$N" = "1" ] && BASE="$W"
  if [ -n "$BASE" ] && [ "$BASE" != "?" ] && [ "$W" != "?" ]; then
    SP=$(awk -v b="$BASE" -v w="$W" 'BEGIN{if(w>0) printf "%.2fx", b/w; else print "?"}')
  else
    SP="?"
  fi
  printf "  %-6s %-10s %-14s %s\n" "$N" "$W" "$SP" "$J"
done
