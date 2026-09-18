#!/bin/bash
# 加速基准：找能真正吃满 CPU 且更快的配置。
#
# 现状：串行 asm/ilu，MOOSE 占 1 核（99.3%），20 核里用 1 核 -> 5% 利用率，
# 约 3.4 分钟/步。全量 325 步要 18 小时。
#
# 为什么 MPI 昨晚更慢（新认识）：**`-pc_type asm` 在串行下退化成"整矩阵 ILU"**
#   （-pc_asm_blocks 未设 -> 1 块 = 全矩阵），是强预条件子；MPI 下变成
#   8 个局部 ILU + 重叠，强度大降 -> 迭代数暴增。所以那是**预条件子质量问题，
#   不是并行扩展性问题**，有救。
#
# 最可能赢的是**直接解**：710k 自由度在 2D 下直接分解是秒级，而现在是
# 最多 300 次 GMRES。四种都跑 10 步（end_time=2e-5）测墙钟：
#   B0 serial asm/ilu              （基线，= 现在生产跑的配置）
#   B1 serial MUMPS 直接解
#   B2 MPI -n 4 + MUMPS
#   B3 MPI -n 8 + MUMPS
#   B4 MPI -n 8 + asm/overlap3 + sub_pc_type lu（更强并行预条件子）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_bench
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_nonad/N.i ./base.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()
s = re.sub(r"^  end_time = .*$", "  end_time = 2e-5", base, flags=re.M)
s = s.replace("file_base = N", "file_base = base")
open("base10.i", "w", encoding="utf-8").write(s)

CFG = {
 "B1_mumps":   ("-pc_type -pc_factor_mat_solver_type",
                "lu mumps"),
 "B2_mpi4_mumps": (None, None),
 "B3_mpi8_mumps": (None, None),
 "B4_mpi8_asm":("-pc_type -ksp_gmres_restart -pc_asm_overlap -sub_pc_type -sub_ksp_type",
                "asm 31 3 lu preonly"),
}
for tag, (iname, ivalue) in CFG.items():
    t = s
    if iname:
        t = re.sub(r"^  petsc_options_iname = .*$", f"  petsc_options_iname = '{iname}'", t, flags=re.M)
        t = re.sub(r"^  petsc_options_value = .*$", f"  petsc_options_value = '{ivalue}'", t, flags=re.M)
    t = t.replace("file_base = base", f"file_base = {tag}")
    open(f"{tag}.i", "w", encoding="utf-8").write(t)
print("已生成 B1/B3/B4（B2 复用 B3 输入换 -n 4）")
PY

for t in B1_mumps B2_mpi4_mumps B3_mpi8_mumps B4_mpi8_asm; do
  mkdir -p "$t"; cp B3_mpi8_mumps.i columnar_seeds.csv "$t"/ 2>/dev/null
done
cp B1_mumps.i B1_mumps/ 2>/dev/null
cp B4_mpi8_asm.i B4_mpi8_asm/ 2>/dev/null
cp B3_mpi8_mumps.i B2_mpi4_mumps/ 2>/dev/null
cp B1_mumps.i B2_mpi4_mumps/ 2>/dev/null   # B2 用 MUMPS 输入但 -n 4

echo "=== 基线 B0（串行 asm/ilu，即当前生产配置）==="
mkdir -p B0_serial && cp base10.i B0_serial/ && cp columnar_seeds.csv B0_serial/
( cd B0_serial && setsid --wait "$MOOSE" -i base10.i > run.log 2>&1 ) &
P0=$!

echo "=== 其余并行启动 ==="
( cd B1_mumps && setsid --wait "$MOOSE" -i B1_mumps.i > run.log 2>&1 ) & P1=$!
( cd B2_mpi4_mumps && setsid --wait mpiexec -n 4 "$MOOSE" -i B3_mpi8_mumps.i > run.log 2>&1 ) & P2=$!
( cd B3_mpi8_mumps && setsid --wait mpiexec -n 8 "$MOOSE" -i B3_mpi8_mumps.i > run.log 2>&1 ) & P3=$!
( cd B4_mpi8_asm && setsid --wait mpiexec -n 8 "$MOOSE" -i B4_mpi8_asm.i > run.log 2>&1 ) & P4=$!

wait $P0 $P1 $P2 $P3 $P4 2>/dev/null
echo
echo "================= 结果（10 步墙钟）================="
for t in B0_serial B1_mumps B2_mpi4_mumps B3_mpi8_mumps B4_mpi8_asm; do
  L="/root/work/s1d_bench/$t/run.log"
  NS=$(grep -ac 'Solve Converged' "$L" 2>/dev/null)
  echo "--- $t ---  收敛步=$NS"
  grep -a -m2 -E '\*\*\* ERROR|out of memory|Aborting|MPI_ABORT' "$L" 2>/dev/null | head -2 | sed 's/^/    /'
  grep -a "Linear solve" "$L" 2>/dev/null | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' | sort | uniq -c | sort -rn | head -2 | sed 's/^/    /'
done
