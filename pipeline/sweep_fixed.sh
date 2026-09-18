#!/bin/bash
# 求解器扫描 —— 跑在**修正后**的 D 版输入上（核已与 GrainGrowth 动作逐位等价）。
#
# 为什么现在才做这件事：之前所有求解器调参都是在**错误的方程**上做的
# （缺 TimeDerivative、v 含自己、缺 variable_L），牛顿在第 0 次迭代就
# DIVERGED_LOCAL_MIN，根本没有可解的东西。修好核之后，牛顿能走 5 步、
# 残差降 5.3 倍，最后停在 DIVERGED_ITS 30 —— 这才轮到求解器调参。
#
# 试 4 种（都用原始 l_max_its=30 作对照，再加提上限与大重叠）：
#   S1 asm/ilu 原样（复现基线症状）
#   S2 asm/ilu + l_max_its=300 + l_tol=1e-5
#   S3 asm/ilu + 非零主元平移 + l_max_its=300
#   S4 hypre boomeramg（椭圆型标配）
#   S5 asm + sub_pc_factor_levels 2 + l_max_its=300
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_sweep

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./base.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re

CONFIGS = {
    "S1_asm_base": ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
                    "asm 31 preonly ilu 1", 30, "1e-6"),
    "S2_asm_300": ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
                   "asm 31 preonly ilu 1", 300, "1e-5"),
    "S3_asm_shift": ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap "
                     "-sub_pc_factor_shift_type -sub_pc_factor_shift_amount",
                     "asm 31 preonly ilu 1 nonzero 1e-8", 300, "1e-5"),
    "S4_hypre": ("-pc_type -pc_hypre_type -ksp_gmres_restart",
                 "hypre boomeramg 31", 300, "1e-5"),
    "S5_asm_lvl2": ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap "
                    "-sub_pc_factor_levels",
                    "asm 31 preonly ilu 2 2", 300, "1e-5"),
}

base = open("base.i", encoding="utf-8").read()
for tag, (iname, ivalue, lmax, ltol) in CONFIGS.items():
    s = base
    s = re.sub(r"^  petsc_options_iname = .*$",
               f"  petsc_options_iname = '{iname}'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$",
               f"  petsc_options_value = '{ivalue}'", s, flags=re.M)
    s = re.sub(r"^  l_max_its = .*$", f"  l_max_its = {lmax}", s, flags=re.M)
    s = re.sub(r"^  l_tol = .*$", f"  l_tol = {ltol}", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    # 逐变量残差
    if "[Debug]" not in s:
        s = s.replace("\n[Executioner]\n",
                      "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
    # 确认核已修好，否则这次扫描没意义
    assert s.count("type = TimeDerivative") == 8, f"{tag}: TimeDerivative 数量不对"
    assert "variable_L = true" in s, f"{tag}: 缺 variable_L"
    open(f"{tag}.i", "w", encoding="utf-8").write(s)
    print(f"  {tag}.i  (l_max_its={lmax})")
PY

for t in S1_asm_base S2_asm_300 S3_asm_shift S4_hypre S5_asm_lvl2; do
  mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/
done

echo "=== 并行跑 5 个配置 ==="
for t in S1_asm_base S2_asm_300 S3_asm_shift S4_hypre S5_asm_lvl2; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; \
    echo "  $t rc=$?" ) &
done
wait

echo
echo "================= 结果 ==================="
for t in S1_asm_base S2_asm_300 S3_asm_shift S4_hypre S5_asm_lvl2; do
  L="/root/work/s1d_sweep/$t/run.log"
  echo "--- $t ---"
  printf "   收敛步=%s   牛顿末次残差=" "$(grep -ac 'Solve Converged' "$L")"
  grep -a "Nonlinear |R|" "$L" | tail -1 | sed 's/.*= //' | sed 's/\x1b\[[0-9;]*m//g'
  echo "   线性求解状态:"
  grep -a "Linear solve" "$L" | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' \
    | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
  grep -a -m2 -E '\*\*\* ERROR|SUBPC|zero pivot' "$L" | sed 's/^/     /'
done
