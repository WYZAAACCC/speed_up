#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1c_col || exit 1

echo "=== 输出文件 ==="
ls -la *.e *.csv 2>/dev/null

echo
echo "=== 日志里有关 coloring / grain 的信息 ==="
grep -i 'color\|grain\|voronoi\|centroid' run.log | head -20

echo
echo "=== 检查 Exodus 的晶粒结构 ==="
f=$(ls *.e 2>/dev/null | head -1)
echo "文件: $f"
python3 - "$f" <<'PY'
import sys
import numpy as np
from netCDF4 import Dataset
ds = Dataset(sys.argv[1], 'r')
nm = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
      for r in ds.variables['name_elem_var'][:]]
print("  单元变量:", nm)
if 'unique_grains' not in nm:
    sys.exit("  没有 unique_grains")
j = nm.index('unique_grains') + 1
vals, conns = [], []
k = 1
while f"connect{k}" in ds.variables:
    conns.append(np.asarray(ds.variables[f"connect{k}"][:], dtype=np.int64) - 1)
    for key in (f'vals_elem_var{j}eb{k}', f'vals_elem_var{j}'):
        if key in ds.variables:
            vals.append(np.asarray(ds.variables[key][:])); break
    k += 1
conn = np.concatenate(conns); ug = np.concatenate(vals, axis=1)
coord = np.column_stack([np.asarray(ds.variables[f'coord{a}'][:], dtype=float)
                         for a in 'xy' if f'coord{a}' in ds.variables])
cx = coord[conn].mean(axis=1)
g = np.rint(ug[0]).astype(int)
print(f"  t=0 unique_grains = {np.unique(g)}")
print(f"    固相占比 {(g>=0).mean():.4f}")
for gid in np.unique(g[g >= 0]):
    m = g == gid
    if m.sum() < 10: continue
    print(f"    晶粒 {gid:>3d}: {m.sum():>6d} 单元, "
          f"x ∈ [{cx[m].min()*1e6:>6.1f}, {cx[m].max()*1e6:>6.1f}] um")

# 序参量最大值分布（看染色到底给了谁）
for name in ['gr0','gr1','gr2']:
    if name in nm:
        jj = nm.index(name)+1
        v = np.asarray(ds.variables[f'vals_nod_var{jj}'][:])
        print(f"  {name}: t=0 最大 {v[0].max():.4f}, 均值 {v[0].mean():.4f}")
PY
