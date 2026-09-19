#!/usr/bin/env python3
"""
为什么 cap 会改变 liquid_flag？—— 把机制算清楚。

实测（`repro_liquid_flag.py` 生成的最小算例，24×12 网格，t=0）：

    raw       T_max=12901.76   liquid_frac=0.081597222   (94/1152 个 qp)
    off       T_max=12901.76   liquid_frac=0.081597222   (与 raw 逐位相同)
    cap3200   T_max=3200       liquid_frac=0.079861111   (92/1152)
    cap3500   T_max=3500       liquid_frac=0.079861111   (与 cap3200 相同)
    cap2000   T_max=2000       liquid_frac=0.069444444
    cap1930   T_max=1930       liquid_frac=0.063368055

`liquid_flag` 是 CONSTANT MONOMIAL，值是**该单元 4 个 qp 里 T>1903 的比例**，
所以 94 与 92 都是「有多少个 qp 判为液态」。

疑点：cap = 3200 和 3500 给出**同一个**结果，却都不同于不截断。
如果机制是「某个 qp 的 T 掉到 1903 以下」，那么 cap 越高应该越接近不截断。
⇒ 说明机制不是「节点值被压低」，而是**插值本身**。

本脚本逐单元算双线性插值，验证这个猜测。
"""

import math

NX, NY = 24, 12
XMIN, XMAX = -2.8e-4, 1.5e-4
YMIN, YMAX = 0.0, 1.5e-4
G = 1.0 / math.sqrt(3.0)      # 2x2 Gauss 点的参考坐标
T_LIQ = 1903.0


def T_node(x, y, t=0.0):
    xi = x + 1.2e-4 - 0.6 * t
    R = math.sqrt(xi * xi + y * y + 1e-10)
    return 353.0 + 28.0 / (2 * math.pi * 20.0 * R) * \
        math.exp(-0.6 * (R + xi) / (2 * 6e-6))


def count_qp_above(cap=None):
    dx = (XMAX - XMIN) / NX
    dy = (YMAX - YMIN) / NY
    n = 0
    per_elem = []
    for i in range(NX):
        for j in range(NY):
            x0, y0 = XMIN + i * dx, YMIN + j * dy
            # 4 个角点的节点值
            corners = {}
            for a in (0, 1):
                for b in (0, 1):
                    v = T_node(x0 + a * dx, y0 + b * dy)
                    if cap is not None:
                        v = min(v, cap)
                    corners[(a, b)] = v
            k = 0
            for gu in (-G, G):
                for gv in (-G, G):
                    # 双线性插值到参考坐标 (gu, gv)
                    s, r = (gu + 1) / 2, (gv + 1) / 2
                    v = (corners[(0, 0)] * (1 - s) * (1 - r)
                         + corners[(1, 0)] * s * (1 - r)
                         + corners[(0, 1)] * (1 - s) * r
                         + corners[(1, 1)] * s * r)
                    if v > T_LIQ:
                        k += 1
            per_elem.append(k)
            n += k
    return n, per_elem


if __name__ == "__main__":
    print("逐单元双线性插值，数 4 个 Gauss 点里 T > 1903 的个数")
    print()
    print(f"{'cap':>10} {'qp 数':>8} {'liquid_frac':>16}   （实测值）")
    print("-" * 62)
    actual = {None: ("0.081597222222222", 94),
              3200: ("0.079861111111111", 92),
              3500: ("0.079861111111111", 92),
              2000: ("0.069444444444444", None),
              1930: ("0.063368055555555", None)}
    for cap in (None, 3200, 3500, 2000, 1930):
        n, _ = count_qp_above(cap)
        tag = "raw/off" if cap is None else str(cap)
        act = actual[cap][0]
        print(f"{tag:>10} {n:>8} {n/1152:>16.15f}   {act}")
