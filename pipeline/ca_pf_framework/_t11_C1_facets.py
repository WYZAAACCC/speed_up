#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_C1_facets.py —— **C1 第一步**：从极图**实际求出面法向集**（Wulff 构造做实）。

## 这一步同时验证 `R658 §5` 里我标为【推理】的那条
> 文档判据针对**界面能 `γ(n)`**；本工具算的是 **`Mfac(n)`（生长动力学）**。
> 两者 Wulff 构造**形式同构** —— **该同构性我未从文档核到**。

## 算法（Wulff 构造的"极图凸包 → 取极"实现）
1. 在球面上取 `Mfac(n̂)` 的值（网格化方向）；
2. 取这些点的**凸包** `H = conv{ Mfac(n̂)·n̂ }`；
3. `H` 的**每个顶点** `v` ↔ Wulff 形状的**一个平直刻面**：
   * **面法向** = `v / |v|`
   * **面到原点距离** = `|v|`
   （因为 `H` 的顶点对应 `r(n) = min{h : h·n ≤ γ(n)}` 的活动约束。）

⇒ **输出面法向集**（这就是 C1 要的"面法向集"，可直接喂给多面体表示）。

## 判据（可 FAIL，先登记）
| 量 | 期望 |
|---|---|
| 面法向个数 | **有限**（若极图光滑凸 ⇒ 无穷/退化为球面网格） |
| 主面法向 | 应含 `±a`（长轴，tip 面）与 `±w`（side 面） |
| `±n*` | **可能不含**（因为 `n*` 方向被强烈钉扎 ⇒ 该取向"缺失" ⇒ 被相邻面取代） |
| 面到原点距离之比 | 应与 `Mfac` 的极值同量级 |
"""
import sys

import numpy as np

BETA_H, BETA_W = 6.477, 2.3
AXN = 0.127107


def mfac_batch(nd):
    """`nd` = (M,3) 单位法向 ⇒ Mfac（逐字照 `windowB_surface.py:5240-5255`，pin_min=True）。"""
    nh = np.array([-0.44243, 0.44246, -0.78005])
    nh /= np.linalg.norm(nh)
    aa = np.array([-0.49087, 0.49087, 0.71979])
    aa /= np.linalg.norm(aa)
    ww = np.cross(nh, aa)
    ww /= np.linalg.norm(ww)
    c2b = (nd @ nh) ** 2
    c2w = (nd @ ww) ** 2
    return np.exp(-BETA_H * c2b - BETA_W * c2w), (nh, aa, ww)


def fibonacci_sphere(M):
    i = np.arange(M) + 0.5
    phi = np.arccos(1 - 2 * i / M)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi),
                     np.cos(phi)], axis=1)


def hull_vertices(P, tol=1e-9):
    """凸包顶点（用 scipy 若可用；否则用"极点"近似）。"""
    try:
        from scipy.spatial import ConvexHull
        h = ConvexHull(P)
        return P[np.unique(h.vertices)], h
    except Exception as e:
        print("  ⚠ scipy ConvexHull 不可用（%s）⇒ 退化为『极点+非凸度』判据" % e)
        return None, None


M = 20000
nd = fibonacci_sphere(M)
mval, (nh, aa, ww) = mfac_batch(nd)
print("SHAPES: nd=%s  mval=%s" % (nd.shape, mval.shape))
P = np.empty((M, 3), float)
for _j in range(3):
    P[:, _j] = mval * nd[:, _j]
print("=" * 100)
print("C1 第一步：从 `Mfac` 极图求**面法向集**（Wulff 构造 = 极图凸包 → 取极）")
print("  参数 β_h=%.3f β_w=%.1f；球面采样 M=%d" % (BETA_H, BETA_W, M))
print("=" * 100)
print("  轴：n* = [%+.5f %+.5f %+.5f]" % tuple(nh))
print("      a  = [%+.5f %+.5f %+.5f]" % tuple(aa))
print("      w  = [%+.5f %+.5f %+.5f]" % tuple(ww))
print("  Mfac：a=%.6g  w=%.6g  n*=%.6g" % (mfac_batch(aa[None])[0][0],
                                            mfac_batch(ww[None])[0][0],
                                            mfac_batch(nh[None])[0][0]))
V, h = hull_vertices(P)
if V is None:
    sys.exit(1)
print("\n  ⇒ 凸包：顶点 %d 个，面 %d 个" % (len(V), len(h.simplices)))
# 面法向 = 顶点方向，面距 = 顶点模
r = np.linalg.norm(V, axis=1)
dirs = V / r[:, None]
print("\n  ⇒ **面法向集（Wulff 刻面）**：%d 个" % len(dirs))
# 把法向按与三个轴的 |cos| 分组
print()
print("  %-4s %-10s %-9s %-9s %-9s %s"
      % ('#', '距原点', '|·n*|', '|·a|', '|·w|', '归类'))
rows = []
for i, (d, ri) in enumerate(zip(dirs, r)):
    c = (abs(d @ nh), abs(d @ aa), abs(d @ ww))
    lab = []
    if c[0] > 0.99:
        lab.append('±n*')
    if c[1] > 0.99:
        lab.append('±a')
    if c[2] > 0.99:
        lab.append('±w')
    if not lab:
        mx = int(np.argmax(c))
        lab.append('斜（近 %s, cos=%.3f）' % ('n*aw'[mx], c[mx]))
    rows.append((ri, c, '/'.join(lab)))
rows.sort(key=lambda t: -t[0])
for i, (ri, c, lab) in enumerate(rows[:40]):
    print("  %-4d %-10.5f %-9.4f %-9.4f %-9.4f %s" % (i, ri, c[0], c[1], c[2], lab))
print()
print("  ⇒ 判读：")
print("     · 若含 `±a` ⇒ **tip 面是 Wulff 刻面**（长轴方向有平直面）")
print("     · 若含 `±w` ⇒ **side 面是 Wulff 刻面**")
print("     · 若**不含** `±n*` ⇒ 该取向**缺失** ⇒ 由相邻面取代（这正是『刻面』的成因）")
