#!/bin/bash
# 检查柱状晶基体到底生成了什么
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work/s1c_col || exit 1

echo "=== 种子文件（运行目录里的）==="
head -4 columnar_seeds.csv
echo "行数: $(( $(wc -l < columnar_seeds.csv) - 1 ))"

echo
echo "=== 日志里的 GrainTracker 初始状态 ==="
grep -A12 'Grains active index' run.log | head -14

echo
echo "=== unique_grains 的实际取值 ==="
python3 - <<'PY'
import numpy as np
from netCDF4 import Dataset
ds = Dataset('stage1.e', 'r')
nm = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
      for r in ds.variables['name_elem_var'][:]]
print("  单元变量:", nm)
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
for t in [0, -1]:
    g = np.rint(ug[t]).astype(int)
    u = np.unique(g)
    print(f"  t索引{t}: unique = {u}")
    act = g >= 0
    print(f"    固相占比 {act.mean():.4f}")
    if act.any():
        # 按 x 分列统计每个晶粒的 x 范围
        for gid in u[u >= 0][:15]:
            m = g == gid
            if m.sum() < 10: continue
            print(f"    晶粒 {gid:>3d}: {m.sum():>6d} 单元, "
                  f"x ∈ [{cx[m].min()*1e6:>6.1f}, {cx[m].max()*1e6:>6.1f}] um")
PY
