#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_reinit.py --- 复核专家新发现 1：
   "独立重初始化各 phi_k 会移动 phi_k - phi_l = 0 的变体-变体界面"。
   构造：phi1 = z + a, phi2 = -z + b => 真实界面 phi1 = phi2 = 0 平面。
   比较三种处理前后 d = phi1 - phi2 的零等值面位置。
"""
import numpy as np
import windowB_surface as W

N, dx = 48, 5e-8
L = N * dx
z = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(z, z, z, indexing='ij')
a, b = 0.02 * L, 0.03 * L           # phi1 = z + a, phi2 = -z + b  (真实界面在 z=(b-a)/2)

def d_zero_pos(d):
    """差分场 d 的零等值面位置：在域中心列上取 |d| 最小处 + 线性插值。"""
    col = d[d.shape[0] // 2, d.shape[1] // 2, :]
    i = int(np.argmin(np.abs(col)))
    if i == 0 or i >= len(col) - 1:
        return float(z[i])
    v0, v1 = col[i], col[i + 1]
    if v0 == v1:
        return float(z[i])
    return float(z[i] + (0.0 - v0) * dx / (v1 - v0))

def mk():
    g = W.LevelSetMulti(N, L, nv=2, gamma=0.15, Mob=1e-9)
    g.phi[1] = Z + a
    g.phi[2] = -Z + b
    g.phi[0] = -(np.minimum(g.phi[1], g.phi[2]))   # 母相 = 补集
    return g

z_true = (b - a) / 2.0
print('真实界面位置（解析） z = (b-a)/2 = %.5f um' % (z_true * 1e6))
print('%-34s %12s %12s' % ('处理', 'd=0 位置(um)', '相对解析偏差(um)'))

# (0) 不重初始化
g = mk(); p = d_zero_pos(g.phi[1] - g.phi[2])
print('%-34s %12.5f %12.2e' % ('(0) 不重初始化', p * 1e6, abs(p - z_true)))

# (1) 独立重初始化每个 phi_k（当前实现的做法）
g = mk()
for k in range(g.nreg):
    near = np.abs(g.phi[k]) <= 6 * dx
    newp = g.sussman_reinit(g.phi[k], iters=30)
    g.phi[k] = np.where(near, newp, g.phi[k])
p = d_zero_pos(g.phi[1] - g.phi[2])
print('%-34s %12.5f %12.2e' % ('(1) 独立 reinit 各 phi_k(现状)', p * 1e6, abs(p - z_true)))

# (2) 对差分场 d = phi1 - phi2 做重初始化后再回写
g = mk()
d = g.phi[1] - g.phi[2]
near = np.abs(d) <= 6 * dx
dn = g.sussman_reinit(d, iters=30)
d = np.where(near, dn, d)
# 回写：保持 phi1 不动，把界面按新 d 重置（phi2 = phi1 - d）
g.phi[2] = np.where(near, g.phi[1] - d, g.phi[2])
p = d_zero_pos(g.phi[1] - g.phi[2])
print('%-34s %12.5f %12.2e' % ('(2) 对差分场 d 做 reinit', p * 1e6, abs(p - z_true)))

print()
print('判读：若 (1) 的偏差 >> (0), 而 (2) 接近 (0) => 专家新发现 1 成立。')
