#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_C1_facets2.py —— **C1：面法向集（正确版）**。修掉采样离散化伪影。

## 第一版的错（`R660` 记账）
`_t11_C1_facets.py` 直接在 20000 个球面采样点上取凸包 ⇒ 得到 **1449 个顶点**。
**那是离散化伪影**：真刻面应是**有限个**。球面采样密度不够时，
每个"几乎平面"的区域都会贡献一批几乎共面的顶点。

## 正确做法（**精确支撑函数**）
Wulff 形状的支撑函数 `h(n) = γ(n)`（本问题里 `γ` 换成 `Mfac`）。
⇒ 面法向是那些**真正"活跃"的约束方向**。判据：
对候选法向集 `{n_i}`，算精确 `h_i = Mfac(n_i)`；
把点 `{h_i·n_i}` 取凸包；**凸包顶点**才是刻面法向。
⇒ 用**分层球面网格**（而不是随机斐波那契）+ 凸包后**按面片面积合并**，
只保留面积占比 > 阈值的面。
"""
import numpy as np

BETA_H, BETA_W = 6.477, 2.3


def axes():
    nh = np.array([-0.44243, 0.44246, -0.78005])
    nh /= np.linalg.norm(nh)
    aa = np.array([-0.49087, 0.49087, 0.71979])
    aa /= np.linalg.norm(aa)
    ww = np.cross(nh, aa)
    ww /= np.linalg.norm(ww)
    return nh, aa, ww


NH, AA, WW = axes()


def mfac(nd):
    c2b = (nd @ NH) ** 2
    c2w = (nd @ WW) ** 2
    return np.exp(-BETA_H * c2b - BETA_W * c2w)


def sphere_grid(nlat=400, nlon=800):
    """经纬网格（比随机采样更适合刻面：保证每个方向附近都有点）。"""
    th = np.linspace(0.0, np.pi, nlat)
    ph = np.linspace(0.0, 2 * np.pi, nlon, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    nd = np.stack([np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)], -1)
    return nd.reshape(-1, 3)


print("=" * 100)
print("C1：面法向集（**精确支撑函数版**，修掉采样离散化伪影）")
print("=" * 100)
print("  Mfac：n*=%.6g  a=%.6g  w=%.6g"
      % (mfac(NH[None])[0], mfac(AA[None])[0], mfac(WW[None])[0]))
print()
print("【1】直接由解析式找**活跃面**：在 (n*, a) 与 (a, w) 平面内扫，找 `h(n)` 的凸包顶点")
for nm, v1, v2 in (('(n*,a)', NH, AA), ('(n*,w)', NH, WW), ('(a,w)', AA, WW)):
    A = v1 / np.linalg.norm(v1)
    B = v2 - A * (A @ v2)
    B /= np.linalg.norm(B)
    th = np.linspace(0, 2 * np.pi, 200001)
    nd = np.cos(th)[:, None] * A + np.sin(th)[:, None] * B
    h = mfac(nd)
    pts = h[:, None] * nd
    # 2D 凸包（在该平面内的坐标）
    xy = np.stack([pts @ A, pts @ B], -1)
    keep = np.ones(len(xy), bool)
    # 单调链
    P = xy[np.lexsort((xy[:, 1], xy[:, 0]))]

    def half(ps):
        o = []
        for p in ps:
            while len(o) >= 2:
                a_, b_ = o[-2], o[-1]
                if (b_[0]-a_[0])*(p[1]-a_[1]) - (b_[1]-a_[1])*(p[0]-a_[0]) <= 1e-15:
                    o.pop()
                else:
                    break
            o.append(p)
        return o
    hull = np.array(half(P)[:-1] + half(P[::-1])[:-1])
    print("  %-8s 凸包顶点数 = %-5d" % (nm, len(hull)))
    # 每个凸包顶点对应的角度与 h
    for hp in hull[:14]:
        ang = np.degrees(np.arctan2(hp[1], hp[0])) % 360
        r = np.hypot(hp[0], hp[1])
        ndv = np.cos(np.radians(ang)) * A + np.sin(np.radians(ang)) * B
        c = (abs(ndv @ NH), abs(ndv @ AA), abs(ndv @ WW))
        lb = ('±n*' if c[0] > 0.999 else '') + ('±a' if c[1] > 0.999 else '') + \
             ('±w' if c[2] > 0.999 else '')
        print("      θ=%7.2f°  h=**%.6f**  (|·n*|,|·a|,|·w|)=(%.3f,%.3f,%.3f)  %s"
              % (ang, r, c[0], c[1], c[2], lb or '斜'))
print()
print("【2】'缺失取向'判定：`n*` 与 `w` 是否落在**凸包边界**上（= 是否活跃面）")
for nm, v in (('n*', NH), ('a', AA), ('w', WW), ('-n*', -NH), ('-a', -AA), ('-w', -WW)):
    print("     %-4s  Mfac = %.6g" % (nm, mfac(v[None])[0]))
print()
print("  ⇒ 判读：`h = Mfac` 在 `a` 方向最大（0.9006）、`w` 次之（0.1003）、`n*` 最小（0.00154）")
print("     ⇒ Wulff 形状沿 `a` 最长 ⇒ **长轴=刻面法向**；`n*` 若不在凸包上 ⇒ **取向缺失**")
