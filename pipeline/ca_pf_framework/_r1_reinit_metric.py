#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_metric.py --- R1 reinit 审计（第 6 步）：**判据量具的交叉核对**。

动机（Q-A 首轮读数逼出来的问题）
--------------------------------
Q-A 用**中心差分** `np.gradient(..., edge_order=2)` 量带内 `median|∇d2|`（与引擎
`reinitialize()` 里那段"运行期告警"用**同一个**口径）。Q-A 实测：**该量在
iters=20–36 处先掉到 0.92–0.93，到 iters≥75 才回到 ~0.99**（非单调）。

但 Sussman 算子**驱动的**是**二阶 ENO 迎风** `upwind_grad2`。仓库已有记账
（`_probe_grad_fixpoint.py`）：**同一场**上用中心差分量全域 max = **1.00**，
而用 `upwind_grad2` 量全域 max = **68.5** ⇒ 两个量具在**脊线/中轴**上差别巨大。

⇒ 必须先分清：med_out 的"先掉后回"到底是
    ① 算子**在自己驱动的量上**也没收敛好（= 迭代不够，降 iters 确实不安全），还是
    ② 算子收敛了，而**中心差分这把尺子**在带内被脊线污染（= 判据本身不可靠）。
本文件在**同一份冻结场**上同时报两个量具 + 一个**基座**：`upwind_grad2` 的带内**中位**
（不是 max，避免一个脊线胞主导）。

★ 只读引擎；不改任何引擎代码。输入 `_r1_reinit_states.npz`。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 6.0
TAGCFG = {'C1': (96 * 250e-9, 250e-9), 'C2': (96 * 125e-9, 125e-9)}
LAD = [0, 5, 10, 20, 30, 36, 50, 75, 100, 150, 200]


def g_central(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def g_upw(f, dx):
    """引擎实际驱动的那个量（`upwind_grad2`，符号取真值 `sign(phi0)`）"""
    s = np.sign(f)
    s[s == 0] = 1.0
    return W.upwind_grad2(f, s, dx)


def active_pairs(reg):
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    return sorted(pairs)


def main():
    z = np.load(os.path.join(HERE, '_r1_reinit_states.npz'))
    print('=' * 120)
    print('R1 reinit 审计 / 两个 |∇d2| 量具的交叉核对（中心差分 vs upwind2，带内**中位**）')
    print('  目的：判定 Q-A 里 med_out 的"先掉后回"是"迭代不够"还是"尺子被脊线污染"')
    print('=' * 120)
    gcache = {}
    for key in sorted(z.files):
        phi0 = z[key]
        tag = key.split('_')[0]
        N = phi0.shape[1]
        L, dx = TAGCFG[tag]
        if tag not in gcache:
            t0 = time.time()
            gcache[tag] = W.LevelSetMulti(
                N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                reinit_dt=None, reinit_band_cells=BAND)
            print('\n####### 配置 %s 建表 %.1f s' % (tag, time.time() - t0), flush=True)
        g = gcache[tag]
        reg = np.argmin(phi0, axis=0).astype(np.int8)
        cand = []
        for (k, l) in active_pairs(reg):
            d2 = 0.5 * (phi0[k] - phi0[l])
            cand.append((int((np.abs(d2) <= BAND * dx).sum()), k, l))
        cand.sort(reverse=True)
        nb, k, l = cand[0]
        d2_in = 0.5 * (phi0[k] - phi0[l])
        near = np.abs(d2_in) <= BAND * dx
        print('\n  #### %s  配对(k=%d,l=%d) 带胞=%d (%.3f%% of N³)  #d2<0=%d'
              % (key, k, l, nb, 100 * nb / d2_in.size, int((d2_in < 0).sum())),
              flush=True)
        print('  %6s %12s %12s %12s %12s %12s %12s %10s'
              % ('iters', 'med|∇|中心', 'med|∇|迎风', 'max|∇|中心', 'max|∇|迎风',
                 'Δ#{d2<0}', 'Δmed中心(胞)', '用时(s)'))
        for n in LAD:
            t0 = time.time()
            dn = d2_in.copy() if n == 0 else g.sussman_reinit(d2_in.copy(), iters=n)
            el = time.time() - t0
            gc_ = g_central(dn, dx)[near]
            gu_ = g_upw(dn, dx)[near]
            print('  %6d %12.5f %12.5f %12.3f %12.3f %12d %+12.5f %10.2f'
                  % (n, float(np.median(gc_)), float(np.median(gu_)),
                     float(gc_.max()), float(gu_.max()),
                     int((dn < 0).sum()) - int((d2_in < 0).sum()),
                     (np.median(dn[near]) - np.median(d2_in[near])) / dx, el),
                  flush=True)
    print()
    print('  ★ 判读规则（先定死，再看数）：')
    print('    · 若 `med|∇|迎风` 在某个 iters 处已≈1 且此后不再改善 ⇒ 算子**收敛**了，')
    print('      中心差分列的"先掉后回"是**尺子**的问题 ⇒ 不能用它当"迭代不足"的证据。')
    print('    · 若 `med|∇|迎风` 也随 iters 单调改善且到 100 仍明显≠1 ⇒ 确实迭代不够。')
    print('=' * 120)
    return 0


if __name__ == '__main__':
    sys.exit(main())
