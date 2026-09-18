#!/bin/bash
# AD 版（雅可比精确）之后，剩下的就是线性求解。批量并行试 4 种预条件子。
#
# 已知：
#   AD + l_max_its=30   牛顿单调下降但 2 次 DIVERGED_ITS 30
#   AD + l_max_its=300  牛顿到迭代 4（3.91->2.75e-05），仍有 2 次 DIVERGED_ITS 300
#   => 单纯加迭代数不够，需要更强的预条件子
#
# 4 种（都用 AD 版输入、end_time=2e-6）：
#   P1 asm + sub_pc_type lu,  overlap 1   <- 子域直接解，远比 ILU 稳健（首选）
#   P2 asm + sub_pc_type lu,  overlap 2   <- 更大子域
#   P3 asm + ilu + sub_pc_factor_levels 3 <- ILU 加强填充
#   P4 asm + sub_pc_type lu + l_max_its=1000
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_sb
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./base.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()
CFG = {
 "P1_asm_lu":     ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
                   "asm 31 preonly lu 1", 300, "1e-6"),
 "P2_asm_lu_ov2": ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
                   "asm 31 preonly lu 2", 300, "1e-6"),
 "P3_ilu_lvl3":   ("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap "
                   "-sub_pc_factor_levels",
                   "asm 31 preonly ilu 1 3", 300, "1e-6"),
 "P4_asm_lu_1000":("-pc_type -ksp_gmres_restart -sub_ksp_type -sub_pc_type -pc_asm_overlap",
                   "asm 31 preonly lu 1", 1000, "1e-6"),
}
for tag, (iname, ivalue, lmax, ltol) in CFG.items():
    s = base
    s = re.sub(r"^  petsc_options_iname = .*$", f"  petsc_options_iname = '{iname}'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", f"  petsc_options_value = '{ivalue}'", s, flags=re.M)
    s = re.sub(r"^  l_max_its = .*$", f"  l_max_its = {lmax}", s, flags=re.M)
    s = re.sub(r"^  l_tol = .*$", f"  l_tol = {ltol}", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 2e-6", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    if "[Debug]" not in s:
        s = s.replace("\n[Executioner]\n",
                      "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
    assert s.count("type = ADGrainGrowth") == 8 and "ADACInterface" in s
    open(f"{tag}.i", "w", encoding="utf-8").write(s)
    print(f"  {tag}.i  l_max_its={lmax}")
PY

for t in P1_asm_lu P2_asm_lu_ov2 P3_ilu_lvl3 P4_asm_lu_1000; do
  mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/
done

echo "=== 并行跑 4 种（20 核）==="
# 先停掉正在跑的 a3（它的线性求解反复失败，没必要继续占 CPU）
pgrep -f 'phase_field-opt -i A.i' > /tmp/p.txt 2>/dev/null
xargs -r kill -9 < /tmp/p.txt 2>/dev/null
sleep 2

for t in P1_asm_lu P2_asm_lu_ov2 P3_ilu_lvl3 P4_asm_lu_1000; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "================= 结果 ==================="
for t in P1_asm_lu P2_asm_lu_ov2 P3_ilu_lvl3 P4_asm_lu_1000; do
  L="/root/work/s1d_sb/$t/run.log"
  echo "--- $t ---"
  printf "   收敛步=%s\n" "$(grep -ac 'Solve Converged' "$L")"
  echo "   牛顿末 6 步:"
  grep -a "Nonlinear |R|" "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -6 | sed 's/^/     /'
  echo "   线性求解:"
  grep -a "Linear solve" "$L" | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' \
    | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
  grep -a -m2 -E '\*\*\* ERROR|SUBPC|zero pivot|out of memory' "$L" | sed 's/^/     /'
done
