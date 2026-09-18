#!/bin/bash
# 上一轮扫描的结论 + 修正：
#   S2 (asm/ilu, l_max_its=300, **l_tol=1e-5**) 线性求解已不再失败，
#   但牛顿停在残差地板 7.32e-07（迭代 13/14/15 = 7.391/7.326/7.319e-07）。
#
# 地板的原因不是雅可比错误，而是 **l_tol 放得太宽**：
#   非精确牛顿的可达残差下限由线性求解精度决定，l_tol 必须 <= nl_rel_tol，
#   否则牛顿步的方向误差把残差钉住。C 版用 l_tol=1e-6 能到 9.2e-08。
# 所以正确组合是 l_max_its 提上去、**l_tol 保持 1e-6**（我上一轮同时放宽两者，错了）。
#
# 本脚本跑三个：
#   T1 asm/ilu, l_max_its=300, l_tol=1e-6   <- 原则性的修法
#   T2 asm/ilu, l_max_its=300, l_tol=1e-8   <- 更紧，做对照
#   T3 同 T1 但 l_max_its=1000              <- 看是否还需要更多线性迭代
# 外加 verify_jac_fixed.sh：小网格 -snes_test_jacobian，
#   判定核修好后 ||J-Jfd||/||J|| 是否从 0.055 回落到 C 的 ~1e-6。
#
# 注意：不用 pkill -f（会杀自己的 shell）。用 PID 文件 + xargs。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_ltol

# 先停掉上一轮卡在地板上的扫描
pgrep -f "phase_field-opt -i" > /tmp/mpids.txt 2>/dev/null
xargs -r kill -9 < /tmp/mpids.txt 2>/dev/null
sleep 3
echo "已停掉旧进程，剩余 $(pgrep -cf 'phase_field-opt -i')"

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./base.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()
CFG = {
    "T1_ltol1e6": (300, "1e-6"),
    "T2_ltol1e8": (300, "1e-8"),
    "T3_its1000": (1000, "1e-6"),
}
for tag, (lmax, ltol) in CFG.items():
    s = base
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -ksp_gmres_restart -sub_ksp_type "
               "-sub_pc_type -pc_asm_overlap'", s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$",
               "  petsc_options_value = 'asm 31 preonly ilu 1'", s, flags=re.M)
    s = re.sub(r"^  l_max_its = .*$", f"  l_max_its = {lmax}", s, flags=re.M)
    s = re.sub(r"^  l_tol = .*$", f"  l_tol = {ltol}", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    if "[Debug]" not in s:
        s = s.replace("\n[Executioner]\n",
                      "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
    assert s.count("type = TimeDerivative") == 8, f"{tag}: 核前提不满足"
    assert "variable_L = true" in s, f"{tag}: 缺 variable_L"
    open(f"{tag}.i", "w", encoding="utf-8").write(s)
    print(f"  {tag}.i  l_max_its={lmax} l_tol={ltol}")
PY

for t in T1_ltol1e6 T2_ltol1e8 T3_its1000; do
  mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/
done

echo "=== 并行跑 T1/T2/T3 ==="
for t in T1_ltol1e6 T2_ltol1e8 T3_its1000; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "================= 结果 ==================="
for t in T1_ltol1e6 T2_ltol1e8 T3_its1000; do
  L="/root/work/s1d_ltol/$t/run.log"
  echo "--- $t ---"
  printf "   收敛步=%s\n" "$(grep -ac 'Solve Converged' "$L")"
  echo "   牛顿轨迹:"
  grep -a "Nonlinear |R|" "$L" | sed 's/\x1b\[[0-9;]*m//g' | tail -8 | sed 's/^/     /'
  echo "   线性求解次数/状态:"
  grep -a "Linear solve" "$L" | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' \
    | sort | uniq -c | sort -rn | head -3 | sed 's/^/     /'
done

echo
echo "################ 独立判定：修正版雅可比是否正确 ################"
bash /root/work/vj.sh 2>&1 | tail -25
