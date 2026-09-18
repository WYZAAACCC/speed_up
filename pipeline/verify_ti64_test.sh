#!/bin/bash
# 核验 Ti64 短测试结果
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1ti64_test || exit 1

echo "DIVERGED 次数 : $(grep -c DIVERGED run.log 2>/dev/null)"
echo "收敛步数      : $(grep -c 'Solve Converged' run.log 2>/dev/null)"
echo "CSV 行数      : $(( $(wc -l < in_out.csv) - 1 ))"
echo
echo "--- 初始 ---"; head -2 in_out.csv | tail -1
echo "--- 末态 ---"; tail -1 in_out.csv
echo
echo "--- Exodus ---"
ls -la stage1.e
python3 - <<'PY'
from netCDF4 import Dataset
import numpy as np
ds = Dataset('stage1.e', 'r')
t = np.asarray(ds.variables['time_whole'][:])
print(f"  帧数 {len(t)}，t = {t[0]:.3g} .. {t[-1]:.3g} s")
k = 1
tot = 0
while f"connect{k}" in ds.variables:
    tot += ds.variables[f"connect{k}"].shape[0]
    k += 1
print(f"  单元总数 {tot}（全部块）")
PY
echo
echo "--- 末态沿 x 的固相分布（用 analyze 脚本）---"
python3 /root/work/analyze_stage1.py stage1.e 2>&1 | tail -12
