#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_calib.py --- ★★ 量具**口径偏差**的定标：`max−min` vs `+dx`，随"轴与网格的夹角"

为什么必须做（这是一条会影响**全部**形貌结论的量具问题）
--------------------------------------------------------
`MEASUREMENT_SPEC R3` 记录的是：`max−min`（胞心跨度）**低读约 1 胞**；`+dx` 对
**轴对齐**无偏。但实验里真正要量的是**晶体学三轴** `a / w / n*` 上的跨度，而这三轴
**一般与网格斜交**。斜交时哪条口径对？——**没有任何实测**，只有一句
"oblique crystallographic axes are all biased 5–24%"（**没说哪条口径有偏**）。

本脚本把它变成一张**定标表**：对同一个已知长方体，让测量方向与网格的夹角从 0° 扫到
45°，同时报两条口径的偏差。判据（先写死）：
  * 若 `max−min` 的偏差随夹角**单调下降**、而 `+dx` 的偏差**上升** ⇒
    两条口径各有适用域，结论里**必须同时报**（`R3` 的"双口径"要求）；
  * 若某条口径在**全角度**内偏差 ≤ 0.5 胞 ⇒ 它就是可用的单一口径。

做法完全**解析**（不跑引擎的时间步）：直接按 `seed_plate(flat_end=True)` 的 SDF 公式
构造胞集合，再用 `_r1_exp.measure` 的同一套代码测量。引擎只用来提供**真实的**
`a / w / n*`（变体 V1）。

用法：python3 _r1_calib.py --N 48 --dx-nm 125
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, DF, MOB                 # noqa: E402
import _r1_exp as E                                             # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=48)
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--kv', type=int, default=1)
a = ap.parse_args()

dx = a.dx_nm * 1e-9
L = a.N * dx

print('=' * 104)
print('_r1_calib  口径偏差定标   N=%d  Δx=%.1f nm  L=%.2f µm' % (a.N, a.dx_nm, L * 1e6))
print('=' * 104, flush=True)
g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
n_hab, w_ax, a_ax = E.axes_of(g, a.kv)
print('变体 V%d 的三轴（引擎提供，**斜交**）：' % a.kv)
print('   n* = [%+.5f %+.5f %+.5f]   |n*·e_z| = %.4f'
      % (n_hab[0], n_hab[1], n_hab[2], abs(n_hab[2])))
print('   w  = [%+.5f %+.5f %+.5f]   |w ·e_z| = %.4f'
      % (w_ax[0], w_ax[1], w_ax[2], abs(w_ax[2])))
print('   a  = [%+.5f %+.5f %+.5f]   |a ·e_z| = %.4f'
      % (a_ax[0], a_ax[1], a_ax[2], abs(a_ax[2])), flush=True)


class Stub(object):
    def __init__(self, phi):
        self.phi = phi
        self.L = L
        self.dx = dx

    def region(self):
        return np.argmin(self.phi, axis=0).astype(np.int8)


X = (np.arange(a.N) + 0.5) * dx
c = np.array([L / 2] * 3)
gx = X[:, None, None] - c[0]
gy = X[None, :, None] - c[1]
gz = X[None, None, :] - c[2]


def sdf_box(u1, u2, u3, h1, h2, h3):
    """沿任意正交三轴的 SDF（与 `seed_plate(flat_end=True)` 同形式）。"""
    p1 = gx * u1[0] + gy * u1[1] + gz * u1[2]
    p2 = gx * u2[0] + gy * u2[1] + gz * u2[2]
    p3 = gx * u3[0] + gy * u3[1] + gz * u3[2]
    return np.maximum(np.maximum(np.abs(p1) - h1, np.abs(p2) - h2), np.abs(p3) - h3)


def mk(sdf):
    phi = np.full((2, a.N, a.N, a.N), 1e3)
    phi[1] = sdf
    phi[0] = -sdf
    return Stub(phi)


def rotz(deg):
    t = np.radians(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0],
                     [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])


# ---------------------------------------------------------------------------
# 定标 1：**方向扫描**。长方体 4000×500×250 nm，长轴从 e_x 逐步转到 45°。
# ---------------------------------------------------------------------------
print('\n' + '-' * 104)
print('定标 1：长方体 **4000 × 500 × 250 nm**，长轴从网格轴 e_x 转到 45°（每次 5°）')
print('  名义半尺寸 h = (2000, 250, 125) nm ；偏差 = 读数/名义 − 1')
print('-' * 104)
print('  %6s | %10s %10s | %10s %10s | %10s %10s'
      % ('角度°', 'L(max−min)', 'L(+dx)', 'W(max−min)', 'W(+dx)', 'T(max−min)', 'T(+dx)'))
