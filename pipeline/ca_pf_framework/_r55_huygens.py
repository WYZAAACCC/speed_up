#!/usr/bin/env python3
"""R55: **正确的筛选工具** —— 2D 支撑函数（Huygens/法向速度）的形状演化。

## 为什么不能用 §41 的 `A` 代理量
`A = <M|cosθ|>/<M|sinθ|>` 用 `|cosθ|` 加权，而**刻面体**的正确权重是**面积**
（侧面积 ≫ 端面积）⇒ 该代理量系统性低估端面**且依赖形状本身**。

## 本工具
把形状表示成**支撑函数** `h(θ)`（θ = 法向角）：
  * 演化：`h(θ, t+dt) = h(θ, t) + v(θ)·dt`，`v(θ) = M(θ)·ΔG`（筛选时取 `ΔG=1`）；
  * **凸化**：更新后取边界点 `x(θ) = h·n + h'·t` 的**凸包**
    ⇒ 这正是**刻面**的产生机制（`h` 在某方向"尖"出去 ⇒ 凸包接管 ⇒ 出平面）；
  * 尺寸：沿 `a` / `w` 的**跨度** = 凸包在对应方向上的宽度。

⇒ 若"刻面住棱角"能把 `v_a/v_w` 推到 ≳12，本工具应当直接显示出来。
"""
import numpy as np


def support_rect(ha, hw, th):
    """矩形的支撑函数（半宽 ha 沿 a、hw 沿 w）。`th` 是法向与 a 轴的夹角。"""
    return ha * np.abs(np.cos(th)) + hw * np.abs(np.sin(th))


def boundary_points(h, th):
    """由支撑函数给出边界点 `x = h·n + h'·t`（2D）。"""
    hp = np.gradient(h, th)
    n = np.stack([np.cos(th), np.sin(th)], -1)
    t = np.stack([-np.sin(th), np.cos(th)], -1)
    return h[:, None] * n + hp[:, None] * t


def extents(pts):
    """凸包在 a / w 方向上的跨度。"""
    from scipy.spatial import ConvexHull
    try:
        hull = ConvexHull(pts)
    except Exception:
        return None
    v = pts[hull.vertices]
    return (v[:, 0].max() - v[:, 0].min(), v[:, 1].max() - v[:, 1].min())


def evolve(mfun, ha0, hw0, steps, dt, nth=721):
    th = np.linspace(0, 2 * np.pi, nth)
    h = support_rect(ha0, hw0, th)
    v = mfun(np.abs(np.cos(th)), np.abs(np.sin(th)))
    out = []
    for i in range(steps):
        h = h + v * dt
        pts = boundary_points(h, th)
        e = extents(pts)
        if e is None:
            break
        out.append((i + 1, e[0], e[1]))
    return out


def m_cur(bw, bh=6.477, a_dot_n=-0.127):
    def f(c, s):
        n_dot_n = c * a_dot_n
        return np.exp(-bh * n_dot_n ** 2 - bw * s ** 2)
    return f


def m_rew(bw, p, bh=6.477, a_dot_n=-0.127):
    eps = np.exp(-bw)

    def f(c, s):
        n_dot_n = c * a_dot_n
        return np.exp(-bh * n_dot_n ** 2) * (eps + (1 - eps) * c ** p)
    return f


def rate(rec):
    if len(rec) < 5:
        return None
    x = np.array([r[0] for r in rec], float)
    ra = np.polyfit(x, np.array([r[1] for r in rec], float), 1)[0]
    rw = np.polyfit(x, np.array([r[2] for r in rec], float), 1)[0]
    return ra, rw


print('=' * 92)
print('2D 支撑函数演化：从 100×100（正方）出发，600 步，量 `v_a/v_w`')
print('（`ΔG=1`；目标：做出 9:1 需要 `v_a/v_w ≳ 12`）')
print()
print('  %-28s %-10s %-10s %-9s %s'
      % ('M(n) 形式', 'v_a', 'v_w', 'v_a/v_w', '末态 L/W'))
rows = []
for bw in (2.3, 3.0, 4.0, 6.0, 9.0):
    rec = evolve(m_cur(bw), 100.0, 100.0, 600, 0.1)
    r = rate(rec)
    if r:
        rows.append(('现形式 β_w=%.1f' % bw, r[0], r[1], r[0] / r[1],
                     rec[-1][1] / rec[-1][2]))
for p in (4, 8, 16, 32):
    rec = evolve(m_rew(2.3, p), 100.0, 100.0, 600, 0.1)
    r = rate(rec)
    if r:
        rows.append(('奖励 a (p=%d, β_w=2.3)' % p, r[0], r[1], r[0] / r[1],
                     rec[-1][1] / rec[-1][2]))
for nm, ra, rw, ratio, lw in rows:
    flag = '✅' if ratio >= 12 else ('接近' if ratio >= 6 else '')
    print('  %-28s %-10.4f %-10.4f %-9.2f %.2f  %s'
          % (nm, ra, rw, ratio, lw, flag))
print()
print('★ 判读：本工具**自带刻面机制**（凸包）')
print('  · 若大 `β_w` 能把 `v_a/v_w` 推到 ≳12 ⇒ **不需要新通道**，只需刻面住棱角；')
print('  · 若怎么做都在个位数 ⇒ **必须在驱动/几何层面加东西**（新通道）。')
