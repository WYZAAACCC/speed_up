#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_membench.py —— 量具在 **N=192 生产尺寸**下的耗时与峰值内存（优化前后对比用）。

优化前（v1）：一次 `measure_state` 会造 3×N³ float64 坐标网格 + `rel` + `pa/pw/pn`
⇒ 单次 ~500 MB 瞬时；生产跑每 5 步一次 ⇒ 把 WSL 推到 swap 99.9%。
优化后（v2）：质心用可分离投影、柱/尺寸只在小包围盒上算 ⇒ 应为 **十几 MB**。
"""
import os
import resource
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main():
    N, dx = 192, 62.5e-9
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    wa = np.array([0.7071, 0.7071, 0.0]); wa /= np.linalg.norm(wa)
    aa = np.array([-0.4909, 0.4909, 0.7198]); aa /= np.linalg.norm(aa)
    reg = np.zeros((N, N, N), np.int8)
    c = np.array([N * dx / 2] * 3)
    ii = np.arange(N) * dx
    rel = [ii[:, None, None] - c[0], ii[None, :, None] - c[1],
           ii[None, None, :] - c[2]]
    pn = nh[0] * rel[0] + nh[1] * rel[1] + nh[2] * rel[2]
    pa = aa[0] * rel[0] + aa[1] * rel[1] + aa[2] * rel[2]
    pw = wa[0] * rel[0] + wa[1] * rel[1] + wa[2] * rel[2]
    for i in range(6):
        off = (i - 2.5) * 250e-9
        reg[(np.abs(pn - off) <= 125e-9) & (np.abs(pa) <= 1200e-9)
            & (np.abs(pw) <= 320e-9)] = i + 1
    del rel, pn, pa, pw
    m0 = rss_mb()
    t = time.time()
    r = BM.measure_state(reg, dx, nh, wa, aa, {i + 1: 1 for i in range(6)})
    dt = time.time() - t
    print('N=192  单次 measure_state: %.2f s ; 峰值 RSS %.0f -> %.0f MB (+%.0f)'
          % (dt, m0, rss_mb(), rss_mb() - m0))
    print('  nslab_n=%d  nf3_col=%d  runs=%s  f3_area=%.4f µm²  ncomp_max=%d'
          % (r['nslab_n'], r['nf3_col'], r['runs'], r['f3_area'] * 1e12,
             max(r['ncomp_%d' % k] for k in range(1, 7))))
    print('  判据：nslab_n==6 且 nf3_col==5 且 ncomp_max==1  ⇒ %s'
          % ('PASS' if (r['nslab_n'] == 6 and r['nf3_col'] == 5
                        and max(r['ncomp_%d' % k] for k in range(1, 7)) == 1)
             else '**FAIL**'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