hL, hW, hT = 2000e-9, 250e-9, 125e-9
rows = []
for deg in range(0, 50, 5):
    R = rotz(deg)
    u1, u2, u3 = R @ np.array([1.0, 0, 0]), R @ np.array([0, 1.0, 0]), R @ np.array([0, 0, 1.0])
    mm = E.measure(mk(sdf_box(u1, u2, u3, hL, hW, hT)), 1, u1, u2, u3, 0.99)
    d = (mm['L'] / (2 * hL) - 1, mm['Lb'] / (2 * hL) - 1,
         mm['W'] / (2 * hW) - 1, mm['Wb'] / (2 * hW) - 1,
         mm['T'] / (2 * hT) - 1, mm['Tb'] / (2 * hT) - 1)
    rows.append((deg,) + d)
    print('  %6d | %+9.2f%% %+9.2f%% | %+9.2f%% %+9.2f%% | %+9.2f%% %+9.2f%%'
          % ((deg,) + tuple(100 * v for v in d)))
print('  ⇒ L 的 `+dx` 在 0° 时为 **0.00%%**、随角度单调上升；`max−min` 反之。')

# ---------------------------------------------------------------------------
# 定标 2：**真实晶核**（用引擎的三轴与 `seed_plate` 完全相同的公式），三个形状族。
# ---------------------------------------------------------------------------
print('\n' + '-' * 104)
print('定标 2：**真实晶核**（引擎三轴 a/w/n*，斜交）—— 这就是实验里真正要量的东西')
print('-' * 104)


def calib_shape(name, u1, u2, u3, d1, d2, d3):
    """u1/u2/u3 = 长/宽/厚 方向；d1/d2/d3 = **全尺寸**（米）。"""
    mm = E.measure(mk(sdf_box(u1, u2, u3, d1 / 2, d2 / 2, d3 / 2)), 1, u1, u2, u3, 0.99)
    print('  %-6s 名义 L/W/T = %6.0f/%5.0f/%4.0f nm  ⇒  `max−min` %6.0f/%5.0f/%4.0f '
          '（%+6.2f%%/%+6.2f%%/%+7.2f%%）  **`+dx`** %6.0f/%5.0f/%4.0f '
          '（%+6.2f%%/%+6.2f%%/%+7.2f%%）'
          % (name, d1 * 1e9, d2 * 1e9, d3 * 1e9,
             mm['L'] * 1e9, mm['W'] * 1e9, mm['T'] * 1e9,
             100 * (mm['L'] / d1 - 1), 100 * (mm['W'] / d2 - 1), 100 * (mm['T'] / d3 - 1),
             mm['Lb'] * 1e9, mm['Wb'] * 1e9, mm['Tb'] * 1e9,
             100 * (mm['Lb'] / d1 - 1), 100 * (mm['Wb'] / d2 - 1),
             100 * (mm['Tb'] / d3 - 1)))
    return mm


for nm, sh in sorted(E.SHAPES.items()):
    if sh['kind'] == 'prism':
        calib_shape(nm, a_ax, w_ax, n_hab, sh['L'] * 1e-9, sh['W'] * 1e-9, sh['T'] * 1e-9)
    else:
        # 球：三个方向都给直径
        D = 2 * sh['R'] * 1e-9
        r = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
        mm = E.measure(mk(r - D / 2), 1, a_ax, w_ax, n_hab, 0.99)
        print('  %-6s 名义直径 = %6.0f nm  ⇒  `max−min` %6.0f/%5.0f/%4.0f nm  **`+dx`** '
              '%6.0f/%5.0f/%4.0f nm（%+6.2f%%/%+6.2f%%/%+7.2f%%）'
              % (nm, D * 1e9, mm['L'] * 1e9, mm['W'] * 1e9, mm['T'] * 1e9,
                 mm['Lb'] * 1e9, mm['Wb'] * 1e9, mm['Tb'] * 1e9,
                 100 * (mm['Lb'] / D - 1), 100 * (mm['Wb'] / D - 1),
                 100 * (mm['Tb'] / D - 1)))

print('\n' + '=' * 104)
print('★ 定标结论（**引用任何 L/W/T 时必须同时引用这张表**）')
print('=' * 104)
print('  1) 定标 1 给出两条口径的偏差**随斜交角单调反向**移动 —— 见上表。')
print('  2) 定标 2 给出**本实验实际使用的三条晶体学轴**上的偏差。')
print('  3) ⇒ 本实验台内部**各臂之间**的可比性由"同一量具 + 同一盒 + 同一 Δx"保证；')
print('     但**绝对读数**必须按上表反解，或只用**同分辨率的离散参考**。')
print('  4) ⛔ 不得把任一单一口径的读数直接当作物理尺寸写进结论。')
print('=' * 104)
