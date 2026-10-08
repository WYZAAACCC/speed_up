#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r729_dbg.py —— 查 `moments()` 里 `Mx` 为何 ≈0（与直接构造的参考逐点比）。

线性场是**唯一能让"一阶矩应恒定"可见**的量具（线性场下一阶矩处处相同）。
"""
import numpy as np

N = 8
dx = 1.0
c = np.arange(N, dtype=float) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
f = 3.0 * X          # 只依赖 x ⇒ Σ r_x f 应恒为 3·dx·(9) = 27
K0 = np.ones(3)
K1 = np.array([-1.0, 0.0, 1.0]) * dx


def corr1(a, k, ax):
    a = np.moveaxis(a, ax, 0)
    p = np.concatenate([a[-1:], a, a[:1]], axis=0)
    out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
    return np.moveaxis(out, 0, ax)


print('--- 单轴 corr1 测试（沿 ax=0）---')
a0 = corr1(f, K0, 0)
b0 = corr1(f, K1, 0)
print('K0: 期望 f[i-1]+f[i]+f[i+1] = 3x[i] = %s' % (3 * c))
print('    实测 %s' % np.round(a0[:, 0, 0], 6))
print('K1: 期望 3*(x[i+1]-x[i-1]) = 6dx = 6.0 处: %s' % (6.0,))
print('    实测 %s' % np.round(b0[:, 0, 0], 6))

print()
print('--- 张量积 (K1,K0,K0) ---')
g = corr1(corr1(corr1(f, K1, 0), K0, 1), K0, 2)
print('  期望恒 = 6*3*3 = 54.0（K0 在 y,z 各乘 3）')
print('  实测 %s' % np.round(g[:, 0, 0], 6))
print('  唯一值 %s' % np.unique(np.round(g, 6)))

print()
print('--- 与**直接构造**的参考比（暴力 27 点）---')
ref = np.zeros_like(f)
fp = np.pad(f, 1, mode='wrap')
for i in (-1, 0, 1):
    for j in (-1, 0, 1):
        for k in (-1, 0, 1):
            ref += (i * dx) * fp[1 + i:1 + i + N, 1 + j:1 + j + N, 1 + k:1 + k + N]
print('  直接构造 ref[1,0,0] = %.6f（应 27.0）' % ref[1, 0, 0])
print('  ref 唯一值 %s' % np.unique(np.round(ref, 6)))
print('  corr1 版 与 ref 的差 max = %.6e' % np.abs(g - ref).max())
print()
print('  ⇒ 若 corr1 版 = 54 而 ref = 27 ⇒ **常数差 2 倍**（我 `_r727` 踩过的那个）')
