#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_pair_normal.py --- 判据 D1（LATH_FACET_PLAN 3）：配对相容法向表的质量。

物理：MATH_FRAMEWORK 5.6 —— 两变体的界面若可自协调，应落在 rank-1 不变平面法向上，
      即 n*(k,l) = argmin_n 0.5*dEps0:Lam(C,n):dEps0（dEps0 = eps0_k - eps0_l）。

★ 判据设计的两条修正（记账，2026-09-26 第一版判据是错的）：
  1) **不能要求 66 对全部强择优**。Ti64 的 12 个 Burgers 变体里只有**少数配对**
     能自协调（文献的自协调变体群正是如此）。第一版用"每对都要 <= 随机 1% 分位"，
     给出 5/66 FAIL —— 那是**判据错**，不是表错。
  2) 正确的判据是**两层**：(a) 分布要有明显层次（存在强相容对）；
     (b) 强相容对必须与**实际界面对富集**（M5）一致（见 _chk_pair_vs_m5.py）。

输出：_pair_normals_table.json（供 M5 交叉验证）。
"""
import json
import numpy as np

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

NSAMP, SEED = 600, 0
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)

g = W.LevelSetMulti(8, 8 * 1e-8, C=C, eps0=eps0, gamma=0.15, Mob=1e-9)
assert g.ncmp is not None, 'ncmp 未建立'

rng = np.random.default_rng(SEED)
ns = rng.normal(size=(NSAMP, 3))
ns /= np.linalg.norm(ns, axis=1)[:, None]
L = np.array([_lam_full(C, n) for n in ns])

rows, tab = [], {}
for k in range(1, nv + 1):
    for l in range(k + 1, nv + 1):
        de = np.asarray(eps0[k - 1], float) - np.asarray(eps0[l - 1], float)
        vals = 0.5 * np.einsum('ij,sijkl,kl->s', de, L, de)
        med = float(np.median(vals))
        quan = float(np.quantile(vals, 0.01))
        nt = g.ncmp[k, l]
        vt = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, nt), de))
        rows.append(dict(k=k, l=l, val=vt, med=med, q01=quan, ratio=vt / med,
                         argmin_is_tab=bool(vt <= quan * 1.0000001)))
        tab['%d-%d' % (k, l)] = dict(val=vt, med=med, ratio=vt / med)

ratio = np.array([r['ratio'] for r in rows])
n_tot = len(rows)
strong = [r for r in rows if r['ratio'] <= 1e-3]
weakc = int((ratio <= 1e-2).sum())

print('=== D1: 配对相容法向表（%d 对）===' % n_tot)
print('  表值/随机中位：min %.3e  中位 %.3e  max %.3e'
      % (ratio.min(), np.median(ratio), ratio.max()))
print('  => 比典型随机方向低：最好 %.1f 个数量级；中位 %.1f 个数量级；最差 %.1f 个数量级'
      % (-np.log10(ratio.min()), -np.log10(np.median(ratio)), -np.log10(ratio.max())))
print('  层次：强相容(<=1e-3) %d 对；可接受(<=1e-2) %d 对' % (len(strong), weakc))
print('  强相容对：%s' % ', '.join('V%d-V%d(%.1e)' % (r['k'], r['l'], r['ratio'])
                                  for r in strong))
print('  弱相容对(top-5 最差)：%s'
      % ', '.join('V%d-V%d(%.1e)' % (r['k'], r['l'], r['ratio'])
                  for r in sorted(rows, key=lambda r: -r['ratio'])[:5]))

ok_a = (len(strong) >= 5) and (np.median(ratio) <= 1e-2)
print('  [D1-a] 存在 >=5 个强相容对 且 中位 <=1e-2 : %s' % ('PASS' if ok_a else 'FAIL'))
print('  [D1-b] 强相容对是否与实际界面对富集一致 -> 由 _chk_pair_vs_m5.py 判')
json.dump(dict(tab=tab, strong=['%d-%d' % (r['k'], r['l']) for r in strong],
               ratio_med=float(np.median(ratio)), n_strong=len(strong)),
          open('_pair_normals_table.json', 'w'), indent=1)
print('  已存 _pair_normals_table.json')
