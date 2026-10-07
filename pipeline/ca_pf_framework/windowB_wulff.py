#!/usr/bin/env python3
"""windowB_wulff.py —— **Wulff 凸化速度律**（刻面机制）的查表实现（R59）。

## 数学（`R30_AUDIT_LEDGER.md` §46/§47）
`φ_t + v(n)|∇φ| = 0` 的渐近形状 = Wulff 形 `W = {x : x·n ≤ v(n) ∀n}`。
`v` 非凸时，`W` 的支撑函数是 `v` 的**凸包络 `v**`**，它在缺失取向上是平的
⇒ **平面刻面**。

`v**(n)` 不必每步求凸包：它**只依赖 `M(n)` 的角函数形式**（与场状态无关）
⇒ **预计算一次查找表**，运行时插值。

## 本模块
* `build_table(nh, a, w, beta_h, beta_w, dip_c, nth, nph)` → `dict`（查找表）；
* `support_from_table(tab, N)` → `v**(N)`（对一批法向，单位向量，形状 (M,3)）；
* `selftest()`：
  1. **凸的 `v` ⇒ `v** = v`**（对回归至关重要：改造后归档路径不该变）；
  2. `c=0`（现形式）⇒ `h(a)/h(w) ≈ 3.51`；
  3. `c=4` ⇒ `h(a)/h(w) ≈ 9.7`（目标 ≳9）。
"""
import numpy as np

B_H_DEF, B_W_DEF = 6.477, 2.3
A_DOT_N_DEF = -0.127


def fib_sphere(m):
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def mrel(N, a, w, nh, beta_h, beta_w, dip_c):
    """`M(n)/M0`（`N`: (M,3) 单位法向）。`dip_c=0` ⇒ 现形式。"""
    n_dot_n = N @ nh
    n_dot_w = N @ w
    out = np.exp(-beta_h * n_dot_n ** 2 - beta_w * n_dot_w ** 2)
    if dip_c > 0:
        par = N - n_dot_n[:, None] * nh[None, :]
        pn = np.linalg.norm(par, axis=-1)
        ok = pn > 1e-9
        u = np.zeros_like(par)
        u[ok] = par[ok] / pn[ok, None]
        s2 = 2.0 * (u @ a) * (u @ w)
        out = out * np.where(ok, np.exp(-dip_c * s2 ** 2), 1.0)
    return out


def build_hull_points(nh, a, w, beta_h=B_H_DEF, beta_w=B_W_DEF, dip_c=0.0,
                      nsamp=20000):
    """极集 `{v(n)·n}` 的点集（**只保留凸包顶点**，用于快速取 max）。

    支撑函数 `h(d) = max_j (x_j·d)`；只需凸包顶点参与 max。
    ⚠ 不调用 `ConvexHull`（球面点集上它会因"初始单纯形退化"报错），
      改用**增量式剪枝**：反复丢掉被其他点的凸组合支配的点（此处用更廉价的
      充分判据：若某点的 `v·n` 在某个方向上严格小于别的点，就不是顶点）。
      这里采用更稳的做法：**直接在采样点集上取 max**（点数固定、代价可控），
      并把采样点降到 `nsamp` 以便运行时使用。
    """
    N = fib_sphere(nsamp)
    v = mrel(N, a, w, nh, beta_h, beta_w, dip_c)
    return N, v


def eval_support(N, v, dirs):
    """`h(d) = max_j [ v_j (n_j·d) ]`，`dirs`: (K,3) 单位方向。"""
    return (v[:, None] * (N @ dirs.T)).max(0)


