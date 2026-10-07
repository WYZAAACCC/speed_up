#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r406_chain.py —— 量化"块是不是排成一条线"：共线性 + 间距分布 + 邻居数。"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
DX_NM = 62.5


def main():
    for tag in (sys.argv[1:] or ['saSet2P0', 'saSet2']):
        d = os.path.join(MB, 'dry_' + tag)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
        if not fs:
            print('%-12s ⚠ 无快照' % tag); continue
        z = np.load(fs[-1], allow_pickle=True)
        reg = np.asarray(z['region'], np.int64)
        vk = np.asarray(z['vmap_keys'], np.int64)
        vv = np.asarray(z['vmap_vals'], np.int64)
        var = {int(a): int(b) for a, b in zip(vk, vv)}
        C, V = [], []
        for v in sorted(set(var.values())):
            m = np.isin(reg, [k for k in var if var[k] == v])
            if m.sum() < 50:
                continue
            C.append(np.argwhere(m).mean(0) * DX_NM * 1e-3)   # µm
            V.append(v)
        C = np.asarray(C)
        print('=' * 84)
        print('### %s  step=%s  显著块数 = %d' % (tag, z['step'], len(C)))
        for v, c in zip(V, C):
            print('   V%-2d 块心 = [%.2f %.2f %.2f] µm' % (v, c[0], c[1], c[2]))
        if len(C) < 3:
            continue
        c0 = C.mean(0)
        X = C - c0
        U, S, Vt = np.linalg.svd(X, full_matrices=False)
        # 共线性：第一主成分解释的方差占比；以及各点到最佳拟合直线的垂距
        axis = Vt[0]
        para = X @ axis
        perp = X - np.outer(para, axis)
        dev = np.linalg.norm(perp, axis=1)
        print('  ## 共线性')
        print('     第一主成分方差占比 = **%.4f**（1.0 = 完全共线）'
              % (S[0] ** 2 / (S ** 2).sum()))
        print('     沿链方向的坐标 = %s µm' % np.round(para, 2).tolist())
        print('     各点到最佳直线的垂距 = %s µm（最大 %.2f）'
              % (np.round(dev, 2).tolist(), dev.max()))
        print('     链总长 = %.2f µm；盒棱 = %.2f µm'
              % (para.max() - para.min(), float(z['L']) * 1e6))
        dd = np.linalg.norm(np.diff(C[np.argsort(para)], axis=0), axis=1)
        print('     相邻块心距 = %s µm（均值 %.2f，极差 %.2f–%.2f）'
              % (np.round(dd, 2).tolist(), dd.mean(), dd.min(), dd.max()))
        # 邻居数：以"块心距 < 2× 块半径"判接触
        nbr = (np.linalg.norm(C[:, None, :] - C[None, :, :], axis=-1) < 2.0).sum(1) - 1
        print('     每块的邻居数（块心距 < 2 µm 计） = %s'
              % (nbr.tolist()))


if __name__ == '__main__':
    sys.exit(main())
