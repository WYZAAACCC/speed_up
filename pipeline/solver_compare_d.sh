#!/bin/bash
# 【生产配置的决定性测量】D = ASM + nl_abs_tol=1e-9
#
# 已确立的事实（三路对比 A/B/C）：
#   * C(MUMPS+1e-6) vs B(ASM+1e-6)：relL2 = 2.6e-13  -> **同容差下两求解器给出同一个解**
#   * A(MUMPS+1e-9) vs C(MUMPS+1e-6)：relL2 = 2.1e-3 -> **差异全部来自容差**
#   => 发散与求解器无关；ASM 并非"不准"。
#
# 但由此产生两个后果：
#   1. |R|=1e-6 对应约 2e-3 的解误差 -> **残差容差是解精度的坏代理**，训练数据应取紧容差
#   2. A(MUMPS+1e-9) 花了 955 s，B(ASM+1e-6) 只花 672 s
#
# 所以决定性问题：**ASM 能不能收敛到 1e-9？**
#   D 收敛且 D ≈ A  ->  **ASM + 紧容差 = 又快又准**，生产用它
#   D 停滞/失败      ->  ASM 的线性解精度不足以支撑紧容差 -> 只能 MUMPS（慢）
#
# （记忆里曾有"ASM 卡在 7.3e-07 地板"的说法，但那条归因已被证明不可靠，
#   必须重新实测，不能引用。）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/slv_cmp

python3 - <<'PY'
import re
s = open("/root/work/slv_cmp/B/B.i", encoding="utf-8").read()
s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-9", s, flags=re.M)
s = s.replace("file_base = B", "file_base = D")
open("/root/work/slv_cmp/D.i", "w", encoding="utf-8").write(s)
print("  D.i = ASM + nl_abs_tol=1e-9")
PY

mkdir -p "$D/D"; cp "$D/D.i" "$D/columnar_seeds.csv" "$D/D"/ 2>/dev/null
cd "$D/D" || exit 1
T0=$(date +%s)
setsid --wait "$MOOSE" -i D.i > run.log 2>&1
RC=$?
T1=$(date +%s)

echo
echo "================ D(ASM + 1e-9) 结果 ================"
echo "  退出码 = $RC   墙钟 = $((T1-T0)) s"
echo "  收敛步 = $(grep -ac 'Solve Converged' run.log)"
echo "  牛顿失败(DIVERGED_MAX_IT) = $(grep -ac 'DIVERGED_MAX_IT' run.log)"
echo "  线性失败(DIVERGED) = $(grep -ac 'DIVERGED' run.log)"
echo "  末步: $(grep -a '^Time Step' run.log | tail -1)"
echo "  --- 各步牛顿末残差 ---"
awk '/^Time Step/{ts=$0} /Nonlinear \|R\|/{last=$0} /Solve Converged/{printf "    %-46s %s\n", ts, last}' run.log | tail -18
echo "  --- 对比基线 ---"
echo "    A(MUMPS+1e-9) 955.7 s / 15 步全收敛 / 牛顿降到 4.5e-10"
echo "    B(ASM+1e-6)   672.6 s / 15 步全收敛"
