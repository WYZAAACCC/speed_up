#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_npref.py --- B4 的 packet 族定义体检：`npref` 的等价类是否复现 Burgers 的
   "{110}β 面"分组？Burgers 的 12 变体应分成 **6 族 × 2 变体**（同一 {110} 面）。"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402
from T24_verify_grouping import packet_families                 # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

U = {k: np.asarray(v, float) / np.linalg.norm(v) for k, v in NPF.items()}
print('=' * 92)
print('npref 两两夹角（度，只列 < 25° 的对；±n 等价 ⇒ 用 |cos|）')
ks = sorted(U)
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        ang = np.degrees(np.arccos(np.clip(abs(float(U[a] @ U[b])), 0, 1)))
        if ang < 25.0:
            print('   (%2d,%2d) : %6.2f°' % (a, b, ang))
print('-' * 92)
for tol in (5.0, 10.0, 15.0, 20.0):
    fam, nf = packet_families(NPF, tol_deg=tol)
    groups = {}
    for k, f in fam.items():
        groups.setdefault(f, []).append(k)
    print('tol=%4.1f° ⇒ %d 族：%s' % (tol, nf, [groups[f] for f in sorted(groups)]))
print('-' * 92)
print('期望（Burgers）：**6 族 × 2 变体**（同一 {110}β 面）')
print('★ 若实测族数 ≠ 6，说明 `npref` 这个代理**不能**复现 packet 结构 ⇒')
print('  必须从 `windowB_ti64_variants.py` 的 Burgers 对应关系里取真正的 {110}β 家族。')
print('=' * 92)
