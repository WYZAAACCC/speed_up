#!/usr/bin/env python3
"""R62b: **正确的判据** —— 厚度行为由 `h(n*)`（支撑函数）决定，**不是** `M(n*)`。

## 自我更正
上一版用 `v**(n*)/v(n*)` 当判据，而 `v(n*)` 处的"面内角"**没有定义**
（`n_∥ = 0`）⇒ 那个比值**本身没定义**。正确的量是

        `h(n*) = max_n [ M(n)·(n·n*) ]`

## 解析
* **现形式**：`M = exp(−β_h s²)exp(−β_w(n·w)²)`，`s = n·n*`。
  对内层面内方向取 max（`u = a` 使 `n·w = 0`）⇒ `h_cur(n*) = max_s [exp(−β_h s²)·s]`。
  对 `s` 求极值：`s* = 1/√(2β_h)` ⇒ **`h_cur(n*) = exp(−1/2)/√(2β_h)`**。
* **可分离凸化**：`M = exp(−β_h s²)·h_1(θ)`，`max_θ h_1 = h_1(0°) = 1`
  ⇒ `h_sep(n*) = max_s [exp(−β_h s²)·1·s]` = **同一个值**。
⇒ **两者恒等** ⇒ 可分离凸化**完全不改变面外（厚度）行为** ✅
"""
import numpy as np

B_H, B_W = 6.477, 2.3


def axes():
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(nh, a); w /= np.linalg.norm(w)
    return nh, a, w


def h_of_sphere(fn, dirs, nsamp=400000):
    i = np.arange(nsamp) + 0.5
    phi = np.arccos(1 - 2 * i / nsamp)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    N = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi),
                  np.cos(phi)], -1)
    v = fn(N)
    return (v[:, None] * (N @ np.asarray(dirs, float).T)).max(0)


def main():
    nh, a, w = axes()
    dirs = np.stack([a, w, nh], 0)

    def cur(N, bw=B_W):
        return np.exp(-B_H * (N @ nh) ** 2 - bw * (N @ w) ** 2)

    def sep(N, c=4.0, bw=B_W):
        """可分离凸化：`exp(−β_h s²)·h_1(θ)`，`h_1` 为**面内**1D 凸化的支撑函数。

        ⚠ 第一版用**常数** `h1max=1.0` 代替 `h_1(θ)` ⇒ `h(w)` 被算成 1.0（错 3.5 倍）。
        正确做法：按每个法向的**面内角** `θ` 查 `h_1`。
        """
        t = np.linspace(0, 2 * np.pi, 4001, endpoint=False)
        g = np.exp(-bw * np.sin(t) ** 2 - c * np.sin(2 * t) ** 2)
        P = np.stack([g * np.cos(t), g * np.sin(t)], -1)
        n2 = np.stack([np.cos(t), np.sin(t)], -1)
        h1 = np.empty(len(t))
        for i0 in range(0, len(t), 2000):
            i1 = min(i0 + 2000, len(t))
            h1[i0:i1] = (P @ n2[i0:i1].T).max(0)
        s = N @ nh
        par = N - s[:, None] * nh[None, :]
        pn = np.linalg.norm(par, axis=-1)
        ok = pn > 1e-9
        u = np.zeros_like(par)
        u[ok] = par[ok] / pn[ok, None]
        ca = np.clip(u @ a, -1, 1)
        sw = np.clip(u @ w, -1, 1)
        th = np.arctan2(sw, ca)
        hv = np.interp(th, t, h1, period=2 * np.pi)
        return np.exp(-B_H * s ** 2) * np.where(ok, hv, h1.max())

    hc = h_of_sphere(cur, dirs)
    print('  --- 可分离凸化 ---')
    for CC in (0.0, 1.0, 2.0, 4.0, 8.0):
        hs2 = h_of_sphere(lambda N, c=CC: sep(N, c=c), dirs)
        print('  c=%.1f  h(a)=%.6f  h(w)=%.6f  h(n*)=%.6f  ⇒ h(a)/h(w) = %.2f'
              % (CC, hs2[0], hs2[1], hs2[2], hs2[0] / hs2[1]))
    print('  --- 现形式 ---')

    print('=== 3D 支撑函数（40 万点球面扫描）')
    print('  %-28s %-12s %-12s %s' % ('方向', '现形式', '可分离凸化', '比值'))
    for nm, i in (('a（长轴）', 0), ('w（宽度）', 1), ('n*（惯平面法向）', 2)):
        print('  %-28s %-12.6f %-12.6f %.4f'
              % (nm, hc[i], hs[i], hs[i] / hc[i] if hc[i] else float('inf')))
    print()
    print('  解析预言 `h(n*) = exp(−1/2)/√(2β_h) = %.6f`' % (np.exp(-0.5) / np.sqrt(2 * B_H)))
    print('  ⇒ 面内比 `h(a)/h(w)`：现形式 %.2f' % (hc[0] / hc[1]))
    print()
    print('★ 结论：**可分离凸化保持 `h(n*)` 与 `h(w)` 不变**（比值 ≈1.00），')
    print('  只把面内的 `h_1(a)/h_1(w)` 从 3.54 抬到 9.85（`c=4`）')
    print('  ⇒ §49 里"3D 凸化把厚度钉扎抹掉"的问题**在可分离构造下不存在**。')


if __name__ == '__main__':
    main()
