#!/bin/bash
# 【C1 验证】改了 c0（0.35->0.036）与 k（0.5->0.63，经 A_part 0.45->0.264）后：
#   1. 重新生成 stage1_meltpool_d.i
#   2. 跑一个缩小算例，确认**仍能收敛**
#   3. 确认溶质分凝方向与量级合理（固相贫化、液相富集）
#
# 判据：
#   * 牛顿二次收敛、无 DIVERGED
#   * c_min < c0 < c_max（固相贫 V、液相富 V，k<1 的必然结果）
#   * c_min/c_max 量级与 k=0.63 相符（不苛求精确，精确验证已由 1D 算例 verify_partition.i 给出）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/c1
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# --- 1. 用改过的 c 版重新生成 d 版 ---
# 【关键陷阱】必须用**非 AD** 版生成器！
#   pipeline/ 里的是 AD 版（ADTimeDerivative/ADGrainGrowth/ADACInterface），
#   而 AD 版有已知的"牛顿线性爬行"问题（每迭代只降约 4%），会 DIVERGED_MAX_IT。
#   非 AD 版在 /root/work/bak/。
#   我第一版验证就是踩了这个坑：把参数改动误判成"k=0.63 导致不收敛"。
cp /root/work/bak/gen_aniso.py .
cp /root/work/bak/splice_aniso.py .
echo "  生成器来源: /root/work/bak （非 AD 版）"
echo "  自检: splice 里 AD 核出现次数 = $(grep -c 'ADTimeDerivative\|ADGrainGrowth\|ADACInterface' splice_aniso.py) （应为 0）"
sed 's/\r$//' /mnt/f/speed_up/pipeline/stage1_meltpool_c.i > stage1_meltpool_c.i
sed 's/\r$//' /mnt/f/speed_up/pipeline/columnar_seeds.csv > columnar_seeds.csv

conda activate ml
python3 gen_aniso.py --op-num 8 --out aniso_block.i > gen.log 2>&1 || { echo "gen 失败"; tail -5 gen.log; exit 1; }
python3 splice_aniso.py >> gen.log 2>&1 || { echo "splice 失败"; tail -5 gen.log; exit 1; }
conda activate moose
[ -f stage1_meltpool_d.i ] || { echo "没生成 d.i"; exit 1; }

echo "=== 确认新参数已进入 d.i ==="
grep -n "value = 0.036\|constant_expressions = '0.9 0.036 0.264'" stage1_meltpool_d.i | sed 's/^/  /'

# --- 2. 缩小算例短跑 ---
python3 - <<'PY'
import re
s = open("stage1_meltpool_d.i", encoding="utf-8").read()
s = re.sub(r"^    nx = .*$", "    nx = 215", s, flags=re.M)
s = re.sub(r"^    ny = .*$", "    ny = 75", s, flags=re.M)
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -pc_factor_shift_type'", s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps nonzero'", s, flags=re.M)
s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 20", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$", "    dt = 1e-7", s, flags=re.M)   # ROADMAP 附录 A
s = s.replace("file_base = stage1d", "file_base = c1")
s = re.sub(r"(time_step_interval = )\d+", r"\g<1>5", s)
open("c1.i", "w", encoding="utf-8").write(s)
print("  c1.i: 215x75, MUMPS, nl_abs_tol=1e-9, dt=1e-7 起步, end_time=4e-6")
PY

mkdir -p run && cp c1.i columnar_seeds.csv run/
echo
echo "=== 运行 ==="
cd run && setsid --wait "$MOOSE" -i c1.i > run.log 2>&1
RC=$?
echo "  rc=$RC  收敛步=$(grep -ac 'Solve Converged' run.log)  DIVERGED=$(grep -ac 'DIVERGED' run.log)"

echo
echo "================ C1 验证结果 ================"
echo "  --- 牛顿末 6 次 ---"
grep -a 'Nonlinear |R|' run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -6 | sed 's/^/    /'
echo "  --- 溶质分凝（末行）---"
if [ -f c1_out.csv ]; then
  head -1 c1_out.csv | tr ',' '\n' | grep -nE 'c_max|c_min|c_solid|total_solute|liquid_frac' | sed 's/^/    列 /'
  tail -1 c1_out.csv | tr ',' '\n' | sed 's/^/    /'
else
  echo "    无 CSV"
fi
echo "  --- 报错 ---"
grep -a -m3 -E '\*\*\* ERROR|Aborting' run.log | sed 's/^/    /'
