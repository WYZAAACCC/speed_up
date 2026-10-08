#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r729_cost2.py —— **标定后**的代价：`lsq_moments`（常数 1/18）vs `np.gradient`。

⚠ 与 `_r727_cost.py` 的区别：那次用的是**临时未标定**的 `/4.0`，**数字不可信**；
本次用 `_r729_verify.py` 已验（与 `pinv` 逐点一致）的常数 **1/18**。
"""
import argparse
import sys
import time

import numpy as np

C = 1.0 / 18.0


def lsq_moments(f, dx):
    """4 个矩 → 3 分量梯度。可分离、周期、`np.correlate`（不翻转核）。"""
    K0 = np.ones(3)
    K1 = np.array([-1.0, 0.0, 1.0]) * dx

    def corr1(a, k, ax):
        a = np.moveaxis(a, ax, 0)
        p = np.concatenate([a[-1:], a, a[:1]], axis=0)
        a = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
        return np.moveaxis(a, 0, ax)

    def tp(kx, ky, kz):
        return corr1(corr1(corr1(f, kx, 0), ky, 1), kz, 2)
    return C * np.stack([tp(K1, K0, K0), tp(K0, K1, K0), tp(K0, K0, K1)], -1)


def lsq_moments_fast(f, dx):
    """**优化版**：把 `K0` 的 3 点和与 `K1` 的差分合并成"加权 3 点和"，
    减少一次全数组遍历（3 个分量 × 2 次 → 1 次）。"""
    # Σ_{s∈{−1,0,1}} w_s f(x+s) ，其中对目标轴 w = (−dx, 0, +dx)，对另两轴 w = (1,1,1)
    out = []
    for tgt in range(3):
        acc = None
        for s in (-1, 0, 1):
            w = (s * dx) if s != 0 else 0.0
            if w == 0.0:
                continue
            a = np.roll(f, -s, tgt) * w
            for other in range(3):
                if other == tgt:
                    continue
                a = a + np.roll(a, 1, other) + np.roll(a, -1, other)
            acc = a if acc is None else acc + a
        out.append(C * acc)
    return np.stack(out, -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--reps', type=int, default=3)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    N = a.N
    f = rng.standard_normal((N, N, N))
    dx = 62.5e-9
    print('=' * 96)
    print('标定后代价微基准（N=%d = %d 胞，单线程，nice 10）' % (N, N ** 3))
    print('=' * 96)

    # 先证 优化版 == 参考版（逐位）
    g1 = lsq_moments(f, dx)
    g2 = lsq_moments_fast(f, dx)
    d = float(np.abs(g1 - g2).max() / (np.abs(g1).max() + 1e-300))
    print('  前置：`fast` 与 `ref` 的相对差 = %.3e  ⇒ %s'
          % (d, '✅ 一致' if d < 1e-12 else '⛔ 不一致'))

    def bench(fn, label):
        fn(f, dx)
        ts = []
        for _ in range(a.reps):
            t0 = time.perf_counter()
            fn(f, dx)
            ts.append(time.perf_counter() - t0)
        t = float(np.median(ts))
        print('  %-30s 中位 = %.4f s' % (label, t))
        return t

    t_g = bench(lambda x, d_: np.gradient(x, d_, edge_order=2), 'np.gradient（既有）')
    t_r = bench(lsq_moments, 'lsq_moments（可分离相关）')
    t_f = bench(lsq_moments_fast, 'lsq_moments_fast（roll 合并）')
    print()
    print('  ⇒ 相对 `np.gradient`：相关版 **%.2f×**、roll 版 **%.2f×**'
          % (t_r / t_g, t_f / t_g))
    step = 2.89
    print()
    print('  折进真实单步（`B2P_q0` @step100 实测 **%.2f s/步**）：' % step)
    print('     相关版 +%.1f ms = 单步 **+%.2f%%**' % (t_r * 1e3, 100 * t_r / step))
    print('     roll 版 +%.1f ms = 单步 **+%.2f%%**' % (t_f * 1e3, 100 * t_f / step))
    print()
    print('  ⚠ 记账：单线程微基准；引擎 4 线程 ⇒ 真实占比可能不同（`P15`）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
