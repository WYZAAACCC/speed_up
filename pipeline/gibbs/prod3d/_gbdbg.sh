#!/bin/bash
# 让约束打印 (secondary, primary, lambda, kex, 单元号) —— 判定 _u_secondary 是不是 0
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/gbdbg
rm -rf "$R"; mkdir -p "$R"; cd "$R" || exit 1
SRC=${1:-/mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i}
sed 's/\r$//' "$SRC" > case.i
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
# 给两条约束都打开诊断打印
python3 - <<'PY'
import re
t = open('case.i', encoding='utf-8').read()
t2, n = re.subn(r"(\[gb\d_exchange\][\s\S]*?kex = kex)",
                r"\1\n    debug_print = true", t)
open('case.i','w',encoding='utf-8',newline='').write(t2)
print("打开 debug_print 的约束数 =", n)
PY
timeout 600 /root/projects/gibbs/gibbs-opt -i case.i Executioner/end_time=1e-7 > run.log 2>&1
echo "rc=$?"
echo "===== [GBDBG] ====="
grep 'GBDBG' run.log | head -24
echo "===== 变量级残差 ====="
grep -A13 'residual|_2 of individual' run.log | head -16
