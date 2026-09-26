#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_lath_shape.py --- **按连通块**测板条形状（修正 M4 的口径错误）。

记账（为什么要这个脚本）：
  _chk_morph_full.py 的 M4 把"**整个变体的所有碎片**"一起算惯性张量。
  但 M2 显示每个变体被邻居切成 ~15 块（主块占比仅 0.25）=> 碎片散布开后
  惯性张量必然接近**等轴** => M4~1.7 是**测量伪影**，不是"没长成板条"的证据。
  正确对象 = **单个连通块**（= 单根/单束板条）。

输出：每块的长径比 a/c、厚度 2c、长度 2a；按体积加权的分布。
用法：python3 _chk_lath_shape.py results_boxB_mob_hi200_final.npz [...]
"""
import sys
import numpy as np
from scipy import ndimage as ndi

import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('--min', type=int, default=400)
_ap.add_argument('files', nargs='*')
_a = _ap.parse_args()
MIN_CELLS = _a.min
for P in (_a.files or sys.argv[1:]):
    d = np.load(P)
    reg = d['reg']; N = int(d['N']); dx = float(d['dx'])
    nv = 12
    Vc = dx ** 3
    print('=== %s : N=%d dx=%.3f um  f=%.4f' % (P.split('/')[-1], N, dx * 1e6, float(d['f'])))
    all_ar, all_t, all_L, all_v = [], [], [], []
    per_var = {}
    for v in range(1, nv + 1):
        m = (reg == v)
        if m.sum() < MIN_CELLS:
            continue
        lab, nb = ndi.label(m, structure=np.ones((3, 3, 3)))
        sz = np.bincount(lab.ravel())
        idxs = np.argwhere(m)
        blocks = 0
        ars, ts, Ls, vs = [], [], [], []
        for bi in range(1, nb + 1):
            n = sz[bi]
            if n < MIN_CELLS:
                continue
            pts = idxs[lab[tuple(idxs.T)] == bi].astype(float) * dx
            pts -= pts.mean(0)
            ev, evec = np.linalg.eigh(np.cov(pts.T))
            ev = np.sort(np.clip(ev, 1e-30, None))[::-1]
            a, b, c = np.sqrt(ev)                 # 半轴（标准差口径）
            ars.append(a / c); ts.append(4 * c); Ls.append(4 * a); vs.append(n * Vc)
            blocks += 1
        if blocks:
            per_var[v] = (blocks, float(np.median(ars)), float(np.median(ts)))
            all_ar += ars; all_t += ts; all_L += Ls; all_v += vs
        print('   V%-2d 块=%3d(>=%d 胞) 中位长径比 %5.2f 中位厚 %.3f um'
              % (v, blocks, MIN_CELLS, np.median(ars) if ars else np.nan,
                 np.median(ts) * 1e6 if ts else np.nan))
    if not all_ar:
        print('   没有满足门槛的块'); continue
    ar = np.array(all_ar); t = np.array(all_t); Ln = np.array(all_L); w = np.array(all_v)
    def wq(x, q):
        o = np.argsort(x); cw = np.cumsum(w[o]) / w.sum()
        return float(np.interp(q, cw, x[o]))
    print('   ---- 全部块（n=%d, 总体积 %.2f um^3）----' % (len(ar), w.sum()))
    print('   长径比 a/c : 中位 %.2f  p25 %.2f  p75 %.2f  体积加权中位 %.2f'
          % (np.median(ar), np.percentile(ar, 25), np.percentile(ar, 75), wq(ar, 0.5)))
    print('   板条厚 2c  : 中位 %.3f um  p25 %.3f  p75 %.3f   -> 文献 0.25-0.9 um'
          % (np.median(t) * 1e6, np.percentile(t, 25) * 1e6, np.percentile(t, 75) * 1e6))
    print('   板条长 2a  : 中位 %.3f um                       -> 文献 1-20 um'
          % (np.median(Ln) * 1e6))
    print('   文献长径比 10-30（板条）; 集束/群 1-3')
