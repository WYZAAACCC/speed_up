#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_metric.py --- ★★★ 几何量具的**正对照**：`max−min` 到底偏多少？有没有更好的口径？

为什么要做（Round 141）
----------------------
用户指示「重新检查初始条件与最终结果，**不要误用数据**」。全仓库的 `L/W/T` 读数
一律用 `MEASUREMENT_SPEC R3` 的 `max−min`（**胞中心之差，不加 `dx`**）。
`R3` 给的理由是「投影极差 **+1 胞**（薄板 +25%）」⇒ 所以**不加** `dx`。

但 `_probe_shape.py --selftest` 的解析正对照（N=64 / Δx=166.7 nm）实测长方体
`3000×1500×800 nm` 报成 `2833.9 × 1166.9 × 500.1`（T 偏 **−37.5%**）。
⇒ 与 `R3` 的方向**相反**。原因直白：胞心判据下一个厚 `n` 胞的板只报 `(n−1)·dx`。

本探针把这件事变成**可判定的**：对**解析已知**的形状同时算 5 种口径，报各自偏差，
并做取向扫描与薄板扫描，再选一个口径。

五种口径
--------
  C-1 `max−min`（`R3` 现状，胞心之差，不加 dx）
  C-2 `max−min + dx`（"加一胞"，`fill_n` 用的口径）
  C-3 `max−min + dx/2`（半胞无偏化）
  C-4 **亚胞支撑函数**（唯一用到水平集亚胞信息的口径）：
      `ψ = φ_K − min_{l≠K} φ_l`（内部 <0）；`d = ψ/|∇ψ| ≈ 到边界的符号距离`（内部 ≤0）
      ⇒ `h(u) = max_{胞∈K}( x·u − d(x) )`，跨度 `= h(u) + h(−u)`。
      **理论保证：`h(u)` 只可能低估、不会高估**（因为 `|d(x)|` 是到最近边界点的距离，
      沿 `u` 走 `|d|` 必定还在体内）⇒ 取 max 后对长方体**精确**。
  C-5 **体积反解**：`T = V/(L·W)`，`V = ncell·dx³` 精确，`L,W` 用 C-4。

用法：python3 _probe_metric.py [--N 64] [--dx-nm 166.7]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=166.7)
a = ap.parse_args()

N = a.N
dx = a.dx_nm * 1e-9
L = N * dx
c = np.array([L / 2] * 3)
X = (np.arange(N) + 0.5) * dx
gx = X[:, None, None] - c[0]
gy = X[None, :, None] - c[1]
gz = X[None, None, :] - c[2]

KEYS = ('L', 'P', 'H', 'S', 'V')
CI = {'L': 'C-1 `max−min`', 'P': 'C-2 `+dx`', 'H': 'C-3 `+dx/2`',
      'S': 'C-4 亚胞支撑', 'V': 'C-5 体积反解'}


def mk_psi(sdf):
    """引擎口径：两区 `ψ = φ_1 − φ_0`（`seed_plate` 里 `φ_0 = −sdf`）⇒ `ψ = 2·sdf`。"""
    return 2.0 * sdf


def measure(psi, axes):
    """返回 {口径: (L,W,T)}；axes = (a_ax, w_ax, n_ax)，可非正交、可倾斜。"""
    m = psi < 0
    ncell = int(m.sum())
    if ncell < 8:
        return None
    # ★ 稳健的 |∇ψ|：中心差分在 `max()` 的脊上会**抵消到 0**（实测把 C-4 打到 1e14%），
    #   故用**单向差分的均方**（SDF 沿一轴时 D⁺=D⁻=1 ⇒ 给 1 ✓；脊上 D⁺=a, D⁻=−a ⇒ 给 a ✓）。
    acc = np.zeros_like(psi)
    for ax in range(3):
        fp = np.roll(psi, -1, axis=ax)
        fm = np.roll(psi, +1, axis=ax)
        dp = (fp - psi) / dx
        dm = (psi - fm) / dx
        for sl in [slice(None)] * 3:
            pass
        acc += 0.5 * (dp ** 2 + dm ** 2)
    gm = np.sqrt(acc)
    ii = np.argwhere(m)
    iif = ii.astype(float)
    xyz = (iif + 0.5) * dx
    psin = psi[tuple(ii.T)]
    # `d` 必须落在物理合理区间：|d| 不会超过"到最近边界的距离"，数值上截到 2Δx
    d = psin / np.maximum(gm[tuple(ii.T)], 1e-3)
    d = np.clip(d, -2.0 * dx, 0.0)                 # 内部 ≤ 0
    out = {k: [] for k in KEYS}
    for ax in axes:
        p = xyz @ ax
        sp = float(p.max() - p.min())
        out['L'].append(sp)
        out['P'].append(sp + dx)
        out['H'].append(sp + 0.5 * dx)
        q = p - d
        out['S'].append(float(q.max() - q.min()))
    V = ncell * dx ** 3
    out['V'] = [out['S'][0], out['S'][1], V / max(out['S'][0] * out['S'][1], 1e-30)]
    return out, gm


