#!/bin/bash
# "缩小但完整"的算例：验证**完整配置**的正确性与收敛性。
#
# 保留全部结构：8 个序参量、柱状种子、熔池 + 移动激光、溶质 Cahn-Hilliard、
# 真实 Rosenthal 温度场、真实 2a（取向差加权 kappa/gamma/L）+ 2b（热梯度对齐）。
# 只缩网格。
#
# 【为什么分两级】`-snes_test_jacobian` 要对**每个自由度**做一次残差求值：
#   全尺寸 710k DOF -> 几小时，做不了。
#   所以：
#     J 级：网格 43x15（~7.7k DOF），开 -snes_test_jacobian -> 验证**雅可比是否正确**
#           这是唯一能证明"8 序参量跨项耦合的雅可比对不对"的手段
#     C 级：网格 215x75（dx=2e-6，约 4 倍便宜），不开 test_jacobian
#           -> 验证**完整配置能否连续收敛多步**
#
# 两级的 AD / 非 AD 都跑，形成对照：
#     AD  ：雅可比应精确（最小算例已测 1e-7）
#     非AD：已知 ACGrGrPoly 丢 dL/deta_j -> 应看到误差 ~1e-3
#
# 【诚实标注的局限】215x75 时 dx=2e-6，而界面宽 int_width=4e-6 -> 界面只跨
# 2 个单元（原算例是 4 个）。所以 C 级验证的是**求解器与耦合结构**，
# 不是定量物理精度。J 级网格更粗，界面跨不到 1 个单元，但雅可比自检
# 比的是"装配矩阵 vs 有限差分"，与界面分辨率无关。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_full
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

# ---- 非 AD 版（含已修好的核）----
cp /root/work/bak/gen_aniso.py /root/work/bak/splice_aniso.py .
cp /root/work/s1d_w/stage1_meltpool_c.i .
cp /root/work/s1d_w/columnar_seeds.csv .
conda activate ml
python3 gen_aniso.py --op-num 8 --out aniso_block.i > gen.log 2>&1 || { echo "gen 失败"; tail -4 gen.log; exit 1; }
python3 splice_aniso.py >> gen.log 2>&1 || { echo "splice 失败"; tail -4 gen.log; exit 1; }
mv stage1_meltpool_d.i base_nonad.i
conda activate moose

# ---- AD 版（pipeline 里当前那份）----
cp /root/work/s1d_w/aniso_block.i ./ 2>/dev/null || true
cp /mnt/f/speed_up/pipeline/gen_aniso.py /mnt/f/speed_up/pipeline/splice_aniso.py .
conda activate ml
python3 gen_aniso.py --op-num 8 --texture random --out aniso_block.i > gen_ad.log 2>&1 || { echo "AD gen 失败"; tail -4 gen_ad.log; exit 1; }
python3 splice_aniso.py >> gen_ad.log 2>&1
mv stage1_meltpool_d.i base_ad.i
conda activate moose

python3 - <<'PY'
import re
def mk(src, dst, nx, ny, tmax, jac, tag):
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"^    nx = .*$", f"    nx = {nx}", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", f"    ny = {ny}", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", f"  end_time = {tmax}", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 12", s, flags=re.M)
    s = re.sub(r"^  l_max_its = .*$", "  l_max_its = 300", s, flags=re.M)
    s = re.sub(r"^  l_tol = .*$", "  l_tol = 1e-8", s, flags=re.M)
    s = re.sub(r"^  nl_rel_tol = .*$", "  nl_rel_tol = 1e-10", s, flags=re.M)
    s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
    s = re.sub(r"^  dtmax = .*$", "  dtmax = 4e-6", s, flags=re.M)
    if jac:
        s = re.sub(r"^  petsc_options_iname = .*$",
                   "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
                   s, flags=re.M)
        s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps 1'", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    s = re.sub(r"(time_step_interval = )\d+", r"\g<1>20", s)
    open(dst, "w", encoding="utf-8").write(s)
    n_dt = s.count("type = TimeDerivative") + s.count("type = ADTimeDerivative")
    n_gg = s.count("type = ACGrGrPoly") + s.count("type = ADGrainGrowth")
    print(f"  {dst}: nx={nx} ny={ny} 序参量核={n_gg} TimeDerivative={n_dt} "
          f"test_jac={jac} AD={'ADGrainGrowth' in s}")

mk("base_ad.i",     "J_ad.i",   43, 15, 4e-6, True,  "Jad")
mk("base_nonad.i",  "J_nonad.i",43, 15, 4e-6, True,  "Jnonad")
mk("base_ad.i",     "C_ad.i",  215, 75, 4e-5, False, "Cad")
mk("base_nonad.i",  "C_nonad.i",215,75, 4e-5, False, "Cnonad")
PY

for t in J_ad J_nonad C_ad C_nonad; do
  mkdir -p "$t"; cp "${t}.i" columnar_seeds.csv "$t"/
done

echo "=== 并行跑 4 个（J 级 2 个 + C 级 2 个）==="
for t in J_ad J_nonad C_ad C_nonad; do
  ( cd "$t" && setsid --wait "$MOOSE" -i "${t}.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "################ J 级：雅可比正确性 ################"
for t in J_ad J_nonad; do
  echo "--- $t ---"
  grep -a "J - Jfd" "/root/work/s1d_full/$t/run.log" 2>/dev/null | head -3 | sed 's/^/  /'
  grep -a -m2 -E '\*\*\* ERROR|Aborting' "/root/work/s1d_full/$t/run.log" 2>/dev/null | sed 's/^/  /'
done

echo
echo "################ C 级：完整配置的收敛性 ################"
for t in C_ad C_nonad; do
  L="/root/work/s1d_full/$t/run.log"
  echo "--- $t ---"
  printf "  收敛步=%s\n" "$(grep -ac 'Solve Converged' "$L" 2>/dev/null)"
  echo "  牛顿末 6 步:"
  grep -a "Nonlinear |R|" "$L" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | tail -6 | sed 's/^/    /'
  echo "  线性求解:"
  grep -a "Linear solve" "$L" 2>/dev/null | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' | sort | uniq -c | sort -rn | head -3 | sed 's/^/    /'
  echo "  时间步:"
  grep -a "^Time Step" "$L" 2>/dev/null | tail -3 | sed 's/^/    /'
done
