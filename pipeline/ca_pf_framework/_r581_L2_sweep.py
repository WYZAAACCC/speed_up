#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L2_sweep.py --- L2 的**参数扫描**：`eps0_fields_stream` 的首轴 slab / chunk 最优值。

## 背景（`_w2_r581_L2_epsh.log`）
首轮候选实测：末轴 slab **更慢**（0.55–0.62×，因为 `e[p,:,:,z0:z1]` 是跨行切片），
**首轴 slab 更快**（N=64 1.179×、N=96 **1.509×**，全部逐位）。
⇒ 本脚本只在**首轴 slab** 上扫 `slab ∈ {2,4,8,12,16,24,32}` × `chunk ∈ {1,2,4,8}`，
   找出最优，并报出**逐位一致性**（每档都要 `array_equal`）。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

sys.argv = ['x']
import _r581_L2_epsh as B           # 复用它的算例与基线

REPS = 5
NV = 48


def s2(e0v, h_at, nv, N, chunk, slab):
    e = np.zeros((6, N, N, N))
    for x0 in range(0, N, slab):
        x1 = min(x0 + slab, N)
        for v0 in range(0, nv, int(chunk)):
            v1 = min(v0 + int(chunk), nv)
            h = h_at(v0, v1, x0, x1)
            for j in range(v1 - v0):
                hj = h[j]
                for p in range(6):
                    e[p, x0:x1] += e0v[v0 + j, p] * hj
    return e


def main():
    L = ['=' * 100, 'R581-L2 sweep —— 首轴 slab / chunk 扫描（`eps0_fields_stream`）',
         '=' * 100]
    for N in (64, 96):
        e0v, phi, h_at_full, _w = B.make_case(N)

        def H0(v0, v1, z0=None, z1=None):
            return h_at_full(v0, v1, z0, z1, ax=0)
        ref = B.s0(e0v, H0, NV, N)
        L.append('')
        L.append('── N=%d  nv=%d  `e`=%.1f MB ──' % (N, NV, 6 * N ** 3 * 8 / 2 ** 20))
        L.append('  %-8s %-7s %-10s %-22s %s'
                 % ('slab', 'chunk', '中位 s', '区间', '提速（vs 归档）'))
        L.append('  ' + '-' * 78)
        combos = [(c, s) for s in (2, 4, 8, 12, 16, 24, 32) for c in (2, 4, 8)]
        # 先量基线
        tb = []
        for _ in range(REPS):
            t0 = time.perf_counter(); B.s0(e0v, H0, NV, N); tb.append(time.perf_counter() - t0)
        base = sorted(tb)[REPS // 2]
        best = []
        for (c, s) in combos:
            got = s2(e0v, H0, NV, N, c, s)
            neq = int(np.count_nonzero(got != ref))
            ts = []
            for _ in range(REPS):
                t0 = time.perf_counter(); s2(e0v, H0, NV, N, c, s)
                ts.append(time.perf_counter() - t0)
            m = sorted(ts)[REPS // 2]
            best.append((base / m, c, s, m, ts))
            L.append('  %-8d %-7d %-10.4f %-22s **%.3f×**  %s'
                     % (s, c, m, '[%.4f, %.4f]' % (min(ts), max(ts)), base / m,
                        '✅逐位' if neq == 0 else '❌不逐位'))
        best.sort(reverse=True)
        L.append('  ⇒ 归档基线中位 %.4f s' % base)
        L.append('  ⇒ ★ 最优：slab=%d chunk=%d ⇒ **%.3f×**（%.4f s）'
                 % (best[0][2], best[0][1], best[0][0], best[0][3]))
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L2_sweep.log', 'w').write(out + '\n')


if __name__ == '__main__':
    main()
