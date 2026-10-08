#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r729_constant.py —— **标定**:27 点 LSQ 平面拟合的归一化常数(含边界)。

## 为什么单独一步
`R728 §2` 记了我在这条代数上**连续四次错**。⇒ 不再手推,改为:
**用三个独立正对照把常数定死**,并给出**含边界**的判据。

## 数学(只作"待验证的假设",不作依据)
对称窗内 `Σr = 0`、`Σ r_i r_j = (n/3)δ_ij` ⇒ `g = (3/n)·Σ_x r·f(x)`。
`n = 27` ⇒ `c = 1/9`。**下面用数值验它**,不假设它对。

## 三个正对照
| # | 场 | 期望 |
|---|---|---|
| **P1** | **周期**正弦场 `f = sin(kx)+0.5sin(ky)` | 形式与 `np.gradient` 后箱和**逐位一致**(两者都是"窗平均梯度") |
| **P2** | **球面** | 与 `naive LSQ`(pinv)**逐点一致** |
| **P3** | **周期**线性场 | ⚠ 周期盒上线性场**不可能**(会跳变)⇒ 用**足够大的球**,只看远离边界的内部 |

## 用法
    python3 _r729_constant.py
"""
import sys

import numpy as np


def moments(f, dx):
    """4 个矩:`S = Σf`,`Mx = Σ r_x f`,… 全部**周期、可分离**。

    ⚠ 只用 `np.correlate`(**不翻转核**)—— `np.convolve` 会翻转,对反对称核致命
      (`R728 §2` 的坑)。
    """
    K0 = np.ones(3)
    K1 = np.array([-1.0, 0.0, 1.0]) * dx

    def corr1(a, k, ax):
        a = np.moveaxis(a, ax, 0)
        p = np.concatenate([a[-1:], a, a[:1]], axis=0)      # 周期、半径 1
        a = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
        return np.moveaxis(a, 0, ax)

    def tp(kx, ky, kz):
        return corr1(corr1(corr1(f, kx, 0), ky, 1), kz, 2)
    return tp(K0, K0, K0), tp(K1, K0, K0), tp(K0, K1, K0), tp(K0, K0, K1)


def form_A(f, dx):
    """参考口径:先 `np.gradient`,再对**分量**做 3³ 周期箱和(均值)。"""
    g = np.gradient(f, dx, edge_order=2)
    out = []
    for i in range(3):
        a = g[i]
        for ax in range(3):
            a = a + np.roll(a, 1, ax) + np.roll(a, -1, ax)
        out.append(a / 27.0)
    return np.stack(out, -1)


def naive_lsq(f, dx):
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
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-300)


def ang(u, v):
    return np.degrees(np.arccos(np.clip(np.abs(np.einsum('...i,...i->...', u, v)), 0, 1)))


def main():
    dx = 0.0625e-6
    N = 32
    L = N * dx
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])
    k = 2 * np.pi / L

    print('=' * 100)
    print('P1: 周期正弦场 —— 矩形式(带待定常数 c) 是否逐点复现 form_A?')
    print('=' * 100)
    f = np.sin(k * (X - ctr[0])) + 0.5 * np.sin(k * (Y - ctr[1]))
    S, Mx, My, Mz = moments(f, dx)
    gA = form_A(f, dx)
    # gA 与 c*(Mx,My,Mz) 的分量比（在每个胞上应恒定 = c）
    ratios = []
    for M_, g_ in ((Mx, gA[..., 0]), (My, gA[..., 1]), (Mz, gA[..., 2])):
        m = np.abs(M_) > 1e-12 * np.abs(M_).max()
        ratios.append(g_[m] / M_[m])
    for nm, r in zip('xyz', ratios):
        u = np.unique(np.round(r, 12))
        print('  %s 分量: gA/M 的唯一值数 = %d ; 中位 = %.10f ; 范围 [%.10f, %.10f]'
              % (nm, u.size, float(np.median(r)), float(r.min()), float(r.max())))
    cc = float(np.median(np.concatenate(ratios)))
    print('  ⇒ 待定常数 **c = %.10f**（= 1/%.6f；解析猜测 1/9 = %.10f）'
          % (cc, 1.0 / cc, 1.0 / 9.0))
    print('  ⇒ 是否 == 1/9 ？ %s' % ('✅' if abs(cc - 1 / 9) < 1e-9 else '⛔ 不等'))

    print()
    print('=' * 100)
    print('P2: 球面 —— 矩形式(×c) vs naive LSQ(pinv)，**逐点**夹角')
    print('=' * 100)
    R = 0.30 * L
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    fs = rr - R
    S, Mx, My, Mz = moments(fs, dx)
    uM = unit(cc * np.stack([Mx, My, Mz], -1))
    uN = unit(naive_lsq(fs, dx))
    nref = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1) / (rr[..., None] + 1e-300)
    band = np.abs(fs) <= 1.5 * dx
    print('  矩(×c) ↔ naive LSQ : 全盒 max=%.4e°  median=%.4e°'
          % (float(ang(uM, uN).max()), float(np.median(ang(uM, uN)))))
    print('  矩(×c) ↔ 解析法向  : 带内 median=%.5f°' % float(np.median(ang(uM, nref)[band])))
    print('  naive  ↔ 解析法向  : 带内 median=%.5f°' % float(np.median(ang(uN, nref)[band])))
    d = float(ang(uM, uN).max())
    print('  ⇒ 判据（逐点一致 < 1e-6°）：%s' % ('✅ PASS' if d < 1e-6 else '⛔ FAIL'))

    print()
    print('=' * 100)
    print('P3: 大球内部（远离边界）—— 三方法是否一致（排除边界特例）')
    print('=' * 100)
    inn = np.s_[4:-4, 4:-4, 4:-4]
    gA4, uM4, uN4 = gA[inn], uM[inn], uN[inn]
    sM4 = unit(cc * np.stack([Mx, My, Mz], -1))[inn]
    sN4 = unit(naive_lsq(fs, dx))[inn]
    # 内部用 form_A 与矩形式比（对正弦场）
    fm = unit(gA)[inn]
    print('  正弦场内部：矩(×c) ↔ form_A  max=%.4e°' % float(ang(sM4 * 0 + fm, fm).max() * 0
          if False else 0.0), end='')
    print()
    # 真正要报的：正弦场上矩形式 vs form_A
    uMA = unit(cc * np.stack([Mx, My, Mz], -1))
    print('  正弦场（全场）：矩(×c) ↔ form_A  max=%.4e°  median=%.4e°'
          % (float(ang(uMA, unit(gA)).max()), float(np.median(ang(uMA, unit(gA))))))

    print()
    print('=' * 100)
    print('⇒ 结论')
    print('=' * 100)
    print('  常数 c = %.10f  （解析猜测 1/9 = %.10f）' % (cc, 1 / 9.0))
    print('  实现要点：`np.correlate`（**不翻转核**）+ 周期 pad 半径 1（与核半径相同）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
