#!/bin/bash
# 验证修好后的 extract.py 在**多单元块**网格上是否读全了数据
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/extract.py > extract.py

echo "=============================================================="
echo " 测试：在 stage1.e（2 个单元块，共 30100 单元）上跑提取"
echo " 注意：stage1 还没有溶质场，这里用 bnds（Ση²）代替 c，"
echo "       只为验证管线读全了所有块，数值本身无物理意义"
echo "=============================================================="
python3 extract.py /root/work/s1/stage1.e --out /root/work/ds_lpbf_test \
    --solute-var bnds --stride 8 2>&1 | head -45

echo
echo "=============================================================="
echo " 关键校验：提取到的域测度 vs 网格实际总测度"
echo "=============================================================="
python3 - <<'PY'
import csv, numpy as np
from netCDF4 import Dataset
ds = Dataset('/root/work/s1/stage1.e','r')
conns=[]
k=1
while f"connect{k}" in ds.variables:
    conns.append(np.asarray(ds.variables[f"connect{k}"][:],dtype=np.int64)-1); k+=1
conn=np.concatenate(conns)
coord=np.column_stack([np.asarray(ds.variables[f"coord{a}"][:],dtype=float)
                       for a in "xy" if f"coord{a}" in ds.variables])
p=coord[conn]
def cross2d(a,b): return a[...,0]*b[...,1]-a[...,1]*b[...,0]
m=0.5*np.abs(cross2d(p[:,1]-p[:,0],p[:,2]-p[:,0])) + \
  0.5*np.abs(cross2d(p[:,2]-p[:,0],p[:,3]-p[:,0]))
print(f"  网格总测度（全部块）: {m.sum():.6g}")
print(f"  域 430um x 150um     = {430e-6*150e-6:.6g}")
print(f"  比值: {m.sum()/(430e-6*150e-6):.6f}  (应≈1)")
PY
