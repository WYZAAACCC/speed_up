#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_cost.py —— **代价估计**：逐点 27 点 LSQ 平面拟合在引擎网格上值不值。

## 为什么要单独测
结论（`_r727_verdict.py`）已经定：**要真 LSQ 精度，就必须做逐点 27 点拟合**；
箱和形式有 `O((dx/R)²)` 的曲率偏置（正弦场实测差 **2800 倍**）。
⇒ 但"逐点"听起来贵 ⇒ **先量，再决定**（`R577` 的教训：占比大 ≠ 能提速；反过来也一样）。

## 口径
* 网格取引擎生产口径：`N=96`（88.5 万胞）
* 两个实现：
  * **naive**：`np.pad(wrap)` + 27 个切片堆叠（我 `_r723` 用的写法）
  * **moments**：只算 4 个矩（`S_ijk` 的 13 个不同乘子）→ 向量化
* 判据：与既有 `ndir_` 构造（`par.gradient` = `np.gradient`）的**墙钟比**
* 纪律：`R630`（≤4 核、`nice=10`）；但本测是**单线程微基准**，故只报"相对倍数"

## 用法
    python3 _r727_cost.py [--N 96] [--reps 3]
"""
import argparse
import sys
import time

import numpy as np


def naive_lsq(f, dx):
    """我 `_r723` 的写法：27 个切片堆叠 + pinv。"""
    off = np.array([(i, j, k) for i in (-1, 0, 1)
                    for j in (-1, 0, 1) for k in (-1, 0, 1)], float) * dx
    A = off - off.mean(0)
    pinv = np.linalg.pinv(A)
    N = f.shape[0]
    fp = np.pad(f, 1, mode='wrap')
    blk = np.stack([fp[i:i + N, j:j + N, k:k + N]
                    for i in range(3) for j in range(3) for k in range(3)], -1)
    b = blk - blk.mean(-1, keepdims=True)
    return np.einsum('ij,...j->...i', pinv, b)


def moments_lsq(f, dx):
    """用 **13 个逐点乘子** 装配 `Σ r_i f(x+r)`（`r` 只取 (−1,0,1)³）。

    `Σ r_x f = dx·[ (f₊₊₊+f₊₀₊+f₊₋₊+…) − (f₋…) ]`
    ⇒ 只要 6 个"面"上的 3×3 和：`P_x⁺ = f(x+1,·,·)` 的 3×3 和，`P_x⁻` 同理。
    用 `np.roll` 取 6 个面，再用两次 1D 加和做 3×3 和 ⇒ **无 pad、无堆叠**。
    """
    out = []
    for ax in range(3):
        # 面 x±1，然后对另外两轴做 3 点周期和
        sp = np.roll(f, -1, ax)
        sm = np.roll(f, +1, ax)
        others = [a for a in range(3) if a != ax]
        for a in others:
            sp = sp + np.roll(sp, 1, a) + np.roll(sp, -1, a)
            sm = sm + np.roll(sm, 1, a) + np.roll(sm, -1, a)
        out.append(dx * (sp - sm) / 4.0)     # ⚠ 常数 4.0 由下面前置对照标定
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
    print('代价微基准（N=%d，%d 胞，单线程）' % (N, N ** 3))
    print('=' * 96)

    def bench(fn, label):
        fn(f, dx)                                   # warm-up
        ts = []
        for _ in range(a.reps):
            t0 = time.perf_counter()
            fn(f, dx)
            ts.append(time.perf_counter() - t0)
        t = float(np.median(ts))
        print('  %-26s 中位 = %.4f s   (min %.4f / max %.4f)'
              % (label, t, min(ts), max(ts)))
        return t

    t_grad = bench(lambda x, d: np.gradient(x, d, edge_order=2), 'np.gradient（既有路径）')
    t_naive = bench(naive_lsq, 'naive LSQ（27 切片堆叠）')
    t_mom = bench(moments_lsq, 'moments LSQ（6 面 roll）')

    print()
    print('  ⇒ 相对 `np.gradient`：naive **%.2f×**、moments **%.2f×**'
          % (t_naive / t_grad, t_mom / t_grad))
    print()
    print('  ⚠ 记账：本测只跑**一个** `advance` 里的法向构造；')
    print('    它在整步里的占比**未测**（须在真实步里量，`R581` 的纪律 P17）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
