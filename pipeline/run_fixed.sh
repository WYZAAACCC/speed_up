#!/bin/bash
# 根因修复后的第一次验证：梯度只以数据身份进入 align4，不再有 1/G^2 雅可比垃圾。
# 用**原始求解器配置**（asm/ilu，不加主元平移、不提迭代上限），
# 检验修复本身是否足够 —— 若还需要调求解器，说明根因没找全。
#
# 三层验证：
#   F1 首步能不能收敛（end_time=1e-6）
#   F2 grad_align 是否不再 NaN（align_mean 应为有限值，顺带修好的老 bug）
#   F3 若 F1 通过，跑到 4e-6 看步长能否涨起来
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
SRC=/root/work/s1d_w
D=/root/work/s1d_fix

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp "$SRC/stage1_meltpool_d.i" "$SRC/columnar_seeds.csv" .

python3 - <<'PY'
import re
s = open("stage1_meltpool_d.i", encoding="utf-8").read()
s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = F1")
assert "[Debug]" not in s
s = s.replace("\n[Executioner]\n",
              "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
open("F1.i", "w", encoding="utf-8").write(s)
print("F1.i 写好（原始求解器配置 + 逐变量残差）")
PY

echo "=== F1: 首步 ==="
setsid --wait "$MOOSE" -i F1.i > F1.log 2>&1
echo "退出码 $?"
printf "收敛步数 = "; grep -ac "Solve Converged" F1.log
echo "逐变量残差:"
grep -a -A12 "individual variables" F1.log | tail -12 | sed 's/^/  /'
echo "线性求解:"
grep -a "Linear solve" F1.log | sed 's/^ *//' | sort | uniq -c | sort -rn | head -4 | sed 's/^/  /'
echo "牛顿:"
grep -a "Nonlinear |R|" F1.log | head -8 | sed 's/^/  /'
echo "** 对齐度诊断（关键：align_mean 不应再是 nan）**"
head -2 F1_out.csv | sed 's/^/  /'
sed -n '2p' F1_out.csv | tr ',' '\n' | paste -d= <(head -1 F1_out.csv | tr ',' '\n') - | grep -E "align|kappa|gamma|^L_" | sed 's/^/  /'
echo "报错:"
grep -a -m3 -E '\*\*\* ERROR|SUBPC|DIVERGED|NaN' F1.log | sed 's/^/  /'
