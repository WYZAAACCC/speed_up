#!/usr/bin/env python3
"""
比选 align4 的几种写法，选一个"在固相里精确等于 cos^2(2(phi-theta))、
且在 |E|->0 时二阶导数有界"的形式。

要求：
  (R1) |E| = 1（单晶粒内部）时精确等于 align4 = cos^2(2(phi-theta))
  (R2) |E| -> 0 时平滑趋于确定值，且 |d/dE|、|d2/dE2| 有界且尽量小

候选：
  cur    (E.g)^2 / ((S+eps1) G)                 eps1=1e-8   —— 现行，已知有 1e10 尖峰
  A      (P.Q)^2 / ((S^2+eps2) G^2)             eps2=1e-8
  B      (P.Q)^2 / ((S+eps2) G^2)               eps2=1e-6
  C      (P.Q)^2 / (G^2 + eps3)                 eps3=1e-30  —— 纯多项式，只对梯度正则
其中 S=Ex^2+Ey^2, P.Q=(Ex^2-Ey^2)(gx^2-gy^2)+4 Ex Ey gx gy。

用法： python3 probe_align_forms.py
"""

import math

E1, E2, E3 = 1e-8, 1e-8, 1e-30


def cur(Ex, Ey, gx, gy):
    S = Ex * Ex + Ey * Ey
    return (Ex * gx + Ey * gy) ** 2 / ((S + E1) * (gx * gx + gy * gy))


def _PQ(Ex, Ey, gx, gy):
    return (Ex * Ex - Ey * Ey) * (gx * gx - gy * gy) + 4.0 * Ex * Ey * gx * gy


def fA(Ex, Ey, gx, gy):
    S = Ex * Ex + Ey * Ey
    G = gx * gx + gy * gy
    return _PQ(Ex, Ey, gx, gy) ** 2 / ((S * S + E2) * G * G)


def fB(Ex, Ey, gx, gy):
    S = Ex * Ex + Ey * Ey
    G = gx * gx + gy * gy
    return _PQ(Ex, Ey, gx, gy) ** 2 / ((S + E2) * G * G)


def fC(Ex, Ey, gx, gy):
    G = gx * gx + gy * gy
    return _PQ(Ex, Ey, gx, gy) ** 2 / (G * G + E3)


def to_align4(f):
    """把 q 形式统一成 align4 = (2q-1)^2 的形状（cur 已经是 q）。"""
    return lambda Ex, Ey, gx, gy: (2.0 * f(Ex, Ey, gx, gy) - 1.0) ** 2


def gA(Ex, Ey, gx, gy):
    # A/B/C 给出的是 S^2*align4 量级，需要再除以 S^2 才是 align4 —— 但那会重新引入 1/S
    # 所以这里直接考察"乘进 L 的因子"本身： 2*value-1
    return 2.0 * fA(Ex, Ey, gx, gy) - 1.0


def d2(f, e, gx, gy, h=1e-5):
    hh = h * max(abs(e), 1e-14)
    return (f(e + hh, 0.0, gx, gy) - 2 * f(e, 0.0, gx, gy)
            + f(e - hh, 0.0, gx, gy)) / (hh * hh)


def scan(f, gx, gy, lo=1e-9, hi=1.0):
    best, beste = 0.0, 0.0
    e = hi
    while e > lo:
        v = abs(d2(f, e, gx, gy))
        if math.isfinite(v) and v > best:
            best, beste = v, e
        e *= 0.85
    return best, beste


def main():
    # 情形一：梯度沿 x，取向 theta=0 -> 完全对齐，真值 align4 = 1
    gx, gy = 1.0, 0.0
    print("情形：梯度沿 x，取向 theta=0（完全对齐，真值 = 1）")
    print(f"{'形式':>6} {'|E|=1':>10} {'|E|=0.25':>10} {'|E|=1e-3':>10} "
          f"{'峰值|d2/dE2|':>14} {'峰位':>10}")
    print("-" * 70)
    for name, f in (("cur", to_align4(cur)), ("A", to_align4(fA)),
                    ("B", to_align4(fB)), ("C", to_align4(fC))):
        v1 = f(1.0, 0.0, gx, gy)
        v2 = f(0.25, 0.0, gx, gy)
        v3 = f(1e-3, 0.0, gx, gy)
        pk, pe = scan(f, gx, gy)
        print(f"{name:>6} {v1:10.6f} {v2:10.6f} {v3:10.6f} {pk:14.4g} {pe:10.2e}")

    print()
    print("判据 R1：|E|=1 必须 = 1.000000（否则固相内部物理被改）")
    print("判据 R2：峰值 |d2/dE2| 越小越好（cur 的 1.28e10 是卡死的元凶）")
    print()
    print("参考：固相内部 |E|=1 处 cur 的 |d2/dE2| = "
          f"{abs(d2(to_align4(cur), 1.0, gx, gy)):.3g}")


if __name__ == "__main__":
    main()
