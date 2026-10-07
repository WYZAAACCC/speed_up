#!/usr/bin/env python3
"""R51: 找出**长轴近乎平行**的变体对 —— 用于"两块能分开摆放且同属一个 packet"。

物理动机：同一个 **packet** 里的块**共享惯习面** ⇒ `n*(v)` 相同 ⇒ 长轴近乎平行。
`_r51_b62p` 失败的根因是 **变体 1 与 3 的长轴夹角 ≈121°**
⇒ 引擎的 `c0 − d_b·a_b` 对称摆放**必然把两个质心拉到一起**
（实测质心距 0.88 µm < 半长 1.00 µm，t=0 接触面 **963**）⇒ 初始混杂。
⇒ 要挑**同惯习面**的变体对，摆放才能分开。
"""
import os
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
from _r30_mbverdict import variant_axes  # noqa: E402

tab = {}
for v in range(1, 25):
    try:
        n, a, w = variant_axes(v)
    except Exception:
        continue
    tab[v] = (np.asarray(n, float), np.asarray(a, float), np.asarray(w, float))
print('可用变体号 %s ⇒ 本模型共 **%d 个变体**' % (sorted(tab), len(tab)))

reps = []                      # [(rep_n, [variants])]
for v in sorted(tab):
    n = tab[v][0]
    for rep, mem in reps:
        if abs(abs(float(np.dot(n, rep))) - 1.0) < 1e-6:
            mem.append(v)
            break
    else:
        reps.append((n, [v]))
print()
print('=== 按 n*（惯习面法向）分组：共 %d 个不同方向' % len(reps))
for rep, mem in reps:
    print('    n*=%s   变体 %s' % (np.round(rep, 4), mem))

print()
print('=== 同一 n* 组内两两长轴夹角（最小 8 对）')
pairs = []
for rep, mem in reps:
    for i in range(len(mem)):
        for j in range(i + 1, len(mem)):
            v1, v2 = mem[i], mem[j]
            c = abs(float(np.dot(tab[v1][1], tab[v2][1])))
            pairs.append((float(np.degrees(np.arccos(np.clip(c, -1, 1)))), v1, v2))
pairs.sort()
for ang, v1, v2 in pairs[:8]:
    print('  变体 %2d & %2d : 长轴夹角 %6.2f°' % (v1, v2, ang))

print()
print('=== 对照：本次失败的组合')
for (v1, v2) in ((1, 3), (1, 2), (1, 4)):
    if v1 in tab and v2 in tab:
        c = abs(float(np.dot(tab[v1][1], tab[v2][1])))
        print('  变体 %2d & %2d : 长轴夹角 %6.2f°   n*·n* = %+.3f'
              % (v1, v2, float(np.degrees(np.arccos(np.clip(c, -1, 1)))),
                 float(np.dot(tab[v1][0], tab[v2][0]))))
