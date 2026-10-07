#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r190_dbg189.py —— 诊断 `_r189` 的 45° 平面对照为什么"没找到界面"。

只做最小复现 + 逐步骤打印，不下物理结论。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _r189_ncmp_from_region import c2p_of_snapshot, load_ncmp, smooth  # noqa: E402


def main():
    ncmp = load_ncmp()
    i, j = 1, 2
    nj = ncmp[j, i] / np.linalg.norm(ncmp[j, i])
    print('ncmp[%d,%d] = %s  |n|=%.6f' % (i, j, nj, np.linalg.norm(nj)))
    N, dx = 40, 1e-8
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)

    t = np.array([nj[1], -nj[0], 0.0])
    print('t（应 ⟂ nj）= %s  |t|=%.6g  t·nj=%.3e'
          % (t, np.linalg.norm(t), float(t @ nj)))
    t = t / (np.linalg.norm(t) + 1e-300)
    n45 = (nj + t) / np.linalg.norm(nj + t)
    print('n45 = %s  |n45|=%.6f  n45·nj=%.6f（期望 0.7071）'
          % (n45, np.linalg.norm(n45), float(n45 @ nj)))

    for tag, nv in (('n∥ncmp', nj), ('n45', n45)):
        proj = X @ nv
        reg = np.zeros((N, N, N), np.int8)
        reg[proj > 0] = i
        reg[proj <= 0] = j
        print()
        print('== %s ==' % tag)
        print('   region 取值计数：%s'
              % dict(zip(*[a.tolist() for a in np.unique(reg, return_counts=True)])))
        # 6 邻域接触
        contact = set()
        for ax in range(3):
            a = np.take(reg, range(reg.shape[ax] - 1), axis=ax)
            b = np.take(reg, range(1, reg.shape[ax]), axis=ax)
            m = (a > 0) & (b > 0) & (a != b)
            print('   axis=%d 相邻且异号的胞对数 = %d' % (ax, int(m.sum())))
            if m.any():
                for xx, yy in zip(a[m].ravel(), b[m].ravel()):
                    contact.add((min(int(xx), int(yy)), max(int(xx), int(yy))))
        print('   contact 集合 = %s' % sorted(contact))
        # 平滑带
        s = ((reg == i).astype(float) - (reg == j).astype(float))
        ss = smooth(s, 2.0)
        g = np.stack(np.gradient(ss, dx), -1)
        nrm = np.linalg.norm(g, axis=-1)
        band = (np.abs(ss) < 0.5) & (nrm > 0)
        print('   |ss|<0.5 的胞数 = %d ；nrm>0 的胞数 = %d ；band 胞数 = %d'
              % (int((np.abs(ss) < 0.5).sum()), int((nrm > 0).sum()),
                 int(band.sum())))
        print('   ss 的范围 = [%.4f, %.4f]' % (ss.min(), ss.max()))
        if band.any():
            nh = g[band] / nrm[band][:, None]
            c2 = np.einsum('ni,i->n', nh, nj) ** 2
            print('   band 内 c2p 中位 = %.4f（band 胞数 %d）'
                  % (float(np.median(c2)), band.sum()))
        c2b, pr = c2p_of_snapshot(reg, ncmp, dx, sig=2.0)
        print('   c2p_of_snapshot ⇒ %s ；pairs=%s'
              % ('None' if c2b is None else '中位 %.4f, n=%d'
                 % (float(np.median(c2b)), len(c2b)), pr))
    return 0


if __name__ == '__main__':
    sys.exit(main())