def rotz(th):
    t = np.deg2rad(th)
    return np.array([[np.cos(t), -np.sin(t), 0.0],
                     [np.sin(t), np.cos(t), 0.0],
                     [0.0, 0.0, 1.0]])


AX = (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))
A, B, C = 1.5e-6, 0.75e-6, 0.40e-6

print('=' * 108)
print('_probe_metric —— 几何量具正对照   N=%d Δx=%.1f nm  L=%.3f µm' % (N, a.dx_nm, L * 1e6))
print('=' * 108)


def table(tag, res, truth):
    print('   %-14s %10s %10s %10s   %8s %8s %8s' % (tag, 'L(nm)', 'W(nm)', 'T(nm)',
                                                     '偏L', '偏W', '偏T'))
    for k in KEYS:
        v = res[k]
        print('   %-14s %10.1f %10.1f %10.1f   %+7.1f%% %+7.1f%% %+7.1f%%'
              % (CI[k], v[0] * 1e9, v[1] * 1e9, v[2] * 1e9,
                 (v[0] / truth[0] - 1) * 100, (v[1] / truth[1] - 1) * 100,
                 (v[2] / truth[2] - 1) * 100))


# ---------------------------------------------------------------- Q-1 长方体
print('\n■ Q-1 长方体 3000×1500×800 nm（轴对齐，解析真值）')
box = np.maximum(np.maximum(np.abs(gx) - A, np.abs(gy) - B), np.abs(gz) - C)
r, gm = measure(mk_psi(box), AX)
ib = np.abs(mk_psi(box)) <= 1.5 * dx * 2
print('   健康度：`ψ` 带内 |∇ψ| 中位 = %.3f（理想 2.000，因 `ψ=2·sdf`）⇒ C-4 除的就是它'
      % np.median(gm[ib]))
table('口径', r, (A * 2, B * 2, C * 2))

# ---------------------------------------------------------------- Q-2 倾斜（阶梯界面）
print('\n■ Q-2 ★ 倾斜（阶梯）界面：把**长方体本体**绕 z 转 θ，设计轴固定为 x/y/z')
print('   （解析投影跨度：L(θ)=3000cosθ+1500sinθ,  W(θ)=3000sinθ+1500cosθ,  T=800 恒定）')
print('   %-6s %-9s %s' % ('θ', '解析L/W', '  '.join('%s L/W/T偏差' % CI[k] for k in ('L', 'P', 'S'))))
for th in (0.0, 7.0, 15.0, 23.0, 30.0, 45.0):
    R = rotz(th)
    # 精确的"旋转长方体" SDF：把查询点变回盒坐标系
    ux = gx * R[0, 0] + gy * R[1, 0] + gz * R[2, 0]
    uy = gx * R[0, 1] + gy * R[1, 1] + gz * R[2, 1]
    uz = gx * R[0, 2] + gy * R[1, 2] + gz * R[2, 2]
    rb = np.maximum(np.maximum(np.abs(ux) - A, np.abs(uy) - B), np.abs(uz) - C)
    rr, _ = measure(mk_psi(rb), AX)
    t = np.deg2rad(th)
    tL = 3000 * np.cos(t) + 1500 * np.sin(t)
    tW = 3000 * np.sin(t) + 1500 * np.cos(t)
    s = '  '.join('(%+6.1f,%+6.1f,%+6.1f)' % ((rr[k][0] / (tL * 1e-9) - 1) * 100,
                                              (rr[k][1] / (tW * 1e-9) - 1) * 100,
                                              (rr[k][2] / 800e-9 - 1) * 100) for k in ('L', 'P', 'S'))
    print('   %-6.1f %4.0f/%-4.0f %s' % (th, tL, tW, s))

