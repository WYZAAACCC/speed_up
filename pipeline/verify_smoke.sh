#!/bin/bash
# 等 smoke test 跑完，然后做全过程检查
RUN=/root/work/s1c_col
cd "$RUN" || exit 1

for i in $(seq 1 30); do
    n=$(pgrep -fc phase_field-opt 2>/dev/null)
    n=${n:-0}
    [ "$n" -eq 0 ] && break
    sleep 30
done

echo "===================== 1. 求解过程 ====================="
echo "DIVERGED    : $(grep -c DIVERGED run.log 2>/dev/null)"
echo "Option left : $(grep -c 'Option left' run.log 2>/dev/null)   (应为 0)"
echo "Converged   : $(grep -c 'Solve Converged' run.log 2>/dev/null)"
echo "CSV 步数    : $(( $(wc -l < in_out.csv) - 1 ))"
echo "末态        : $(tail -1 in_out.csv)"

echo
echo "===================== 2. 守恒 ====================="
python3 - <<'PY'
import csv
rows = list(csv.DictReader(open('in_out.csv')))
t0 = float(rows[0]['total_solute'])
vals = [float(r['total_solute']) for r in rows]
dev = max(abs(v - t0) for v in vals) / abs(t0)
print(f"  总溶质 初值 {t0:.12g}")
print(f"  全程最大相对漂移 {dev:.3e}   ({'机器精度 ✓' if dev < 1e-12 else '**偏大**'})")
cs = [float(r['c_solid_avg']) for r in rows]
print(f"  固相平均浓度 {cs[0]:.6f} -> {cs[-1]:.6f}  "
      f"({'固相被贫化 ✓ k<1' if cs[-1] < cs[0] else '**未贫化**'})")
cmax = [float(r['c_max']) for r in rows]
cmin = [float(r['c_min']) for r in rows]
print(f"  浓度跨度：初 {cmax[0]-cmin[0]:.2e} -> 末 {cmax[-1]-cmin[-1]:.4f}"
      f"  (max {cmax[-1]:.5f}, min {cmin[-1]:.5f})")
PY

echo
echo "===================== 3. Exodus 完整性 ====================="
python3 - <<'PY'
import numpy as np
from netCDF4 import Dataset
ds = Dataset('stage1c.e', 'r')
t = np.asarray(ds.variables['time_whole'][:])
conns, k = [], 1
while f"connect{k}" in ds.variables:
    conns.append(ds.variables[f"connect{k}"].shape[0]); k += 1
ev = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
      for r in ds.variables['name_elem_var'][:]]
nv = [b''.join(r).decode(errors='replace').replace('\x00','').strip()
      for r in ds.variables['name_nod_var'][:]]
print(f"  帧数 {len(t)}  (t = {t[0]:.3g} .. {t[-1]:.3g} s)")
print(f"  单元块 {len(conns)} 个，合计 {sum(conns)} 单元")
print(f"  单元变量 {ev}")
print(f"  节点变量 {nv}")
PY

echo
echo "===================== 4. 柱状程度 ====================="
python3 - <<'PY'
import numpy as np
from netCDF4 import Dataset
ds = Dataset('stage1c.e','r')
nm=[b''.join(r).decode(errors='replace').replace('\x00','').strip()
    for r in ds.variables['name_elem_var'][:]]
j=nm.index('unique_grains')+1
vals,conns,k=[],[],1
while f"connect{k}" in ds.variables:
    conns.append(np.asarray(ds.variables[f"connect{k}"][:],dtype=np.int64)-1)
    for key in (f'vals_elem_var{j}eb{k}', f'vals_elem_var{j}'):
        if key in ds.variables:
            vals.append(np.asarray(ds.variables[key][:])); break
    k+=1
conn=np.concatenate(conns); ug=np.concatenate(vals,axis=1)
coord=np.column_stack([np.asarray(ds.variables[f'coord{a}'][:],dtype=float)
                       for a in 'xy' if f'coord{a}' in ds.variables])
cx=coord[conn].mean(axis=1); cy=coord[conn].mean(axis=1)
for tag,t in (("初始",0),("末态",-1)):
    g=np.rint(ug[t]).astype(int); act=g>=0
    print(f"  --- {tag} (t 索引 {t}) ---")
    print(f"    固相占比 {act.mean():.4f}，晶粒数 {len(np.unique(g[act]))}")
    rs=[]
    for gid in np.unique(g[act]):
        m=g==gid
        if m.sum()<20: continue
        sx=cx[m].max()-cx[m].min(); sy=cy[m].max()-cy[m].min()
        rs.append(sy/sx if sx>0 else 0)
    if rs:
        rs=np.array(rs)
        print(f"    y跨度/x跨度: 中位 {np.median(rs):.2f}, 最大 {rs.max():.2f}, "
              f">1.5 的占 {(rs>1.5).mean()*100:.0f}%")
PY
