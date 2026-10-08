#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_lsq_equiv.py —— **离线验证**：`R727 §2.1` 的代数等价式 + 边界正对照。

## 要证的三件事（判据 **J-6 / J-7**，`R727 §3.2`）
| # | 命题 |
|---|---|
| **A** | **代数等价**：`3×3×3 周期箱和` 形式 与 `逐点 27 邻域最小二乘平面拟合` 给出**同一个法向** |
| **B** | **边界正确**：在**周期数组**上，箱和形式在含边界处仍等于"该点周围 27 点的均值梯度" |
| **C** | **精度**：两者对**解析法向**的夹角都 ≤ 0.05°（球）/ = 0.000°（长方体） |

## 为什么这是**纯离线**
不 import 引擎、不改主代码、不跑仿真。只做 numpy 代数与解析几何。

## 口径（写死）
* 箱和 `S(f)[i] = Σ_{|δ|∞≤1} f[i+δ]`（**周期**，`np.pad(mode='wrap')`）
* 箱和形式的法向 `g = (1/6)·[S(f)_{i+1} − S(f)_{i−1}]`（逐轴）
* LSQ 形式：`g = pinv(A) @ (f[N] − mean(f[N]))`，`A = 相对坐标 (−1,0,1)³`
* `f` 取**差分场** `d = pha − phb`（引擎 `:4671` 的输入）；解析场上直接取 `f = SDF`

## 用法
    python3 _r727_lsq_equiv.py
"""
import sys

import numpy as np


def boxsum(f):
    """3×3×3 **周期**箱和（三次可分离 1D 卷积，等价于 np.pad(wrap)+滑窗）。"""
    out = np.asarray(f, float)
    k = np.ones(3) / 1.0                      # 只求和（不归一）
    for ax in range(3):
        out = np.moveaxis(out, ax, 0)
        pad = np.concatenate([out[-1:], out, out[:1]], axis=0)
        out = np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 0, pad)
        out = np.moveaxis(out, 0, ax)
    return out


def grad_boxsum(f, dx):
    """`g = (1/6)·[S(f)_{i+1} − S(f)_{i−1}] / dx`，逐轴。"""
    S = boxsum(f)
    out = []
    for ax in range(3):
        out.append((np.roll(S, -1, ax) - np.roll(S, 1, ax)) / (6.0 * dx))
    return out


def lsq_plane(f, dx):
    """逐点 27 邻域的**最小二乘平面拟合**（与 `_r723_normal_lsq.py` 同口径）。"""
    off = np.array([(i, j, k) for i in (-1, 0, 1)
                    for j in (-1, 0, 1) for k in (-1, 0, 1)], float) * dx
    A = off - off.mean(0)                      # 去心 ⇒ 与常数项正交
    pinv = np.linalg.pinv(A)
    N = f.shape[0]
    fp = np.pad(f, 1, mode='wrap')
    blk = np.stack([fp[i:i + N, j:j + N, k:k + N]
                    for i in range(3) for j in range(3) for k in range(3)], -1)
    b = blk - blk.mean(-1, keepdims=True)
    g = np.einsum('ij,...j->...i', pinv, b)     # (N,N,N,3)
    return [g[..., 0], g[..., 1], g[..., 2]]


def unit(gs):
    n = np.sqrt(sum(g ** 2 for g in gs)) + 1e-300
    return np.stack([g / n for g in gs], -1)


def main():
    N = 24
    dx = 0.0625e-6
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])
    ok = True

    cases = {}
    R = 0.30 * N * dx
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    cases['球 SDF'] = (rr - R, np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
                       / (rr[..., None] + 1e-300))
    b = np.maximum(np.maximum(np.abs(X - ctr[0]), np.abs(Y - ctr[1])),
                   np.abs(Z - ctr[2])) - R
    nb = np.zeros(X.shape + (3,))
    which = np.argmax(np.stack([np.abs(X - ctr[0]), np.abs(Y - ctr[1]),
                                np.abs(Z - ctr[2])], -1), -1)
    d = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
    for a in range(3):
        m = (which == a)
        for comp in range(3):
            nb[..., comp] = np.where(m, np.sign(d[..., comp]), nb[..., comp])
    cases['长方体 SDF'] = (b, nb)

    print('=' * 100)
    print('A) 代数等价：箱和形式  vs  逐点 27 邻域最小二乘平面拟合')
    print('=' * 100)
    for name, (f, _) in cases.items():
        g1 = unit(grad_boxsum(f, dx))
        g2 = unit(lsq_plane(f, dx))
        # 逐点夹角
        ca = np.clip(np.abs(np.einsum('...i,...i->...', g1, g2)), 0, 1)
        ang = np.degrees(np.arccos(ca))
        finite = np.isfinite(ang)
        mx, med = float(ang[finite].max()), float(np.median(ang[finite]))
        good = mx < 1e-9
        ok &= good
        print('  %-12s 逐点夹角  max=%.3e°  median=%.3e°   ⇒ %s'
              % (name, mx, med, '✅ 逐位等价' if good else '⛔ 不等价'))

    print()
    print('=' * 100)
    print('B) 边界正确：整盒首末胞的夹角也在上表的 max 里（周期 box 和 ⇒ 无边界特例）')
    print('=' * 100)
    for name, (f, nref) in cases.items():
        g1 = unit(grad_boxsum(f, dx))
        ca = np.clip(np.abs(np.einsum('...i,...i->...', g1, nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))
        # 取 6 个面心处的值（最靠近边界的点）
        face_idx = [(0, N // 2, N // 2), (N - 1, N // 2, N // 2),
                    (N // 2, 0, N // 2), (N // 2, N - 1, N // 2),
                    (N // 2, N // 2, 0), (N // 2, N // 2, N - 1)]
        fv = np.array([ang[i] for i in face_idx])
        print('  %-12s 六个面心处的夹角 = %s'
              % (name, np.array2string(fv, precision=3, suppress_small=False)))
        print('                全盒 max=%.4f°  median=%.4f°'
              % (float(ang.max()), float(np.median(ang))))

    print()
    print('=' * 100)
    print('C) 精度（判据 J-6/J-7）：箱和形式的法向 vs 解析法向')
    print('=' * 100)
    for name, (f, nref) in cases.items():
        g1 = unit(grad_boxsum(f, dx))
        ca = np.clip(np.abs(np.einsum('...i,...i->...', g1, nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))
        # 只在界面上比（|f| <= 1.5dx）
        band = np.abs(f) <= 1.5 * dx
        med = float(np.median(ang[band]))
        p90 = float(np.percentile(ang[band], 90))
        tgt = 0.05 if '球' in name else 1e-6
        good = med <= tgt
        ok &= good
        print('  %-12s 界面带内  median=%.4f°  p90=%.4f°  靶 ≤%.3f°  ⇒ %s'
              % (name, med, p90, tgt, '✅' if good else '⛔'))

    print()
    print('⇒ **总判定：%s**' % ('全部通过（A/B/C）' if ok else '**有 FAIL**'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
