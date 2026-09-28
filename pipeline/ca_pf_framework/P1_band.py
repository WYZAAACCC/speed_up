#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1_band.py --- P1 的第二条隔离：**界面膨胀是否由"带的构造"造成**。

动机（P1 的第一条隔离结论）
--------------------------
`central` 的界面膨胀是 `upwind` 的 2.6 倍（同半径下），但两者都远超解析键测度
⇒ **换格式只是缓解**。所以再查"怎么构造那条带"：
  * `band_cells`  —— 速度**延拓**带宽（胞）
  * `iface_band`  —— 界面**种子**带宽（胞，阈值 `|φ_w| ≤ iface_band·dx`）
两者共同决定"哪些胞被推进"，也就是带的形状会不会自己长出来。

判据
----
  P1-2 在**同一半径**（~525 nm）下比"界面按键数 / 解析键测度"。
      若某个参数组合把它压到 ~1.5（纯阶梯误差量级）⇒ 那组就是修法（**不需要改物理**）。
      量具：解析键测度 = `4πR²/dx²`（阶梯误差已知 +48.5%@R/dx=6，见 T1）。

用法：python3 P1_band.py [--N 64] [--steps 120]
退出码：0 = 找到可用组合 / 1 = 没找到（需换思路）
"""
import os
import sys
import argparse
import itertools

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

DF, MOB = 2.0e8, 1e-9


def run(N, dx, adv, band, iband, steps):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=4, reinit_every=0)
    g.seed_sphere(1, [L / 2] * 3, 0.15 * L)
    g.init_parent()
    c0 = np.array([L / 2] * 3)
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(steps):
        g.advance(dt, band_cells=band, iface_band=iband, adv_grad=adv)
    reg = g.region()
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    idx = np.argwhere(reg == 1)
    if idx.size == 0:
        return None
    R = float(np.linalg.norm((idx.astype(float) + 0.5) * dx - c0, axis=1).mean())
    A_an = 4.0 * np.pi * R ** 2 / dx ** 2          # 解析键测度（阶梯会高估）
    return R, nb, nb / max(A_an, 1e-30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=120)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 100)
    print('P1 第二条隔离 —— 带的构造   N=%d Δx=%.0f nm  steps=%d（固定到同一半径附近）'
          % (N, a.dx_nm, a.steps))
    print('  判据：`界面键数 / 解析键测度`；纯阶梯误差已知 ≈ +48%%（R/dx≈6）')
    print('=' * 100)
    print('%-9s %-7s %-6s | %-9s %-10s %-10s %s' %
          ('adv', 'band', 'iband', 'R (nm)', '键数', '键/解析', '判定'))
    best = None
    for adv, band, iband in itertools.product(
            ('central', 'upwind'), (5, 10, 20, 40), (1.0, 2.0, 3.0)):
        r = run(N, dx, adv, band, iband, a.steps)
        if r is None:
            continue
        R, nb, ratio = r
        tag = ''
        if 500e-9 <= R <= 550e-9:              # 只在"同一半径"区间里比
            if best is None or ratio < best[0]:
                best = (ratio, adv, band, iband, R)
            tag = '★可比'
        print('%-9s %-7d %-6.1f | %-9.1f %-10d %-10.2f %s'
              % (adv, band, iband, R * 1e9, nb, ratio, tag), flush=True)
    print()
    if best is None:
        print('  ⚠ 没有落在 R∈[500,550] nm 的组合 ⇒ 本轮不可比（调步数重跑）')
        return 2
    print('  ⇒ 同半径下最好的组合：adv=%s band=%d iface_band=%.1f ⇒ 键/解析 = %.2f'
          % (best[1], best[2], best[3], best[0]))
    ok = best[0] < 1.8
    print('  %s' % ('**找到可用组合**（接近纯阶梯误差量级 ⇒ 不需要改物理）'
                   if ok else '**没找到** —— 最好也只到 %.2f，说明膨胀不在"带的构造"上，'
                   '需要走"保几何投影"那条路' % best[0]))
    print('=' * 100)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
