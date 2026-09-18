#!/bin/bash
# 【B7】全尺寸（430×150）非 AD + ASM 的内存与速度 —— 决定"吞吐方案"
#
# 为什么关键：刚算出的战略结论 —— **吞吐受内存限制，不是受核数限制**。
#   全尺寸单进程 MUMPS 要 6.4 GB，21 GB 内存只能并发 3 条
#   MPI n=8 每核只有 0.34x 效率（饱和在 2.75x），8 核换 2.75 条当量
#   => 若 ASM 全尺寸只要 2-3 GB，就能并发 6-10 条，吞吐反超数倍
#
# 已知前提（§2.4）：ASM 与 MUMPS **同容差下解相同**（relL2 ~1e-15），
# 所以用 ASM 不牺牲物理，只牺牲"每迭代速度"。
#
# 与 bench_full_mumps.sh **同配置**（430×150、dt=1e-7 起步、end_time=8e-6、
# nl_abs_tol=1e-9），唯一差别是求解器 —— 这样两者可直接对比。
#
# 起始 dt 一律 1e-7（ROADMAP 附录 A 的坑）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/bench_full_asm
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_full/C_nonad.i src.i
cp /root/work/s1d_full/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("src.i", encoding="utf-8").read()
s = re.sub(r"^    nx = .*$", "    nx = 430", s, flags=re.M)
s = re.sub(r"^    ny = .*$", "    ny = 150", s, flags=re.M)
# ASM + ILU（与 solver_compare 的 B 同款），但容差取紧的 1e-9
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap'",
           s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'asm 31 preonly ilu 1'", s, flags=re.M)
s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
s = re.sub(r"^  end_time = .*$",  "  end_time = 8e-6", s, flags=re.M)
s = re.sub(r"^  dtmax = .*$",     "  dtmax = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$",      "    dt = 1e-7", s, flags=re.M)   # 附录 A
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
s = s.replace("file_base = Cnonad", "file_base = ba")
s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n  print_linear_residuals = false\n[]\n", s)
open("bench_asm.i", "w", encoding="utf-8").write(s)
print("  已生成 bench_asm.i: 430x150, ASM+ILU, nl_abs_tol=1e-9, dt=1e-7 起步")
PY

echo "=== 启动全尺寸 ASM 基准（RSS 看门狗阈值 9 GB）==="
setsid --wait "$MOOSE" -i bench_asm.i > run.log 2>&1 &
MPID=$!
PEAK=0
while kill -0 $MPID 2>/dev/null; do
  for P in $(pgrep -f 'bench_asm.i' 2>/dev/null); do
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    [ -n "$R" ] && [ "$R" -gt "$PEAK" ] 2>/dev/null && PEAK=$R
    if [ -n "$R" ] && [ "$R" -gt 9000000 ] 2>/dev/null; then
      echo "[看门狗] RSS 超过 9 GB（${R} kB），杀掉 $P"
      kill -9 $P 2>/dev/null
    fi
  done
  sleep 4
done
wait $MPID
RC=$?

echo
echo "================ 全尺寸 ASM 基准结果 ================"
echo "  退出码 = $RC"
echo "  **RSS 峰值 = $((PEAK/1024)) MB**"
echo "  --- MOOSE 自报内存（末 5 行）---"
grep -a -oE '\[ *[0-9]+ MB\]' run.log | tail -5 | sed 's/^/    /'
echo "  --- 时间步 ---"
grep -a '^Time Step' run.log | tail -6 | sed 's/^/    /'
echo "  --- 牛顿末 10 次 ---"
grep -a 'Nonlinear |R|' run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -10 | sed 's/^/    /'
echo "  --- 线性求解统计 ---"
grep -a 'Linear solve' run.log | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//' | sort | uniq -c | sort -rn | head -5 | sed 's/^/    /'
echo "  --- 报错 ---"
grep -a -m4 -E '\*\*\* ERROR|Aborting|out of memory' run.log | sed 's/^/    /'
echo
echo "  对照 MUMPS（同配置）：RSS 峰值 6418 MB，首步约 2839 s（坏 dt）后修正"