# ---------------------------------------------------------------- Q-2b ★ 关键：斜轴
# 为什么这一条最重要：全仓库的 `L/W/T` 用的是 `a_ax / w_ax / n_hab` —— **斜的**晶体学轴。
# 而 `max−min` 的"少一胞"偏差来自**格点在轴上的投影间距 = dx**；斜轴下投影会**致密填充**
# ⇒ `max−min` 的偏差远小于一胞。**必须实测，不能推理。**
print('\n■ Q-2b ★★ **斜轴**（决定归档读数要不要改）：长方体沿**一般方向** u 的跨度有解析式')
print('   `W(u) = 2(A|u_x| + B|u_y| + C|u_z|)`（长方体的支撑函数差）')
GEN = [('u=x 轴对齐', np.array([1.0, 0, 0])),
       ('u=(1,1,0)/√2', np.array([1.0, 1, 0]) / np.sqrt(2)),
       ('u=(1,2,3)/√14', np.array([1.0, 2, 3]) / np.sqrt(14)),
       ('u=(10,5,5,3)型', np.array([0.6180, 0.3717, 0.6910])),
       ('u=(0.1,0.7,0.7053)', np.array([0.1, 0.7, 0.7053])),
       ('u 随机1', np.array([0.3271, -0.8130, 0.4811])),
       ('u 随机2', np.array([-0.5602, 0.2190, 0.7986]))]
print('   %-20s %10s %s' % ('方向 u', '解析跨度', '  '.join('%s' % CI[k] for k in ('L', 'P', 'H', 'S'))))
for nm, u in GEN:
    u = u / np.linalg.norm(u)
    wtrue = 2 * (A * abs(u[0]) + B * abs(u[1]) + C * abs(u[2]))
    rr, _ = measure(mk_psi(box), (u, u, u))
    s = '  '.join('%+8.1f%%' % ((rr[k][0] / wtrue - 1) * 100) for k in ('L', 'P', 'H', 'S'))
    print('   %-20s %10.1f %s' % (nm, wtrue * 1e9, s))
print('   ⇒ 若"轴对齐"行 C-1 偏 −30% 而"斜轴"行的 C-1 偏 ≈0 ⇒ **归档读数无需改口径**；')
print('     若斜轴行也显著偏负 ⇒ `R3` 的"不加 dx"必须推翻。')

# ---------------------------------------------------------------- Q-3 薄板（集合平均）
# ★ 关键：轴对齐 + 面正好落在胞心上是**退化平局**（Q-3 第一版就被它骗了：
#   n 为偶数时 `+dx` 恒给 0.0%，看着"精确"，其实是 `n_cells = n+1` 的巧合）。
#   ⇒ 必须扫**亚胞偏移**，报**系综平均偏差**与**极差**，这才是量具的真实偏差。
OFFS = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0 / 3, 2.0 / 3)
print('\n■ Q-3 ★ 薄板 + **亚胞偏移系综**：厚 t = n·Δx（n=2..12），面内恒 3000×1500 nm')
print('   每个 n 扫 %d 个亚胞偏移 ⇒ 报 **平均偏差**（极差）' % len(OFFS))
print('   %-4s %-9s %s' % ('n', 't真值', '  '.join('%s' % CI[k] for k in ('L', 'P', 'S'))))
for n in (2, 3, 4, 5, 6, 8, 10, 12, 16):
    tt = n * dx
    acc = {k: [] for k in ('L', 'P', 'S')}
    for off in OFFS:
        pl = np.maximum(np.maximum(np.abs(gx) - A, np.abs(gy) - B),
                        np.abs(gz - off * dx) - tt / 2)
        rr, _ = measure(mk_psi(pl), AX)
        if rr is None:
            continue
        for k in acc:
            acc[k].append((rr[k][2] / tt - 1) * 100)
    if not acc['L']:
        print('   %-4d %-9.1f  （胞数不足）' % (n, tt * 1e9))
        continue
    cells = '  '.join('%+7.1f%%(%4.1f)' % (np.mean(acc[k]), np.ptp(acc[k]))
                      for k in ('L', 'P', 'S'))
    print('   %-4d %-9.1f %s' % (n, tt * 1e9, cells))
print('   ⇒ 判据：**平均偏差 |bias| ≤ 5% 且极差 ≤ 2 胞**才算量具合格；'
      '偏 T 一律在**最薄轴**上最差。')

# ---------------------------------------------------------------- Q-4 椭球
print('\n■ Q-4 椭球 3000×1500×800 nm（真值 = 最大跨度；体积比 π/6 = 0.5236）')
ell = (np.sqrt((gx / A) ** 2 + (gy / B) ** 2 + (gz / C) ** 2) - 1.0) * C
rr, _ = measure(mk_psi(ell), AX)
table('口径', rr, (A * 2, B * 2, C * 2))
ncell = int((ell < 0).sum())
Vc = ncell * dx ** 3
Vtrue = 4.0 / 3.0 * np.pi * A * B * C
print('   体积：离散 %.4e m³ vs 解析 %.4e m³ ⇒ **离散体积偏 %+.1f%%**（胞心判据的固有损失）'
      % (Vc, Vtrue, (Vc / Vtrue - 1) * 100))
print('=' * 108)
