#!/bin/bash
# 【B8】MPI 下**每条算例的总内存** —— 决定"MPI 多核"vs"多开单进程"哪个吞吐高
#
# 为什么必须测：
#   吞吐 = 并发条数 × 单条速度，受 21 GB 内存与 20 核双重约束。
#   已知：单进程 MUMPS 全尺寸 6.4 GB（只能并发 3 条）、单进程 ASM 3.3 GB（能并发 5-6 条）
#   MPI n=8 单条速度 2.75x，但**整条算例占多少内存未知**：
#     MUMPS 会把矩阵分布到各进程 => 每进程可能只 1-1.5 GB，整条约 8-12 GB
#     若如此，只能并发 1-2 条，MPI 方案反而更差
#
# MUMPS 的内存峰值出现在**第一次分解**，所以只跑 1-2 个时间步就够。
# 全尺寸 430x150，n=8，dt=1e-7 起步（附录 A）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/bench_mpi_mem
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_nonad.i src.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("src.i", encoding="utf-8").read()
s = re.sub(r"^    nx = .*$", "    nx = 430", s, flags=re.M)
s = re.sub(r"^    ny = .*$", "    ny = 150", s, flags=re.M)
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type'",
           s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps nonzero'", s, flags=re.M)
s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
s = re.sub(r"^  end_time = .*$",  "  end_time = 2.5e-7", s, flags=re.M)  # 2 步足够拿到分解峰值
s = re.sub(r"^  dtmax = .*$",     "  dtmax = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$",      "    dt = 1e-7", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
s = s.replace("file_base = Cnonad", "file_base = bm")
s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n  print_linear_residuals = false\n[]\n", s)
open("bm.i", "w", encoding="utf-8").write(s)
print("  已生成 bm.i: 430x150, MPI n=8, MUMPS, end_time=2.5e-7")
PY

echo "=== 启动 MPI n=8 全尺寸（测整条算例总内存）==="
setsid --wait mpiexec -n 8 "$MOOSE" -i bm.i > run.log 2>&1 &
MPID=$!
PEAK_SUM=0
while kill -0 $MPID 2>/dev/null; do
  SUM=0
  for P in $(pgrep -f 'bm.i' 2>/dev/null); do
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    [ -n "$R" ] && SUM=$((SUM + R))
  done
  [ "$SUM" -gt "$PEAK_SUM" ] 2>/dev/null && PEAK_SUM=$SUM
  sleep 3
done
wait $MPID
RC=$?

echo
echo "================ MPI n=8 全尺寸内存 ================"
echo "  退出码 = $RC"
echo "  **整条算例 RSS 峰值（8 进程求和）= $((PEAK_SUM/1024)) MB ≈ $((PEAK_SUM/1024/1024)) GB**"
echo "  --- MOOSE 自报每进程内存（末 6 行）---"
grep -a -oE '\[ *[0-9]+ MB\]' run.log | tail -6 | sed 's/^/    /'
echo "  --- 时间步 ---"
grep -a '^Time Step' run.log | tail -3 | sed 's/^/    /'
echo "  --- 牛顿末 6 次 ---"
grep -a 'Nonlinear |R|' run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -6 | sed 's/^/    /'
echo "  --- 报错 ---"
grep -a -m3 -E '\*\*\* ERROR|Aborting|out of memory' run.log | sed 's/^/    /'
echo
echo "  === 对照 ==="
echo "    单进程 MUMPS 全尺寸: 内存峰值 6418 MB, 速度 1.00x"
echo "    单进程 ASM   全尺寸: 内存峰值 3281 MB, 速度待测(缩小算例上约 0.6x)"
echo
echo "  判据：若整条 MPI 算例 <= 3 GB，则 MPI n=8 可并发 2-4 条，吞吐 5.5-11 单核当量，最优；"
echo "        若 >= 8 GB，则只能并发 1 条，吞吐 2.75，不如单进程 ASM 的约 3-3.6。"
