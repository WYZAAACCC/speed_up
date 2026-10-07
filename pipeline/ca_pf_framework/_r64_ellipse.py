#!/usr/bin/env python3
"""R64: **凸的极曲线构造** —— 用"椭圆径向函数"代替 `exp(−β_w sin²θ)`。

## 动机（`R30_AUDIT_LEDGER.md` §51 的出路 ①）
Wulff 两难：极集薄（`M(n*)=0.0015`）⇒ 其**凸包很胖**（`r(n*)=0.168`，109×）
⇒ "刻面"与"惯习面钉扎"不可兼得。
**除非极集本身就是凸的** ⇒ 凸化成为**恒等变换** ⇒ 两难消失。

## 现形式为什么不凸
面内部分 `v(θ) = exp(−β_w sin²θ)`：在 `θ=0` 处
`v'' = −2β_w v = −4.6` ⇒ **`F = v + v'' = 1 − 4.6 = −3.6 < 0`** ⇒ 尖端附近**凹**
（与 §44 实测的"`F<0` 覆盖 `0–21.4°`"一致）。

## 本构造
面内极曲线直接取**椭圆**（径向函数）：
        `g(θ) = A·B / sqrt(B²cos²θ + A²sin²θ)`，`g(0)=A`、`g(90°)=B`
⇒ 极曲线**就是那个椭圆** ⇒ **凸** ✓（凸化 = 恒等）
⇒ `v(a)/v(w) = A/B` —— **直接就是长径比**，想给多少给多少。
面外仍用解析式 `exp(−β_h(n·n*)²)` ⇒ **厚度钉扎不动**。

## 判据（先写死）
  E-1 面内 `F(θ) = v + v'' > 0` 全程（凸）
  E-2 `hull(P)` 与 `P` 一致（凸化 = 恒等）：`h(a)/h(w)` = `A/B`（±3%）
  E-3 `h(n*)/M(n*)` 与**现形式**同量级（≤1.2×）⇒ 厚度行为不被改坏
"""
import numpy as np
from scipy.spatial import ConvexHull

B_H, A_DOT_N = 6.477, -0.127


def axes():
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(nh, a); w /= np.linalg.norm(w)
    return nh, a, w


def g_ellipse(th, ratio):
    """椭圆径向函数：`A=1`、`B=1/ratio`。"""
    A, B = 1.0, 1.0 / ratio
    return A * B / np.sqrt(B ** 2 * np.cos(th) ** 2 + A ** 2 * np.sin(th) ** 2)


def g_exp2(th, bw=2.3):
    return np.exp(-bw * np.sin(th) ** 2)


def fib(m):
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi),
                     np.cos(phi)], -1)


def build(N, nh, a, w, gfun):
    s = N @ nh
    par = N - s[:, None] * nh[None, :]
    pn = np.linalg.norm(par, axis=-1)
    ok = pn > 1e-9
    u = np.zeros_like(par)
    u[ok] = par[ok] / pn[ok, None]
    ca = np.clip(u @ a, -1, 1)
    sw = np.clip(u @ w, -1, 1)
    th = np.arctan2(sw, ca)
    g = gfun(th)
    return np.exp(-B_H * s ** 2) * np.where(ok, g, gfun(np.zeros_like(th)))


def support(P, dirs):
    return (P @ np.atleast_2d(dirs).T).max(0)


def main():
    nh, a, w = axes()
    dirs = np.stack([a, w, nh], 0)
    print('=== E-1 面内凸性 `F(θ) = v + v''`')
    th = np.linspace(1e-4, np.pi / 2 - 1e-4, 4001)
    d = th[1] - th[0]
    for nm, g in (('现形式 exp(−β_w sin²θ)', lambda t: g_exp2(t)),
                  ('椭圆 (ratio=9)', lambda t: g_ellipse(t, 9.0))):
        v = g(th)
        F = v + np.gradient(np.gradient(v, d), d)
        neg = th[F < 0]
        print('  %-26s min F = %+-9.4f  `F<0` 区间 = %s'
              % (nm, F.min(),
                 '无 ✅' if neg.size == 0 else '%.1f°–%.1f° ❌'
                 % (np.degrees(neg[0]), np.degrees(neg[-1]))))
    print()
    N = fib(60000)
    print('=== E-2/E-3 支撑函数（凸化后的 Wulff 形）')
    print('  %-22s %-11s %-11s %-11s %-9s %s'
          % ('形式', 'h(a)', 'h(w)', 'h(n*)', 'h(a)/h(w)', 'h(n*) 相对现形式'))
    v_cur = build(N, nh, a, w, g_exp2)
    h_cur = support(v_cur[:, None] * N, dirs)
    for ratio in (3.0, 6.0, 9.0, 12.0):
        v = build(N, nh, a, w, lambda t, r=ratio: g_ellipse(t, r))
        h = support(v[:, None] * N, dirs)
        print('  %-22s %-11.5f %-11.5f %-11.5f %-9.2f %.3f'
              % ('椭圆 ratio=%.0f' % ratio, h[0], h[1], h[2], h[0] / h[1],
                 h[2] / h_cur[2]))
    print('  %-22s %-11.5f %-11.5f %-11.5f %-9.2f %.3f'
          % ('现形式', h_cur[0], h_cur[1], h_cur[2], h_cur[0] / h_cur[1], 1.0))
    print()
    print('★ 判读：')
    print('  · `F<0` 若在椭圆形式下**消失** ⇒ 极曲线凸 ⇒ 凸化是恒等变换（两难消失）；')
    print('  · `h(a)/h(w)` 若 ≈ `ratio` ⇒ 形状比 = 设计比，**不需要**任何凸化实现；')
    print('  · `h(n*)` 若与现形式接近 ⇒ 厚度钉扎未被改坏。')


if __name__ == '__main__':
    main()
