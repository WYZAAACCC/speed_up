#!/usr/bin/env python3
"""
T_cap 在生产网格（dx = 1 µm）上会不会也改变熔池几何？

背景（见 `why_cap_changes_liquid.py`）：在 24×12 的**粗**网格上，
cap 在节点上做 `min`，MOOSE 再对节点值做双线性插值 —— 而 `min` 是**凹**的，
「先截断再插值」≤「先插值再截断」，所以 cap 会移动**插值场自己**的 1903 K 等值线。
实测：liquid_frac 0.081597 → 0.079861（−2.1%）。我原先断言的「几何不变」是错的。

但那条结论是在 dx = 17.9 µm 上得到的。**生产网格 dx = 1 µm**，
如果 T > T_cap 的区域**完全落在** T > 1903 的区域内部足够深，
那么跨在熔池边界上的单元里**没有任何节点被截断**，cap 就不影响几何。

本脚本量出这两个等值线的实际间距，判断生产网格上 cap 是否安全。
"""

import math

XMIN, XMAX = -2.8e-4, 1.5e-4
YMIN, YMAX = 0.0, 1.5e-4


def T(x, y, t=0.0):
    xi = x + 1.2e-4 - 0.6 * t
    R = math.sqrt(xi * xi + y * y + 1e-10)
    return 353.0 + 28.0 / (2 * math.pi * 20.0 * R) * \
        math.exp(-0.6 * (R + xi) / (2 * 6e-6))


def node_grid(nx, ny):
    dx = (XMAX - XMIN) / nx
    dy = (YMAX - YMIN) / ny
    pts = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            pts.append((XMIN + i * dx, YMIN + j * dy))
    return pts, dx, dy


def analyse(nx, ny, cap):
    """返回 (被截断的节点数, 跨越 1903 的单元里含被截断节点的个数)。"""
    pts, dx, dy = node_grid(nx, ny)
    capped = set()
    for (x, y) in pts:
        if T(x, y) > cap:
            capped.add((round(x, 12), round(y, 12)))
    # 逐个单元看：4 个角点是否同时存在 >1903 与 <1903（即跨熔池边界）
    straddle_with_cap = 0
    n_solid = 0
    for i in range(nx):
        for j in range(ny):
            x0, y0 = XMIN + i * dx, YMIN + j * dy
            vals, has_cap = [], False
            for a in (0, 1):
                for b in (0, 1):
                    p = (round(x0 + a * dx, 12), round(y0 + b * dy, 12))
                    vals.append(T(*p))
                    if p in capped:
                        has_cap = True
            if has_cap:
                n_solid += 1
            if min(vals) < 1903 < max(vals) and has_cap:
                straddle_with_cap += 1
    return len(capped), n_solid, straddle_with_cap, dx * 1e6


if __name__ == "__main__":
    print("问题：跨在熔池边界（T=1903）上的单元里，有没有被 cap 截断的节点？")
    print("      有 ⇒ cap 会改变几何；没有 ⇒ cap 对几何中性。")
    print()
    print(f"{'网格':>14} {'dx (µm)':>9} {'被截断节点':>11} {'含截断节点的单元':>17} "
          f"{'跨边界且含截断':>15}")
    print("-" * 72)
    for nx, ny in [(24, 12), (86, 30), (215, 75), (430, 150), (860, 300)]:
        ncap, nsolid, straddle, dxu = analyse(nx, ny, 3200)
        print(f"{nx}x{ny:<9} {dxu:>9.3f} {ncap:>11} {nsolid:>17} {straddle:>15}"
              + ("   <- cap 影响几何" if straddle else "   OK 中性"))
