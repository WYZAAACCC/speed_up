#!/usr/bin/env python3
"""
量化证实：align4 对 AuxVariable grad_Tx/grad_Ty 求导所引入的 1/G^2 垃圾有多大。

背景：
  align4_prop 的 coupled_variables 含 grad_Tx grad_Ty（两个 AuxVariable），
  derivative_order=2，表达式分母含 (grad_Tx^2+grad_Ty^2) = G（无正则化）。
  于是 d(align4)/d(grad_Tx) ∝ 1/G，d2 ∝ 1/G^2。
  但这些导数项在牛顿步里乘的是 Δgrad_T = 0（FunctionAux 精确给出），
  所以它们是矩阵里的**死重量**——不帮忙，只破坏条件数。

本脚本在真实网格上扫描 G 的最小值，给出垃圾项的量级。
"""

import math
import numpy as np

C_R = 28.0 / (2.0 * math.pi * 20.0)
K_R = 0.6 / (2.0 * 6.0e-6)

XMIN, XMAX = -2.8e-4, 1.5e-4
YMIN, YMAX = 0.0, 1.5e-4
TEND = 6.5e-4


def grads(x, y, t):
    xi = x + 1.2e-4 - 0.6 * t
    R = np.sqrt(xi * xi + y * y + 1e-10)
    e = np.exp(-K_R * (R + xi))
    pref = C_R / R * e
    gx = pref * (-xi / (R * R) - K_R * (R + xi) / R)
    gy = pref * (-y / (R * R) - K_R * y / R)
    return gx, gy


def main():
    print("=" * 78)
    print("G = |grad T|^2 在真实网格上的取值范围")
    print("=" * 78)

    x = np.linspace(XMIN, XMAX, 2000)
    y = np.linspace(YMIN, YMAX, 1000)
    X, Y = np.meshgrid(x, y, indexing="ij")

    gmin_all, t_at, xy_at = np.inf, None, None
    for t in np.linspace(0.0, TEND, 14):
        gx, gy = grads(X, Y, t)
        G = gx * gx + gy * gy
        k = np.unravel_index(np.argmin(G), G.shape)
        if G[k] < gmin_all:
            gmin_all = G[k]
            t_at = t
            xy_at = (X[k], Y[k])
    print(f"  G_min = {gmin_all:.6e}   在 t={t_at:.3e}, (x,y)=({xy_at[0]:.3e}, {xy_at[1]:.3e})")
    print(f"  G_max ≈ {np.max(G):.6e}")

    gx, gy = grads(X, Y, 0.0)
    G = gx * gx + gy * gy
    print(f"  t=0 时 G 的范围: {G.min():.6e} ~ {G.max():.6e}")
    print()

    print("=" * 78)
    print("由此产生的雅可比垃圾项量级（d/dgrad_T ~ 1/G, d2 ~ 1/G^2）")
    print("=" * 78)
    print(f"{'量':>28} {'在 G_min 处':>16} {'在 G 中位数处':>18}")
    Gmed = float(np.median(G))
    for name, expr in (("1/G", lambda g: 1.0 / g),
                       ("1/G^2", lambda g: 1.0 / (g * g)),
                       ("1/G^3 (二阶导典型)", lambda g: 1.0 / (g ** 3))):
        print(f"{name:>28} {expr(gmin_all):16.4e} {expr(Gmed):18.4e}")
    print()

    print("=" * 78)
    print("与主导对角项对比")
    print("=" * 78)
    kappa, L_typ, h = 1.8e-6, 0.204, 6.98e-7      # L 在 T=1900 K
    diag = L_typ * kappa / (h * h)
    print(f"  ACInterface 主导对角 L*kappa/h^2 = {diag:.4e}   (h = {h:.3e} m)")
    print(f"  时间导数对角 1/dt (dt=1e-6)     = {1e6:.4e}")
    print(f"  垃圾项 1/G^3 在 G_min 处        = {1.0/gmin_all**3:.4e}")
    print()

    print("=" * 78)
    print("网格上是否有 G 恰好为 0 的单元（会导致 1/G = Inf -> NaNORINF）")
    print("=" * 78)
    print(f"  y=0 边界上 grad_Ty 恒为 0（grad_Ty ∝ y）")
    gx0, gy0 = grads(np.linspace(XMIN, XMAX, 430), np.zeros(430), 0.0)
    G0 = gx0 * gx0 + gy0 * gy0
    print(f"  y=0 线上 G 的范围: {G0.min():.6e} ~ {G0.max():.6e}")
    print(f"  y=0 线上 |grad_Tx| 的最小值: {np.abs(gx0).min():.4e} K/m")
    print("  => grad_Tx 在 y=0 上不为零，所以 G>0。")
    print("  但**若 FunctionAux 尚未填充**（initial 阶段），grad_Tx=grad_Ty=0")
    print("  => G=0 => 1/G^2 = Inf => AMG 报 DIVERGED_NANORINF。这与实测一致。")


if __name__ == "__main__":
    main()
