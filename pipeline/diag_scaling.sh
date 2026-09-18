#!/bin/bash
# 【诊断】为什么 |R|=1e-6 会对应 2e-3 的解误差？
#
# 假设：残差**全局范数**被某个量纲大的变量主导（`w` 是化学势，量级可能远大于 η~O(1)），
#       所以把 nl_abs_tol 从 1e-6 收到 1e-9 时，实际上主要是在收紧 w 的方程，
#       而 η 的方程早就"够准"了 —— 反过来说，**在 1e-6 时 η 可能还远没收敛**。
#
# 测法：跑 2 个时间步，开 show_var_residual_norms，看**逐变量残差**在
#       收敛判定的那一刻各是多少。若 w 的残差比 gr* 大几个数量级，假设成立。
#
# 如果假设成立，正确的修法是**给变量做 scaling**（[Variables] scaling = ...）
# 或用基于**解增量**的判据 nl_rel_step_tol，而不是一味收紧 nl_abs_tol。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/diag_scale
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/slv_cmp/B/B.i base.i
cp /root/work/slv_cmp/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("base.i", encoding="utf-8").read()
s = re.sub(r"^  end_time = .*$", "  end_time = 8e-6", s, flags=re.M)
s = re.sub(r"^  dtmax = .*$", "  dtmax = 4e-6", s, flags=re.M)
s = re.sub(r"^    dt = .*$", "    dt = 4e-6", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 30", s, flags=re.M)
s = re.sub(r"\[Outputs\][\s\S]*$", "[Outputs]\n  csv = true\n[]\n", s)
# 开逐变量残差
# 【坑】show_var_residual_norms 在 [Debug] 块里，**不在 [Executioner]**。
# 放错位置不会报错，只会以 "unused parameter" 让 MOOSE 中止
# （源码依据：framework/src/actions/SetupDebugAction.C:33）。
s = re.sub(r"\n\[Debug\][\s\S]*?\n\[\]\n", "\n", s)   # 去掉已有的 Debug 块
s = s.rstrip() + "\n\n[Debug]\n  show_var_residual_norms = true\n[]\n"
for tol, tag in (("1e-6", "lo"), ("1e-9", "hi")):
    t = re.sub(r"^  nl_abs_tol = .*$", f"  nl_abs_tol = {tol}", s, flags=re.M)
    open(f"g_{tag}.i", "w", encoding="utf-8").write(t)
    print(f"  g_{tag}.i: ASM + nl_abs_tol={tol} + show_var_residual_norms")
PY

for T in lo hi; do mkdir -p "g_$T"; cp "g_$T.i" columnar_seeds.csv "g_$T"/; done

for T in lo hi; do
  ( cd "$D/g_$T" && setsid --wait "$MOOSE" -i "g_$T.i" > run.log 2>&1 ) &
done
wait

echo
echo "================ 逐变量残差对比 ================"
for T in lo hi; do
  L="$D/g_$T/run.log"
  echo "--- nl_abs_tol = $([ $T = lo ] && echo 1e-6 || echo 1e-9) ---"
  echo "  收敛步 = $(grep -ac 'Solve Converged' "$L")"
  echo "  MOOSE 报的逐变量残差行（末尾 12 行）:"
  sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aE '^\s+(gr[0-7]|c|w|T)\s+resid' | tail -12 | sed 's/^/    /'
  # 若上面没有，试另一种格式
  sed 's/\x1b\[[0-9;]*m//g' "$L" | grep -aE 'Residual norms|resid' | tail -4 | sed 's/^/    /'
done
