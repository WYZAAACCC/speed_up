#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_dbg4.py —— 用**线性场**反解：(a) 正确的归一化常数；(b) 正确的 pad 宽度。

线性场上一切应精确 ⇒ 它是唯一能同时定这两件的量具。
"""
import numpy as np

N = 8
dx = 1.0
c = np.arange(N, dtype=float) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
f = 3.0 * X + 5.0 * Y - 2.0 * Z          # 梯度 (3,5,-2)
K0 = np.array([1.0, 1.0, 1.0])
K1 = np.array([-1.0, 0.0, 1.0]) * dx


def corr1(f, k, ax, padw):
    out = np.asarray(f, float)
    out = np.moveaxis(out, ax, 0)
    p = np.concatenate([out[-padw:], out, out[:padw]], axis=0)
    out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
    return np.moveaxis(out, 0, ax)


def tp(f, kx, ky, kz, padw):
    return corr1(corr1(corr1(f, kx, 0, padw), ky, 1, padw), kz, 2, padw)


print('=' * 96)
print('(b) pad 宽度扫描（线性场 f = 3x+5y−2z，Mx 应恒为 3·dx·9 = 27）')
print('=' * 96)
for padw in (1, 2, 3):
    Mx = tp(f, K1, K0, K0, padw)
    S = tp(f, K0, K0, K0, padw)
    uniq = np.unique(np.round(Mx, 9))
    print('  padw=%d  Mx 唯一值 = %s   S 唯一比值(range/8) = %.4f'
          % (padw, np.array2string(uniq, precision=3),
             (S.max() - S.min()) / 8))
    # 内部（挖掉 padw 层）
    inner = Mx[padw:-padw, padw:-padw, padw:-padw]
    print('         内部 Mx 唯一值 = %s' % np.array2string(
        np.unique(np.round(inner, 9)), precision=3))

print()
print('=' * 96)
print('(a) 用 padw=1 的**内部**值反解归一化常数')
print('=' * 96)
for padw in (1, 2):
    Mx = tp(f, K1, K0, K0, padw)
    inner = Mx[padw:-padw, padw:-padw, padw:-padw]
    v = float(np.unique(np.round(inner, 9))[0]) if np.unique(
        np.round(inner, 9)).size == 1 else float(np.median(inner))
    c_true = 3.0 / v
    print('  padw=%d  内部 Mx = %.4f  ⇒ 归一化常数 c = 3/Mx = %.6f  (3/27=%.6f)'
          % (padw, v, c_true, 3.0 / 27.0))

print()
print('=' * 96)
print('(c) 用反解出的 (padw, c) 验：内部是否**逐点**精确 = (3,5,−2)')
print('=' * 96)
for padw in (1, 2):
    Mx = tp(f, K1, K0, K0, padw)
    My = tp(f, K0, K1, K0, padw)
    Mz = tp(f, K0, K0, K1, padw)
    inner = np.s_[padw:-padw, padw:-padw, padw:-padw]
    v = float(np.median(Mx[inner]))
    cc = 3.0 / v
    gx, gy, gz = cc * Mx[inner], cc * My[inner], cc * Mz[inner]
    print('  padw=%d  c=%.6f  ⇒ gx err=%.3e  gy err=%.3e  gz err=%.3e'
          % (padw, cc,
             np.abs(gx - 3.0).max(), np.abs(gy - 5.0).max(), np.abs(gz + 2.0).max()))
