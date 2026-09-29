#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_dbgcol.py —— 诊断 `column_profile` 在 C13b（第 5 层减半）上少了一根板条。"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402

N, dx = 64, 62.5e-9
T = 125e-9
nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
wa = np.array([0.70711, 0.70711, 0.0]); wa /= np.linalg.norm(wa)
aa = np.array([-0.4909, 0.4909, 0.7198]); aa /= np.linalg.norm(aa)
am = dict(n=nh, w=wa, a=aa)
c0 = np.array([N * dx / 2] * 3)
W, AL = 320e-9, 1200e-9

reg = np.zeros((N, N, N), np.int8)
for i in range(6):
    off = (i - 2.5) * 2 * T
    tt = T if i == 4 else 2 * T
    reg[BM._synth_slab(N, dx, c0 + off * nh, dict(n=tt, w=W, a=AL), am)] = i + 1

allowed = set(range(1, 7))
prof, runs = BM.column_profile(reg, dx, nh, wa, aa, allowed)
print('runs =', runs, ' nslab =', len(runs))
print('profile len =', 0 if prof is None else len(prof))
if prof is not None:
    print('profile =', prof.tolist())

# 手工复算（不优化：整盒）
m_all = np.isin(reg, list(allowed))
ii = np.arange(N) * dx
X = [ii[:, None, None], ii[None, :, None], ii[None, None, :]]
cnt = float(m_all.sum())
cc = np.array([float((X[t] * m_all).sum()) / cnt for t in range(3)])
rel = [X[t] - cc[t] for t in range(3)]
pa = aa[0] * rel[0] + aa[1] * rel[1] + aa[2] * rel[2]
pw = wa[0] * rel[0] + wa[1] * rel[1] + wa[2] * rel[2]
pn = nh[0] * rel[0] + nh[1] * rel[1] + nh[2] * rel[2]
col = m_all & (pa ** 2 + pw ** 2 <= (300e-9) ** 2)
print('整盒法 col 胞数 =', int(col.sum()))
v = pn[col]; ids = reg[col]
edges = np.arange(v.min() - 0.5 * dx, v.max() + 1.5 * dx, dx)
prof2 = np.zeros(len(edges) - 1, np.int32)
for b in range(prof2.size):
    sel = (np.digitize(v, edges) - 1 == b)
    if sel.any():
        prof2[b] = int(np.bincount(ids[sel]).argmax())
print('整盒 profile =', prof2.tolist())
print('centroid 优化法 =', np.array2string(cc * 1e9, precision=1),
      ' nm')
seg = []
for val in prof2:
    if seg and seg[-1][0] == int(val):
        seg[-1][1] += 1
    else:
        seg.append([int(val), 1])
print('整盒 segs =', seg)
print('整盒 runs(去<2) =', [s[0] for s in seg if s[0] != 0 and s[1] >= 2])
