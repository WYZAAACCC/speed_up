#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_alignfix.py --- 结清一个悬案：`e5_equi6` 的"主轴 ⊥ `a`"与"沿 `a` 跨度最大"**不能同时为真**。

悬案
----
`_r1_analyze.py --block` 报 `e5_equi6` 的 `align_deg` 末态 ≈ **85.9°**（分量 PCA 主轴 ⊥ `a`）；
而**同一行**的整列回归说沿 `a` 的跨度 `L` 是三者中最大的（ΔL=+26.6 nm/步，ΔW=+2.4）。
`_r1_sigprove.py` 从快照独立复核过：最大分量的 PCA 主轴确实 ≈ **83.5°**（不是碎屑伪影）。
⇒ 两个量**必有一个是错的**，或我对其中之一的**含义理解错了**。

本脚本在同一快照上一次性算清三件事（全部用**与引擎逐字相同**的 `a` 轴定义）：
  A. 最大分量的**三向跨度**（沿 a / w / n*）—— 看"沿 a 最大"是否成立；
  B. 最大分量的 **PCA 特征值/特征向量**（在**胞索引空间**算，与 `align_deg` 同一算法）；
  C. 把 B 的每个特征向量分别投影到 a/w/n* 上 —— 看"轴 ⊥ a"是否成立。

判据：若 A 说"沿 a 的跨度最大"而 B/C 说"主轴 ⊥ a"，则检查
  **PCA 是在胞索引空间做的，而胞索引空间的三轴是 (i,j,k)，与物理 (x,y,z) 是否同序**。
这是本脚本要定案的关键点：`np.argwhere` 返回的是 **(i,j,k)**，
若引擎的 `phi` 数组索引顺序与物理坐标轴顺序**不同**，则跨度投影 `ici @ a_ax`
与 PCA 主轴 `vt[0]` 会落在**不同的坐标系**里 —— 那就是这个"矛盾"的根源。
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

d = sys.argv[1] if len(sys.argv) > 1 else 'e5_equi6'
DIR = os.path.join(HERE, '_exp', d)
snaps = sorted(glob.glob(os.path.join(DIR, 'snap_*.npz')))
if not snaps:
    print('✗ 无快照'); sys.exit(1)
snap = snaps[-1]
z = np.load(snap)
reg = z['region']
meta = json.load(open(os.path.join(DIR, 'meta.json')))
dx = (meta.get('dx_nm') or 125.0) * 1e-9

# 与 `_r1_exp.axes_of` 逐字相同的三轴
import windowB_surface as W                                            # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                            # noqa: E402
vals, cnts = np.unique(reg[reg > 0], return_counts=True)
K0 = int(vals[np.argmax(cnts)])
_g = W.LevelSetMulti(8, 1.0e-6, C=C, eps0=EPS0, gamma=0.15,
                     Mob=1.0, df=[0.0] * (NV + 1), workers=1)
n_hab = np.asarray(NPF[K0], float); n_hab /= np.linalg.norm(n_hab)
w_ax = np.asarray(_g.wtab[K0], float); w_ax /= np.linalg.norm(w_ax)
a_ax = np.asarray(_g.atab[K0], float)
a_ax = a_ax - (a_ax @ n_hab) * n_hab
a_ax /= (np.linalg.norm(a_ax) + 1e-300)

print('=' * 96)
print('%s ；快照 %s ；K0=%d' % (d, os.path.basename(snap), K0))
print('   a=[%+.4f %+.4f %+.4f]  w=[%+.4f %+.4f %+.4f]  n*=[%+.4f %+.4f %+.4f]'
      % (*a_ax, *w_ax, *n_hab))
print('   ⚠ 三轴正交性（应 ≈0；非 0 说明它们不是正交基）：a·w=%.2e  a·n*=%.2e  w·n*=%.2e'
      % (a_ax @ w_ax, a_ax @ n_hab, w_ax @ n_hab))
print('=' * 96)

m = (reg == K0)
lab, ncomp = nd.label(m)
sizes = np.array(nd.sum(m, lab, range(1, ncomp + 1)), dtype=int)
big = int(np.argmax(sizes)) + 1
mc = (lab == big)
ici = np.argwhere(mc).astype(np.float64)     # ← 注意：这是 (i,j,k) 胞索引
print('最大分量：%d 胞' % int(sizes[big - 1]))

print('\nA. 三向跨度（`ici @ 轴`，与引擎 `measure()` 同一算法）：')
pa, pw, pn = ici @ a_ax, ici @ w_ax, ici @ n_hab
for tag, p in (('a', pa), ('w', pw), ('n*', pn)):
    print('   沿 %-2s ：%.1f 胞  （%.0f nm）' % (tag, p.max() - p.min(),
                                               (p.max() - p.min()) * dx * 1e9))
big_ax = 'a' if np.ptp(pa) >= max(np.ptp(pw), np.ptp(pn)) else ('w' if np.ptp(pw) >= np.ptp(pn) else 'n*')
print('   ⇒ 跨度最大的是 **%s**' % big_ax)

print('\nB. 最大分量的 PCA（**与 `align_deg` 同一算法**：对去均值后的胞索引做 SVD）：')
cm = ici.mean(0)
u, s, vt = np.linalg.svd(ici - cm, full_matrices=False)
print('    奇异值 = %s' % np.array2string(s, precision=1))
for i in range(3):
    v = vt[i]
    ang = float(np.degrees(np.arccos(min(1.0, abs(float(v @ a_ax))))))
    print('    主轴%d = [%+.4f %+.4f %+.4f]  与 a 夹角 = %6.2f°  |  与 w %6.2f°  |  与 n* %6.2f°'
          % (i, *v, ang, float(np.degrees(np.arccos(min(1.0, abs(float(v @ w_ax)))))),
             float(np.degrees(np.arccos(min(1.0, abs(float(v @ n_hab))))))))
ang0 = float(np.degrees(np.arccos(min(1.0, abs(float(vt[0] @ a_ax))))))
print('   ⇒ `align_deg`（主轴0 与 a 的夹角）= **%.2f°**' % ang0)

print('\nC. 定案：两者矛盾吗？')
print('    A 说跨度最大方向 = %s ；B 说主轴0 与 a 夹角 = %.2f°' % (big_ax, ang0))
if big_ax == 'a' and ang0 > 45:
    print('    ⇒ ⛔ **确实矛盾**。可能原因（按可能性排序）：')
    print('       (1) 分量**非凸/多臂**：最大方差方向 ≠ 最大跨度方向（对 L 形/枝状物体成立）；')
    print('       (2) `np.argwhere` 的 **(i,j,k)** 与物理 (x,y,z) **不同序**；')
    print('       (3) 该分量的胞集合被 `lab` 的连通性判据切成了窄条。')
    print('       判据：看 B 的主轴方向是否**接近某个网格轴**（若是 ⇒ (2) 可能）。')
    for i in range(3):
        e = np.eye(3)[i]
        print('          主轴%d · e%d = %+.3f' % (i, i, float(vt[i] @ e)))
elif big_ax == 'a' and ang0 <= 45:
    print('    ⇒ ✅ 不矛盾（跨度与主轴都指向 a 附近）')
else:
    print('    ⇒ ✅ 不矛盾（跨度最大方向不是 a，与"主轴 ⊥ a"一致）')
print('=' * 96)
