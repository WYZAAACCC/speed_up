#!/bin/bash
# 核验 extract.py 在多单元块网格上是否会漏数据
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

cd /root/work/s1 || exit 1

python3 - <<'PY'
import numpy as np
from netCDF4 import Dataset

ds = Dataset('stage1.e', 'r')

print("=" * 66)
print(" 1. Exodus 的单元块结构")
print("=" * 66)
print("  eb_prop1 (块 ID):", np.asarray(ds.variables['eb_prop1'][:]).ravel())
k = 1
tot = 0
while f"connect{k}" in ds.variables:
    n = ds.variables[f"connect{k}"].shape[0]
    tot += n
    print(f"  connect{k}: {n} 个单元")
    k += 1
print(f"  合计 {tot}")

print()
print("=" * 66)
print(" 2. extract.py 实际会读到什么")
print("=" * 66)
# extract.py 第 128 行：只读 connect1
conn1 = np.asarray(ds.variables['connect1'][:], dtype=np.int64) - 1
print(f"  extract.py 读 connect1      -> {conn1.shape[0]} 个单元")
print(f"  网格实际总数                -> {tot} 个单元")
print(f"  ** 漏掉 {tot - conn1.shape[0]} 个单元 ({100*(tot-conn1.shape[0])/tot:.1f}%) **")

print()
print("=" * 66)
print(" 3. 单元变量的分层情况（read_var 硬编码了 eb1）")
print("=" * 66)
for name in ['unique_grains', 'liquid_flag']:
    nm = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
          for r in ds.variables['name_elem_var'][:]]
    if name not in nm:
        print(f"  {name}: 不在单元变量里")
        continue
    j = nm.index(name) + 1
    keys = [k for k in ds.variables if k.startswith(f'vals_elem_var{j}')]
    print(f"  {name} (var{j}): 分块存储 -> {keys}")

print()
print("=" * 66)
print(" 4. unique_grains 的取值（判断 'gid >= 0' 是否正确）")
print("=" * 66)
nm = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
      for r in ds.variables['name_elem_var'][:]]
j = nm.index('unique_grains') + 1
# 拼接所有块
vals, conns = [], []
k = 1
while f"connect{k}" in ds.variables:
    conns.append(np.asarray(ds.variables[f"connect{k}"][:], dtype=np.int64) - 1)
    for key in (f'vals_elem_var{j}eb{k}', f'vals_elem_var{j}'):
        if key in ds.variables:
            vals.append(np.asarray(ds.variables[key][:]))
            break
    k += 1
conn = np.concatenate(conns)
ug = np.concatenate(vals, axis=1)

for t in [0, len(ug)//2, -1]:
    u = np.unique(np.rint(ug[t]).astype(np.int64))
    print(f"  t 索引 {t}: 取值 {u[:12]}{' ...' if len(u)>12 else ''}")
    print(f"      最小值 {u.min()}，'>= 0' 的单元占比 {(ug[t] >= 0).mean():.4f}，"
          f"'> 0' 的占比 {(ug[t] > 0).mean():.4f}")

print()
print("=" * 66)
print(" 5. 只在 connect1（固态区）上取 unique_grains 会怎样")
print("=" * 66)
ug1 = np.asarray(ds.variables[f'vals_elem_var{j}eb1'][:])
u1 = np.unique(np.rint(ug1[-1]).astype(np.int64))
print(f"  eb1 上的取值: {u1[:12]}")
print(f"  '>= 0' 占比 {(ug1[-1] >= 0).mean():.4f}")
print(f"  '> 0'  占比 {(ug1[-1] > 0).mean():.4f}")
PY
