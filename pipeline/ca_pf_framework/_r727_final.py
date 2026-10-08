#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_final.py —— **R727 §2.1 代数式的最终形式**（常数与 pad 由**数值反解**，不手推）。

## 我在这一条上犯的错（**全部留痕**，`R712 §0.5` 纪律）
| 版 | 断言 | 结果 |
|---|---|---|
| `_r727_lsq_equiv.py` | 「箱和 `(1/6)[S_{i+1}−S_{i−1}]` ≡ 27 点 LSQ 平面拟合」 | ⛔ **证否**（球面 0.102° vs LSQ 0.037°）。根因：箱和把**二次项** `tr(H)/(2·3)` 混进法向（球面 = `1/(3R)`），而真 LSQ 在原点是精确的 |
| `_r727_lsq_exact.py` | 「可分张量积 (K1,K0,K0)，常数 `3/n`」 | ⛔ **常数差 2 倍**（"胞中心 vs 胞边界"因子），且**边界 pad 少一格** |
| **本文件** | 常数与 pad **由线性场数值反解**，再验球面 | 见输出 |

★ **这正是判据 `J-6/J-7` 存在的意义** —— 它们把我两次错的代数式当场抓出来了。

## 口径（**最终、可复现**）
```
g_α = c · (K1 ⊗ K0 ⊗ K0) f        （α = x/y/z，K1 放在对应轴上）
K0 = [1,1,1]   K1 = [−1,0,+1]·Δx      （用 np.correlate，**不翻转**）
c  = 由**线性场**反解（解析值 3/27 = 0.1111…；本实现实测 3/54，见输出）
pad = 宽度须 ≥ 1 且逐轴
```

## 用法
    python3 _r727_final.py
"""
import sys

import numpy as np

K0 = np.array([1.0, 1.0, 1.0])


def corr1(f, k, ax, padw=2):
    """周期 1D **相关**（不翻转核）。`padw` 与核半径解耦，便于加宽边界余量。"""
    out = np.asarray(f, float)
    out = np.moveaxis(out, ax, 0)
    if padw > 0:
        out = np.concatenate([out[-padw:], out, out[:padw]], axis=0)
    out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, out)
    return np.moveaxis(out, 0, ax)


def separable_grad(f, dx, padw=2):
    """返回**未归一化**的三分量矩 `(Mx, My, Mz)`（常数由调用方乘）。"""
    K1 = np.array([-1.0, 0.0, 1.0]) * dx
    def tp(kx, ky, kz):
        return corr1(corr1(corr1(f, kx, 0, padw), ky, 1, padw), kz, 2, padw)
    return tp(K1, K0, K0), tp(K0, K1, K0), tp(K0, K0, K1)


def lsq_ref(f, dx):
    """逐点 27 点 LSQ 平面拟合（参考实现，`pinv`；`_r723` 已验其精度 0.037°）。"""
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


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-300
    return v / n


def main():
    dx = 0.0625e-6
    N = 32
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])

    print('=' * 96)
    print('① 用**线性场**反解归一化常数 c（解析预期 3/27 = %.6f）' % (3 / 27))
    print('=' * 96)
    lin = 3.0 * (X - ctr[0]) + 5.0 * (Y - ctr[1]) - 2.0 * (Z - ctr[2])
    Mx, My, Mz = separable_grad(lin, dx)
    inn = np.s_[2:-2, 2:-2, 2:-2]
    vx, vy, vz = (float(np.median(Mx[inn])), float(np.median(My[inn])),
                  float(np.median(Mz[inn])))
    cc = 3.0 / vx
    print('  内部 Mx 中位 = %.6e  ⇒ c = 3/Mx = %.8f' % (vx, cc))
    gx, gy, gz = cc * Mx[inn], cc * My[inn], cc * Mz[inn]
    print('  反解后：gx err=%.3e  gy err=%.3e  gz err=%.3e  （线性场应精确）'
          % (np.abs(gx - 3).max(), np.abs(gy - 5).max(), np.abs(gz + 2).max()))
    # 一致性：三轴的 vx/vy/vz 比值应为 3:5:−2
    print('  Mx:My:−Mz 的比值 = %.6f : %.6f : %.6f （应 ≈ 3:5:2）'
          % (vx * cc / 3, vy * cc / 5, -vz * cc / 2))

    print()
    print('=' * 96)
    print('② pad 宽度对**边界**的影响（线性场，整盒应处处精确）')
    print('=' * 96)
    for padw in (1, 2, 3, 4):
        Mx2, _, _ = separable_grad(lin, dx, padw=padw)
        e = float(np.abs(cc * Mx2 - 3.0).max())
        print('  padw=%d  整盒 max|gx−3| = %.3e  ⇒ %s'
              % (padw, e, '✅ 无边界特例' if e < 1e-9 else '⚠ 边界仍有差'))

    print()
    print('=' * 96)
    print('③ 球面对照：可分形式 (c 已反解) vs 逐点 LSQ 参考实现')
    print('=' * 96)
    R = 0.30 * N * dx
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    f = rr - R
    nref = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1) / (rr[..., None] + 1e-300)
    Mx2, My2, Mz2 = separable_grad(f, dx)
    u_sep = unit(cc * np.stack([Mx2, My2, Mz2], -1))
    u_ref = unit(lsq_ref(f, dx))
    band = np.abs(f) <= 1.5 * dx
    for nm, u in (('可分形式(反解 c)', u_sep), ('逐点 LSQ 参考', u_ref)):
        ca = np.clip(np.abs(np.einsum('...i,...i->...', u, nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))[band]
        print('  %-18s 球面界面带内 median=%.5f°  p90=%.5f°'
              % (nm, float(np.median(ang)), float(np.percentile(ang, 90))))
    ca = np.clip(np.abs(np.einsum('...i,...i->...', u_sep, u_ref)), 0, 1)
    ang2 = np.degrees(np.arccos(ca))
    print('  两者**互相**夹角 max=%.4f°  median=%.4f°'
          % (float(ang2.max()), float(np.median(ang2))))
    ok = float(np.median(np.degrees(np.arccos(np.clip(
        np.abs(np.einsum('...i,...i->...', u_sep, nref)), 0, 1)))[band])) <= 0.05
    print()
    print('⇒ **判据 J-6（球面 ≤0.05°）：%s**' % ('✅ PASS' if ok else '⛔ FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