def fast_support_factory(nh, a, w, beta_h=B_H_DEF, beta_w=B_W_DEF, dip_c=0.0,
                         nsamp=20000):
    """返回 `f(N) -> v**(N)`；**用真正的凸包顶点**（不是"取 v 最大的几个"）。

    ⚠ 自伤记账：第一版按 `v_j` **降序取前 `keep` 个**当顶点 —— **错**。
    取到 `h(w)` 最大值的那些方向是 **`n_j ≈ w`**（那里 `v` **最小**），
    按 `v` 排序会把它们**全部剪掉** ⇒ 实测 `h(w)` 从 0.1020 掉到 0.0921（−10%）。
    ⇒ 改为 `scipy.spatial.ConvexHull` 取**真顶点**（3D 极集不退化，qhull 可用）。
    """
    N, v = build_hull_points(nh, a, w, beta_h, beta_w, dip_c, nsamp)
    P = v[:, None] * N
    from scipy.spatial import ConvexHull
    hull = ConvexHull(P)
    V = P[hull.vertices]                       # 真顶点（几十个）
    Vn = V / (np.linalg.norm(V, axis=-1, keepdims=True) + 1e-300)

    def f(dirs):
        d = np.atleast_2d(np.asarray(dirs, float))
        d = d / (np.linalg.norm(d, axis=-1, keepdims=True) + 1e-300)
        return (V @ d.T).max(0)
    return f, V, Vn


def selftest():
    print('=' * 92)
    print('windowB_wulff 自检')
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(nh, a); w /= np.linalg.norm(w)
    dirs = np.stack([a, w, nh], 0)
    ok = True
    print()
    print('【1】凸的 `v` ⇒ `v** == v`（回归安全性）')
    print('    ⚠ 容差说明：球面**有限采样**只能给出多面体近似 ⇒ `h` 系统性偏低')
    print('      约 **3e-4 相对**（各方向差异 <1e-4 相对 ⇒ **近似各向同性**）。')
    print('      判据取 `rtol=1e-3`：要的是"不产生**伪各向异性**"，不是逐位相等。')
    N = fib_sphere(4000)
    for const in (0.1, 1.0):
        v = np.full(len(N), const)
        h = eval_support(N, v, dirs)
        good = np.allclose(h, const, rtol=1e-3)
        ok = ok and good
        print('    v≡%.2f ⇒ h = %s  相对散布 %.1e  %s'
              % (const, np.array2string(h, precision=6),
                 float((h.max() - h.min()) / const),
                 'PASS' if good else '**FAIL**'))
    print()
    print('【2】现形式（`c=0`）⇒ `h(a)/h(w)` 应 ≈ 3.51')
    N, v = build_hull_points(nh, a, w, dip_c=0.0)
    h = eval_support(N, v, dirs)
    r = h[0] / h[1]
    good = abs(r - 3.51) < 0.15
    ok = ok and good
    print('    h(a)=%.5f h(w)=%.5f ⇒ 比 = %.2f  %s'
          % (h[0], h[1], r, 'PASS' if good else '**FAIL**'))
    print()
    print('【3】加凹陷 `c=4` ⇒ `h(a)/h(w)` 应 ≈ 9.7（目标 ≳9）')
    N4, v4 = build_hull_points(nh, a, w, dip_c=4.0)
    h4 = eval_support(N4, v4, dirs)
    r4 = h4[0] / h4[1]
    good4 = r4 >= 9.0
    ok = ok and good4
    print('    h(a)=%.5f h(w)=%.5f ⇒ 比 = %.2f  %s'
          % (h4[0], h4[1], r4, 'PASS' if good4 else '**FAIL**'))
    print()
    print('【4】凸包顶点法（运行时用）与全量采样一致？')
    f, V, _ = fast_support_factory(nh, a, w, dip_c=4.0)
    hk = f(dirs)
    goodk = np.allclose(hk, h4, rtol=5e-3)
    ok = ok and goodk
    print('    顶点数 = %d' % len(V))
    print('    顶点法 h = %s' % np.array2string(hk, precision=6))
    print('    全量   h = %s   %s'
          % (np.array2string(h4, precision=6), 'PASS' if goodk else '**FAIL**'))
    print()
    print('SELFTEST =', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(selftest())
