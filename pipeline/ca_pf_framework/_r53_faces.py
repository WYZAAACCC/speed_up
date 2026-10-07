#!/usr/bin/env python3
"""_r53_faces.py —— **面位置量具 v2**：把"直接解 φ=0"与"只算该场占优的区域"合起来。

## 为什么需要 v2（`R30_AUDIT_LEDGER.md` §36）
四个口径互差 3–20 倍，其中：
* ④ 直接解 φ=0 的**优点**：不受"簇/中位位置"影响，尖端变钝不会让它停住；
  **缺点**：`φ_k = 0` 的体可以**超出** `region == k`（argmin 只让一个场赢）
  ⇒ 会把别的场的地盘算进来；
* ③ 最大连通分量的**优点**：孤儿免疫；**缺点**：跨度口径，长指会撑大。

## v2 的口径（先写死）
对场 k 的每条网格边（x/y/z 各一次）：
  1. 两端都必须**在带内**（φ 有值）且**变号** ⇒ 线性插值出零交叉点 `x*`；
  2. **只收**"内侧胞（φ<0 的那个）属于 `region == k`"的交叉点
     ⇒ 这才是**场 k 实际占优的那部分界面**；
  3. 把收下的 `x*` 投影到 `(n, w, a)`，取 `max − min` ⇒ 三个方向的**面间距**。

## 正对照（**必须先过**，`AGENTS.md §3` 教训 19）
构造一个**解析长方体**的水平集：`φ = max(|p·n|−T/2, |p·w|−W/2, |p·a|−L/2)`
（负值在内），沿三个方向**按已知速率平移**（`L += 2·v_a·t` 等），
判据：v2 恢复出的速率必须等于给定速率（**±5%**）。
"""
import numpy as np

NM = 1e9


def face_extent(phi_k, region_k, dx, axes, nreg_ok=True):
    """v2 口径：返回 `dict(a=…, w=…, n=…)`（米），不可测的方向不返回。

    `phi_k`   : (N,N,N) 带内稀疏 φ（米，带外 NaN）
    `region_k`: (N,N,N) bool —— 该场**占优**的胞（`region == k`）
    `axes`    : dict(a=…, w=…, n=…) 单位向量
    """
    N = phi_k.shape[0]
    P = []
    for axis in (0, 1, 2):
        a_ = np.moveaxis(phi_k, axis, 0)
        r_ = np.moveaxis(region_k, axis, 0)
        for i in range(N - 1):
            p0, p1 = a_[i], a_[i + 1]
            r0, r1 = r_[i], r_[i + 1]
            m = np.isfinite(p0) & np.isfinite(p1) & (p0 * p1 < 0)
            if not m.any():
                continue
            # 内侧 = φ<0 的那一侧；要求它属于本场
            inner = np.where(p0 < 0, r0, r1)
            m = m & inner
            if not m.any():
                continue
            w = p0[m] / (p0[m] - p1[m])
            sub = np.argwhere(m)
            full = np.zeros((sub.shape[0], 3))
            oth = [j for j in range(3) if j != axis]
            full[:, axis] = (i + w) * dx
            full[:, oth[0]] = (sub[:, 0] + 0.5) * dx
            full[:, oth[1]] = (sub[:, 1] + 0.5) * dx
            P.append(full)
    if not P:
        return {}
    P = np.vstack(P)
    out = {}
    for nm, u in axes.items():
        u = np.asarray(u, float)
        u = u / (np.linalg.norm(u) + 1e-300)
        pr = P @ u
        if pr.size >= 20:
            out[nm] = float(pr.max() - pr.min())
    return out


def _analytic_box(N, L, W, T, axes, center=None):
    """解析长方体水平集：负值在内。返回 (phi, region_bool)。"""
    dx = L / N
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    c = np.array([L / 2.0] * 3) if center is None else np.asarray(center, float)
    P = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
    n = np.asarray(axes['n'], float); n /= np.linalg.norm(n)
    w = np.asarray(axes['w'], float); w /= np.linalg.norm(w)
    a = np.asarray(axes['a'], float); a /= np.linalg.norm(a)
    d = np.stack([P @ n, P @ w, P @ a], -1)
    half = np.array([T / 2.0, W / 2.0, L / 2.0])
    phi = np.max(np.abs(d) - half, axis=-1)
    return phi, (phi < 0)


def selftest():
    print('=' * 88)
    print('正对照：解析长方体（已知 L/W/T 与已知速率）')
    N = 96
    box_um = 9.0
    dx = box_um * 1e-6 / N
    # 取一组正交基（模拟变体的 n/w/a）
    n = np.array([-0.4424, 0.4425, -0.7801]); n /= np.linalg.norm(n)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(n, a); w /= np.linalg.norm(w)
    axes = dict(n=n, w=w, a=a)

    def run(L_nm, W_nm, T_nm):
        phi, reg = _analytic_box(N, box_um * 1e-6, 0, 0, axes)   # 只为拿坐标系
        ii = (np.arange(N) + 0.5) * dx
        X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
        c = np.array([box_um * 1e-6 / 2.0] * 3)
        P = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
        d = np.stack([P @ n, P @ w, P @ a], -1)
        half = np.array([T_nm * 1e-9 / 2, W_nm * 1e-9 / 2, L_nm * 1e-9 / 2])
        phi = (np.abs(d) - half).max(-1)
        return face_extent(phi, phi < 0, dx, axes)

    print('  %-10s %-9s %-9s %-9s' % ('给定 (nm)', 'L 恢复', 'W 恢复', 'T 恢复'))
    ok = True
    for (Ln, Wn, Tn) in ((1600, 700, 500), (2000, 700, 635), (1200, 400, 500)):
        r = run(Ln, Wn, Tn)
        got = (r.get('a', float('nan')) * NM, r.get('w', float('nan')) * NM,
               r.get('n', float('nan')) * NM)
        good = all(abs(g - e) <= 0.05 * e for g, e in zip(got, (Ln, Wn, Tn)))
        ok = ok and good
        print('  %-10s %-9.1f %-9.1f %-9.1f  %s'
              % ('%d/%d/%d' % (Ln, Wn, Tn), got[0], got[1], got[2],
                 'PASS' if good else '**FAIL**'))

    print()
    print('正对照 2：**已知速率**（把 3 个尺寸按给定速率一起长）')
    v = dict(a=2.0, w=0.5, n=0.1)          # nm/步
    st = 400
    L0, W0, T0 = 1600.0, 700.0, 400.0
    r0 = run(L0, W0, T0)
    r1 = run(L0 + 2 * v['a'] * st, W0 + 2 * v['w'] * st, T0 + 2 * v['n'] * st)
    print('  %-6s %-12s %-12s %s' % ('方向', '给定 (nm/步)', '恢复 (nm/步)', '判定'))
    for nm in ('a', 'w', 'n'):
        got = ((r1[nm] - r0[nm]) / 2.0) * NM / st
        good = abs(got - v[nm]) <= 0.05 * abs(v[nm]) + 0.02
        ok = ok and good
        print('  %-6s %-12.3f %-12.3f %s'
              % (nm, v[nm], got, 'PASS' if good else '**FAIL**'))
    print()
    print('SELFTEST =', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(selftest())
