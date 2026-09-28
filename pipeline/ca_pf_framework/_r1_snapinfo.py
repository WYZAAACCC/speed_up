#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_snapinfo.py --- 快照解剖：碎裂到底是"什么"碎了（不需要引擎，秒级）

为什么需要
----------
阶段③（实验 4/6）在 step ~120 起出现**大量连通分量**：
`e4_lath6` 的 `ncomp` 21→24、最大分量只占 **17%**；`e6_mid6` 的 `ncomp` 到 **51**。
必须回答：**是主块裂开了，还是主块完好、旁边多了一堆小碎片？**
两者的物理含义完全不同，而 `nc`/`big_frac` 两个汇总数**分不开**它们。

做法
----
读 `snap_XXXXX.npz` 的 `region()`（int8）⇒ `scipy.ndimage.label` ⇒
按体积排序，报**每个分量的体积、质心、沿 a/w/n* 的跨度**，以及
"去掉小于 k 胞的碎片之后，主分量还剩多少"。
"""
import os
import sys
import glob
import argparse

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ap = argparse.ArgumentParser()
ap.add_argument('snaps', nargs='*')
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--kv', type=int, default=1)
ap.add_argument('--top', type=int, default=10)
ap.add_argument('--series', default=None,
                help='给定一个 `_exp/<name>` 目录：遍历**全部**快照，输出'
                     ' `nsig`/`debris`/`big_frac` 的**时间序列** CSV 到该目录')
a = ap.parse_args()
dx = a.dx_nm * 1e-9

if a.series:
    d = a.series if os.path.isabs(a.series) else os.path.join(HERE, a.series)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                   key=lambda p: int(os.path.basename(p)[5:-4]))
    print('遍历 %d 个快照：%s' % (len(snaps), d))
    rows = []
    for p in snaps:
        z = np.load(p)
        reg = z['region']
        step = int(z['step'])
        m = (reg == a.kv)
        tot = int(m.sum())
        if tot < 8:
            continue
        lab, ncomp = nd.label(m)
        sz = np.bincount(lab.ravel())[1:]
        thr = 0.01 * tot
        sig = int((sz >= thr).sum())
        big = int(sz.max())
        rows.append((step, ncomp, sig, big / tot, 1.0 - sz[sz >= thr].sum() / tot))
    out = os.path.join(d, 'components.csv')
    with open(out, 'w') as f:
        f.write('step,ncomp,nsig,big_frac,debris\n')
        for r in rows:
            f.write('%d,%d,%d,%.6g,%.6g\n' % r)
    print('已写 %s' % out)
    print('  %6s %8s %8s %10s %10s' % ('step', 'ncomp', 'nsig', 'big_frac', 'debris'))
    for r in rows:
        print('  %6d %8d %8d %10.4f %10.4f' % r)
    sys.exit(0)

import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, DF, MOB                 # noqa: E402
from _r1_exp import axes_of                                     # noqa: E402

for sp in a.snaps:
    for pat in ([sp] if os.path.exists(sp) else
                sorted(glob.glob(os.path.join(HERE, sp, 'snap_*.npz')))[-3:]):
        z = np.load(pat)
        reg = z['region']
        step = int(z['step']) if 'step' in z else -1
        print('=' * 96)
        print('快照 %s  step=%d' % (os.path.relpath(pat), step))
        for K in ([a.kv] if a.kv > 0 else sorted(set(reg.ravel().tolist()))):
            m = (reg == K)
            nc_all = int(m.sum())
            if nc_all < 8:
                continue
            lab, ncomp = nd.label(m)
            sz = np.bincount(lab.ravel())
            order = np.argsort(-sz[1:]) + 1
            big = sz[order[0]]
            print('  变体 V%d：总胞 %d，分量数 %d，最大分量 %d 胞（%.1f%%）'
                  % (K, nc_all, ncomp, big, 100.0 * big / nc_all))
            # 去掉碎片后的"主分量"
            for kmin in (1, 8, 50, 500):
                keep = sum(s for s in sz[1:] if s >= kmin)
                print('     去掉 <%-4d 胞的碎片后剩 %6d 胞（%.1f%%），'
                      '碎片贡献 %5.1f%%'
                      % (kmin, keep, 100.0 * keep / nc_all,
                         100.0 * (nc_all - keep) / nc_all))
            print('     最大 %d 个分量：' % min(a.top, ncomp))
            for ci in order[:a.top]:
                mm = (lab == ci)
                n = int(mm.sum())
                idx = np.argwhere(mm).astype(np.float64)
                c = idx.mean(0) * dx * 1e6
                print('        #%-3d %7d 胞  %5.1f%%  质心 (%.2f, %.2f, %.2f) µm'
                      % (ci, n, 100.0 * n / nc_all, c[0], c[1], c[2]))
        print()
