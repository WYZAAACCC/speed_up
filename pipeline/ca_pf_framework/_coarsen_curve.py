#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_coarsen_curve.py --- 决定性问题: 域尺度是"能量极小"还是"动力学假象"?

做法: 取一个已算好的末态标签场, 用 2x2x2 多数投票**逐级粗化**(尺度 x2), 每一级量
      E_el(精确 FFT) 与 E_surf(各向异性面积测度), 画 E_tot(域尺度)。
判读:
   * 若 E_tot 在末态尺度附近有**极小** ⇒ 真平衡, 尺度由"面能 vs 弹性能"决定 ✅
   * 若 E_tot 随粗化**单调下降** ⇒ 末态是被动力学钉住的假象, 需要更强的粗化算法 ✗
（注意: 多数投票粗化会改变界面能测量本身的离散精度, 故同时报告 E_surf 的连续估计）
"""
import os
import sys
import numpy as np
from windowB_gibbs import GibbsLath, pairs6
from windowB_pf3d import C_iso3
from windowB_ti64_variants import variants

OUT = '/mnt/f/speed_up/bench/windowB_gibbs'


def coarsen_once(lab):
    """2x2x2 多数投票（平局取已有的多数；全不同取原值）"""
    N = lab.shape[0]
    if N % 2:
        lab = lab[:-1, :-1, :-1]
        N -= 1
    v = lab.reshape(N // 2, 2, N // 2, 2, N // 2, 2)
    out = np.zeros((N // 2, N // 2, N // 2), np.int8)
    for a in range(2):
        for b in range(2):
            for c in range(2):
                out = np.where(np.zeros_like(out, bool), out, out)  # 占位
    # 逐块取众数
    from collections import Counter
    for i in range(N // 2):
        for j in range(N // 2):
            for k in range(N // 2):
                blk = lab[2 * i:2 * i + 2, 2 * j:2 * j + 2, 2 * k:2 * k + 2]
                out[i, j, k] = Counter(blk.ravel().tolist()).most_common(1)[0][0]
    return out


def surf_bonds(lab):
    c = 0
    for d in pairs6():
        c += int(np.count_nonzero(np.roll(lab, d, axis=(0, 1, 2)) != lab))
    return c // 2


def main(tag='_a0', dx=2.0e-8):
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    lab = np.load(os.path.join(OUT, 'lab%s.npy' % tag))
    print('=' * 92)
    print('粗化曲线 (tag=%s, 初始 N=%d, dx=%.1f nm)' % (tag, lab.shape[0], dx * 1e9))
    print('=' * 92)
    print('%-8s %10s %14s %14s %14s %12s' %
          ('尺度/nm', '胞数', 'E_el', 'E_surf', 'E_tot', '6V/A nm'))
    rows = []
    while lab.shape[0] >= 8:
        N = lab.shape[0]
        L = N * dx
        g = GibbsLath(N, L, C, eps0, gamma=0.15, df=5e8, workers=4, k0_mode='clamped')
        g.lab[:] = lab
        Eel = g.E_el()
        Es = g.E_surf()
        nb = surf_bonds(lab)
        lscale = 6 * (N * dx) ** 3 / max(nb * dx ** 2, 1e-30) if nb else np.inf
        rows.append((lscale, N, Eel, Es, Eel + Es, nb))
        print('%-8.1f %10d %14.4e %14.4e %14.4e %12.1f'
              % (lscale * 1e9, N, Eel, Es, Eel + Es, lscale * 1e9))
        if N <= 8:
            break
        lab = coarsen_once(lab)
    print('\n判读: 若 E_tot 随粗化单调下降 ⇒ 当前末态尺度是【动力学假象】;')
    print('      若在某尺度取极小 ⇒ 该尺度是【面能 vs 弹性能】的真平衡。')
    return rows


if __name__ == '__main__':
    tg = sys.argv[1] if len(sys.argv) > 1 else '_a0'
    dx = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0e-8
    main(tg, dx)
