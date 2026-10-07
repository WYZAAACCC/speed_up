#!/usr/bin/env python3
"""R59: **3D 版 Wulff 凸化** —— 核对 2D 切片（`_r58_wulff.py` 给 8.98）是否够用。

## 为什么必须先算这个
`_r58_wulff.py` 的 `v**` 是在 **a–w 平面**上做的 2D 凸包。
但真实法向是**球面**上的，3D 凸包会**额外填掉平面外方向造成的凹陷**
⇒ `h(a)/h(w)` **可能不同**。**实现前必须核对**（否则按 2D 数实现出来会不对）。

## 球面上的 `M(n)`
`M(n)/M0 = exp(−β_h(n·n*)² − β_w(n·w)² − c·sin²(2θ))`
其中 `θ` = 法向在**惯习面内**的投影与 `a` 的夹角：
`u = (n − (n·n*)n*)/|…|`，`cosθ = u·a`，`sinθ = u·w`，`sin2θ = 2 cosθ sinθ`。
（`c=0` 时退回现形式。）
"""
import numpy as np

B_H, B_W, A_DOT_N = 6.477, 2.3, -0.127


def axes():
    n = np.array([-0.4424, 0.4425, -0.7801]); n /= np.linalg.norm(n)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(n, a); w /= np.linalg.norm(w)
    return n, a, w


def fib_sphere(m):
    """球面准均匀采样（Fibonacci）。"""
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def mrel(N, a, w, nh, c):
    n_dot_n = N @ nh
    n_dot_w = N @ w
    n_dot_a = N @ a
    base = np.exp(-B_H * n_dot_n ** 2 - B_W * n_dot_w ** 2)
    if c <= 0:
        return base
    # 面内投影方向与 a 的夹角
    par = N - n_dot_n[:, None] * nh[None, :]
    pn = np.linalg.norm(par, axis=-1)
    ok = pn > 1e-9
    u = np.zeros_like(par)
    u[ok] = par[ok] / pn[ok, None]
    ca = np.clip(u @ a, -1, 1)
    sw = np.clip(u @ w, -1, 1)
    s2 = 2.0 * ca * sw                       # sin(2θ)
    dip = np.where(ok, np.exp(-c * s2 ** 2), 1.0)
    return base * dip


def support(P, directions):
    """极集 `P`（点集）在给定方向上的支撑函数。

    ⚠ 不需要 `ConvexHull`：凸包的支撑函数 = **点集本身**在这些方向上的 max
    （`max_{x∈hull(P)} x·d = max_{x∈P} x·d`）。
    第一版用 `scipy.spatial.ConvexHull`，在**平面点集**（2D 切片）上直接报
    `QH6154 Initial simplex is flat` —— 换成 max 后又快又稳。
    """
    return (P @ directions.T).max(0), P.shape[0]


def main():
    nh, a, w = axes()
    N = fib_sphere(20000)
    print('球面采样 %d 点；β_h=%.3f β_w=%.1f a·n*=%.3f' % (len(N), B_H, B_W, a @ nh))
    print()
    print('  %-6s %-14s %-14s %-12s %-12s %s'
          % ('c', 'h(a)', 'h(w)', '2D 切片比', '**3D 比**', '与 2D 一致?'))
    # 2D 切片对照（a-w 平面内）
    th = np.linspace(0, 2 * np.pi, 7201)
    for c in (0.0, 1.0, 2.0, 4.0, 8.0):
        v = mrel(N, a, w, nh, c)
        P = v[:, None] * N
        d = np.stack([a, w, nh], 0)
        h, nv = support(P, d)
        # 2D 切片：只在 a-w 平面内的法向
        u2 = np.stack([np.cos(th), np.sin(th)], -1)
        N2 = u2[:, 0:1] * a + u2[:, 1:2] * w
        v2 = mrel(N2, a, w, nh, c)
        P2 = v2[:, None] * N2
        h2, _ = support(P2, d)
        r2d = h2[0] / h2[1] if h2[1] else float('inf')
        r3d = h[0] / h[1] if h[1] else float('inf')
        print('  %-6.1f %-14.5f %-14.5f %-12.2f %-12.2f %s'
              % (c, h[0], h[1], r2d, r3d,
                 '✅' if abs(r3d - r2d) < 0.05 * max(r2d, 1) else '⚠ 不同'))
    print()
    print('★ 判读：若 **3D 比** 也随 `c` 升到 ≳9，则 2D 设计可用；')
    print('  若 3D 比显著**低于** 2D 比，则必须按 3D 重定 `c`。')


if __name__ == '__main__':
    main()
