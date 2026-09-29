#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT ★★★ 判决实验：`phi` 里到底有没有**亚胞信息**？

* 若 `phi` 是 **±1 二值**（不是 SDF）⇒ 标签界面就是它的完整信息 ⇒
  `region` **无损**，`phi` 落盘对"重算几何结论"**没有增量**（只是方便）。
* 若 `phi` 是连续 SDF（有中间值）⇒ 亚胞位置只能从 `phi` 读 ⇒ 不存就是真缺。

同时量化：把 `phi` **二值化**（`phi>0 ⇒ 1`）后，界面位置/面积/厚度差多少。
用法: python3 _r30_phibin.py <dir-or-npz> ...
"""
import glob
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _bk_measure as BM                                          # noqa: E402


def stats(p):
    z = np.load(p, allow_pickle=False)
    phi = z['phi']
    reg = z['region']
    u = np.unique(phi)
    # 完整直方图（用分位近似，避免 N³ 排序）
    frac_mid = float(((np.abs(phi) > 1e-6) & (np.abs(phi) < 0.999)).mean())
    print('%s' % p.replace('/mnt/f/speed_up/pipeline/ca_pf_framework/', ''))
    print('   phi: shape=%s dtype=%s  唯一值个数=%d' % (phi.shape, phi.dtype,
                                                       u.size))
    print('   前 12 个唯一值: %s' % np.array2string(u[:12], precision=6))
    print('   后 12 个唯一值: %s' % np.array2string(u[-12:], precision=6))
    print('   |phi| 落在 (1e-6, 0.999) 的占比 = %.6f  ⇒ %s'
          % (frac_mid, '**二值**（无亚胞信息）' if frac_mid < 1e-4
             else '**连续 SDF**（含亚胞信息）'))
    print('   phi 取值 = {%s} 等' % ', '.join('%.4g' % v for v in u[:8]))
    # region vs argmax 一致性
    am = np.argmax(phi, axis=0)
    print('   region == argmax(phi) 的占比 = %.6f'
          % float((reg == am).mean()))
    z.close()


def binarize_and_compare(p):
    z = np.load(p, allow_pickle=False)
    phi = z['phi'].astype(np.float64)
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    nv = phi.shape[0]
    print('   --- 二值化对照 (%s) ---' % os.path.basename(p))
    # 连续口径的界面位置：取 (phi_i - phi_j) = 0 的线性插值零点
    # 二值口径：先二值化再取梯度
    for ki, kj in [(1, 2), (1, 3), (2, 3)]:
        if ki >= nv or kj >= nv:
            continue
        d = phi[ki] - phi[kj]
        db = np.sign(d)
        n_mid = int(((d > -0.999) & (d < 0.999)).sum())
        n_midb = int(((db > -0.999) & (db < 0.999)).sum())
        print('     对 %d-%d: |d|<0.999 的胞数  连续=%d  二值化后=%d'
              % (ki, kj, n_mid, n_midb))
    z.close()


for a in sys.argv[1:]:
    ps = sorted(glob.glob(os.path.join(a, 'snap_*.npz'))) \
        if os.path.isdir(a) else [a]
    for p in ps[:2]:
        stats(p)
        binarize_and_compare(p)
        print()
