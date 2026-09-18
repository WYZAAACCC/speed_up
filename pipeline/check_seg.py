#!/usr/bin/env python3
"""
检查晶界偏析有没有建立。

做法：用 gb_indicator（Ση_i²，体相≈1、晶界≈0.5）把单元分成"体相"和"晶界"两组，
      比较两组内的浓度。
"""
import sys
import numpy as np
from netCDF4 import Dataset

path = sys.argv[1] if len(sys.argv) > 1 else "phase2_2d_seg.e"
ds = Dataset(path, "r")


def names(key):
    out = []
    for row in ds.variables[key][:]:
        try:
            s = b"".join(row).decode("utf-8", "replace")
        except Exception:
            s = str(row)
        out.append(s.replace("\x00", "").strip())
    return out


en = names("name_elem_var")
nn = names("name_nod_var")
print("元素变量:", en)
print("节点变量:", nn)
print()

t = np.asarray(ds.variables["time_whole"][:], dtype=float)
conn = np.asarray(ds.variables["connect1"][:], dtype=np.int64) - 1


def elem_var(name):
    i = en.index(name) + 1
    return np.asarray(ds.variables[f"vals_elem_var{i}eb1"][:], dtype=float)


def nod_var(name):
    i = nn.index(name) + 1
    return np.asarray(ds.variables[f"vals_nod_var{i}"][:], dtype=float)


gb = elem_var("gb_indicator")
c_node = nod_var("c")
# 节点量平均到单元
c_e = np.stack([c_node[it][conn].mean(axis=1) for it in range(len(t))])

print(f"{'time':>8} {'c(体相)':>11} {'c(晶界)':>11} {'差值':>10} {'富集比':>9} {'GB单元占比':>10}")
print("-" * 66)

for it in np.linspace(0, len(t) - 1, min(12, len(t))).astype(int):
    g = gb[it]
    c = c_e[it]
    bulk = g > 0.98      # 体相
    face = g < 0.80      # 晶界
    if bulk.sum() < 10 or face.sum() < 10:
        print(f"{t[it]:>8.0f}   体相 {bulk.sum()} 个 / 晶界 {face.sum()} 个单元（阈值需调）")
        continue
    cb, cf = c[bulk].mean(), c[face].mean()
    print(f"{t[it]:>8.0f} {cb:>11.6f} {cf:>11.6f} {cf-cb:>+10.6f} "
          f"{cf/cb:>9.4f} {face.sum()/len(g)*100:>9.1f}%")

ds.close()
