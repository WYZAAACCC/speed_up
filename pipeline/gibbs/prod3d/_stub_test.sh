#!/bin/bash
# 二分诊断：只加一个"掏空"的 GBSoluteSink（probe_stub=true），看是否还段错误。
#   · 仍然段错误 ⇒ 崩溃来自"对象在场"（注册/执行组/参数），与内部逻辑无关
#   · 正常跑完   ⇒ 崩溃在我 execute() 里的某个 API 调用
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/stub
rm -rf "$R"; mkdir -p "$R"; cd "$R" || exit 1
SRC=/mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i
sed 's/\r$//' "$SRC" > case.i
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
python3 - <<'PY'
import re
t = open('case.i', encoding='utf-8').read()
t2, n = re.subn(r"(\[gb_sink\][\s\S]*?r_gas = [0-9.]+)",
                r"\1\n    probe_stub = true", t)
open('case.i','w',encoding='utf-8',newline='').write(t2)
print("改动数 =", n)
PY
timeout 600 /root/projects/gibbs/gibbs-opt -i case.i Executioner/end_time=1e-6 > run.log 2>&1
echo "rc=$?"
echo "Time Step 次数 = $(grep -c 'Time Step' run.log)"
tail -3 run.log | sed 's/\x1b\[[0-9;]*m//g'
