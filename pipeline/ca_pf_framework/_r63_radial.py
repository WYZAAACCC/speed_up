#!/usr/bin/env python3
"""R63: **径向函数 `r(n)`**（凸化后的速度场）—— 与 `h(n)`（支撑函数）对照，并定离线判据。

## 依据（`R30_AUDIT_LEDGER.md` §50）
`P = {v(n)·n}`、凸包 `H`。Wulff 理论里：
* **支撑函数 `h(d) = max_{x∈H}(x·d)`** —— 决定**渐近形状**（`H` 在各方向的宽度）；
* **径向函数 `r(n)`** = 原点沿 `n` 到 `H` 边界的距离 —— **这才是引擎该用的速度场**
  （只有 `{r(n)·n} = H`）。
§49 的实现错用了 `h` ⇒ 处处高估（尤其凹区）⇒ `d(n)` 涨 35 倍。

## 本脚本
1. 由极集点云取 `ConvexHull`，用 `equations`（面法向 `f_k`、偏移 `c_k`）算
   `r(n) = min_{k: f_k·n>0} c_k/(f_k·n)`；
2. 对照 `M(n)` / `h(n)` / `r(n)` 在 `a`、`w`、`n*` 三个方向的值；
3. 给出 **Wulff 形 `H` 的长径比** `h(a)/h(w)`（= 渐近形状比，验收目标）。

## 判据（先写死）
  T-1 **`r(n*)/M(n*)` ≤ 5**（现形式；`h` 给 112 ⇒ 不合格）
  T-2 `h(a)/h(w)` **≥ 9**（`c=4` 的 Wulff 形）
  T-3 `r(a)/r(w)` 与 `h(a)/h(w)` **同量级**（差 ≤3 倍，说明速度场与形状一致）
"""
import numpy as np
from scipy.spatial import ConvexHull

B_H, B_W = 6.477, 2.3


def axes():
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(nh, a); w /= np.linalg.norm(w)
    return nh, a, w


def fib(m):
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi),
                     np.cos(phi)], -1)


def mrel(N, nh, a, w, bw=B_W, c=0.0):
    s = N @ nh
    out = np.exp(-B_H * s ** 2 - B_W * (N @ w) ** 2)
    if c > 0:
        par = N - s[:, None] * nh[None, :]
        pn = np.linalg.norm(par, axis=-1)
        ok = pn > 1e-9
        u = np.zeros_like(par)
        u[ok] = par[ok] / pn[ok, None]
        s2 = 2.0 * (u @ a) * (u @ w)
        out = out * np.where(ok, np.exp(-c * s2 ** 2), 1.0)
    return out


def hull_facets(P):
    h = ConvexHull(P, qhull_options='QJ')
    eq = h.equations                       # [f_x, f_y, f_z, c] with f·x + c ≤ 0
    f = eq[:, :3]
    c = -eq[:, 3]
    return f, c, h


def radial(P, dirs):
    f, c, _ = hull_facets(P)
    out = []
    for d in np.atleast_2d(dirs):
        d = d / (np.linalg.norm(d) + 1e-300)
        num = f @ d
        m = num > 1e-12
        out.append(float((c[m] / num[m]).min()) if m.any() else 0.0)
    return np.array(out)


def support(P, dirs):
    return (P @ np.atleast_2d(dirs).T).max(0)


def main():
    nh, a, w = axes()
    N = fib(60000)
    dirs = np.stack([a, w, nh], 0)
    print('  %-5s %-28s %-12s %-12s %-12s %s'
          % ('c', '方向', 'M(n)', 'h(n)', '**r(n)**', 'r/M'))
    ok = True
    for c in (0.0, 4.0):
        v = mrel(N, nh, a, w, c=c)
        P = v[:, None] * N
        hh = support(P, dirs)
        rr = radial(P, dirs)
        for i, nm in enumerate(('a', 'w', 'n*')):
            mm = float(mrel(dirs[i:i + 1], nh, a, w, c=c)[0])
            print('  %-5.1f %-28s %-12.6f %-12.6f %-12.6f %.2f'
                  % (c, nm, mm, hh[i], rr[i], rr[i] / mm if mm else float('inf')))
        # Wulff 形长径比（= 支撑函数之比）
        r_h = hh[0] / hh[1]
        r_r = rr[0] / rr[1]
        print('        ⇒ **Wulff 形** `h(a)/h(w)` = **%.2f**   ｜ 速度场 `r(a)/r(w)` = %.2f'
              % (r_h, r_r))
        if c == 0.0:
            t1 = rr[2] / float(mrel(dirs[2:3], nh, a, w, c=0.0)[0])
            print('        T-1 `r(n*)/M(n*)` = **%.2f**  %s'
                  % (t1, '✅ (≤5)' if t1 <= 5 else '❌'))
            ok = ok and t1 <= 5
        if c == 4.0:
            t2 = r_h >= 9.0
            t3 = (max(r_h, r_r) / max(min(r_h, r_r), 1e-9)) <= 3.0
            print('        T-2 `h(a)/h(w)` ≥ 9 : %s (%.2f)'
                  % ('✅' if t2 else '❌', r_h))
            print('        T-3 `r` 与 `h` 同量级（≤3×）: %s'
                  % ('✅' if t3 else '❌ (%.2f×)' % (max(r_h, r_r) / max(min(r_h, r_r), 1e-9))))
            ok = ok and t2 and t3
        print()
    print('SELFTEST =', 'PASS' if ok else 'FAIL')


if __name__ == '__main__':
    main()
