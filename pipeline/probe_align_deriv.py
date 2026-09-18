#!/usr/bin/env python3
"""
验证猜想：我写的 align4 在 |E| -> 0 处导数爆掉，且爆点正好在 S ~ eps 处。

    q      = (Ex*gx+Ey*gy)^2 / ((Ex^2+Ey^2+eps)*(gx^2+gy^2))
    align4 = (2q-1)^2

align4 只依赖 E 的**方向**，是尺度无关量，所以 d(方向)/dE ~ 1/|E| 必然发散。
eps 把 0/0 挡住了，却在 |E| ~ sqrt(eps) 处留下一个导数尖峰。

对照"安全形式"（用倍角形式，并把 1/S^2 换成 1/(S^2+delta^2)）：
    P.Q = (Ex^2-Ey^2)(gx^2-gy^2) + 4*Ex*Ey*gx*gy
    align4_safe = (P.Q)^2 / ((S^2 + delta^2) * (gx^2+gy^2)^2),  S = Ex^2+Ey^2
它在 |E|->0 时平滑趋于 0，且一阶/二阶导数都有界。

用法： python3 probe_align_deriv.py
"""

import math

EPS = 1e-8        # 现在算例里用的
DELTA2 = 1e-8     # 拟改用


def align4(Ex, Ey, gx, gy):
    q = (Ex * gx + Ey * gy) ** 2 / ((Ex * Ex + Ey * Ey + EPS) * (gx * gx + gy * gy))
    return (2.0 * q - 1.0) ** 2


def align4_safe(Ex, Ey, gx, gy):
    S = Ex * Ex + Ey * Ey
    PQ = (Ex * Ex - Ey * Ey) * (gx * gx - gy * gy) + 4.0 * Ex * Ey * gx * gy
    return PQ * PQ / ((S * S + DELTA2) * (gx * gx + gy * gy) ** 2)


def d1(f, Ex, Ey, gx, gy, h=1e-6):
    """对 Ex 的一阶中心差分（相对步长，避免量级问题）。"""
    hh = h * max(abs(Ex), 1e-12)
    return (f(Ex + hh, Ey, gx, gy) - f(Ex - hh, Ey, gx, gy)) / (2 * hh)


def d2(f, Ex, Ey, gx, gy, h=1e-5):
    hh = h * max(abs(Ex), 1e-12)
    return (f(Ex + hh, Ey, gx, gy) - 2 * f(Ex, Ey, gx, gy)
            + f(Ex - hh, Ey, gx, gy)) / (hh * hh)


def main():
    gx, gy = 1.0, 0.0          # 梯度方向；|g| 的大小不影响 align4（尺度无关）
    print("梯度沿 x 轴，晶粒取向 theta=0 -> 应完全对齐 align4=1")
    print()
    print(f"{'|E|':>12} {'align4':>12} {'|d/dE|':>14} {'|d2/dE2|':>14}   "
          f"{'safe align4':>12} {'|safe d/dE|':>14} {'|safe d2|':>14}")
    print("-" * 96)
    for e in [1.0, 0.3, 1e-1, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 1e-6, 0.0]:
        Ex = e if e > 0 else 1e-12
        Ey = 0.0
        a = align4(Ex, Ey, gx, gy)
        s = align4_safe(Ex, Ey, gx, gy)
        if e > 0:
            a1, a2 = abs(d1(align4, Ex, Ey, gx, gy)), abs(d2(align4, Ex, Ey, gx, gy))
            s1, s2 = (abs(d1(align4_safe, Ex, Ey, gx, gy)),
                      abs(d2(align4_safe, Ex, Ey, gx, gy)))
        else:
            a1 = a2 = s1 = s2 = float("nan")
        print(f"{e:12.1e} {a:12.6f} {a1:14.4g} {a2:14.4g}   "
              f"{s:12.6f} {s1:14.4g} {s2:14.4g}")

    print()
    # 找当前形式的导数尖峰位置
    best, beste = 0.0, 0.0
    e = 1e-1
    while e > 1e-8:
        v = abs(d2(align4, e, 0.0, gx, gy))
        if v > best:
            best, beste = v, e
        e *= 0.8
    print(f"当前形式：二阶导数尖峰 |d2/dE2| = {best:.4g}，出现在 |E| ~ {beste:.2e}")
    print(f"          而 sqrt(eps) = {math.sqrt(EPS):.2e}  <- 与尖峰位置吻合")
    print(f"          对照：固相内部 |E| ~ 1 时 |d2/dE2| ~ "
          f"{abs(d2(align4, 1.0, 0.0, gx, gy)):.4g}")
    print()
    print(f"安全形式：同样扫描范围内的最大 |d2/dE2| = "
          f"{max(abs(d2(align4_safe, e, 0.0, gx, gy)) for e in [1.0,1e-1,1e-2,1e-3,1e-4,1e-5]):.4g}")


if __name__ == "__main__":
    main()
