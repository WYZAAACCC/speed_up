#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_w8b.py --- W-8b：盒子 B 的 **Delta x 收敛**（同一物理盒子 L=20 µm，两种分辨率）。

设计（关键：三次运行的**物理设置完全相同**，只有 Delta x 变）：
  * 晶核表在**物理坐标**里生成（同一 rng、同一位置/尺寸/变体）⇒ 两种分辨率看到同一初始组织；
  * **同一物理时间**：CFL 给出 dt ∝ dx（每步位移恒为 0.15 dx）⇒ 取 nstep ∝ 1/Delta x；
  * 观测量：f_trans、板片厚 t = 2f/S_v（coarea 几何测度）、12 变体均分度。
判据：W8b-1 |t(0.25 µm) - t(0.5 µm)| / t(0.25 µm) < 0.30（一阶界面 + 几何测度的量级容差）；
      W8b-2 |f(0.25) - f(0.5)| < 0.05；
      W8b-3 记账：变体均分度也随分辨率收敛。
"""
import sys

import numpy as np

import windowB_surface as W

L_PHYS = 20.0e-6          # 盒子 20 µm（用户批准的盒子 B 尺度）
DF = 1e8
NSEED, R_PHYS = 12, 0.22 * 4.0e-6      # 12 个晶核、R = 0.88 µm（与冒烟算例同族）
T_TARGET = 25 * 0.15 * 0.25e-6 / (1e-9 * DF)   # 以 dx=0.25 µm、25 步为基准的物理时间


def nuclei():
    rng = np.random.default_rng(3)
    out = []
    for _ in range(NSEED):
        c = rng.random(3) * (L_PHYS - 2 * R_PHYS) + R_PHYS
        out.append((c, int(rng.integers(1, 13))))
    return out


def run(dx):
    N = int(round(L_PHYS / dx))
    nsteps = int(round(T_TARGET / (0.15 * dx / (1e-9 * DF))))
    o = W.M2_twelve_variants(N=N, nstep=max(nsteps, 4), dx=dx, df=DF, quiet=True)
    f = o['f_trans']
    t = 2 * f / max(o['S_v_geom'], 1e-30)
    v = np.asarray(o['v_abs'], float)[1:]
    return dict(N=N, dx=dx, nstep=max(nsteps, 4), f=f, t=t, band=o['band'],
                ok=o['band_ok'], unif=float(v.max() / max(v.min(), 1e-30)),
                Sv=o['S_v_geom'])


print('==== W-8b 盒子 B 的 Delta x 收敛（L=20 µm，同一物理时间 %.2e s）====' % T_TARGET)
res = [run(0.5e-6), run(0.25e-6)]
for r in res:
    print('   dx=%.2f um  N=%3d  nstep=%3d : f=%.4f  t=%.3f um  band=%6d ok=%d 均分度=%.2f'
          % (r['dx'] * 1e6, r['N'], r['nstep'], r['f'], r['t'] * 1e6, r['band'], r['ok'], r['unif']))
a, b = res[0], res[1]
dt = abs(b['t'] - a['t']) / max(b['t'], 1e-30)
df_ = abs(b['f'] - a['f'])
du = abs(b['unif'] - a['unif']) / max(b['unif'], 1e-30)
print('   相对差: 板片厚 %.1f%% ; f %.4f ; 均分度 %.1f%%' % (100 * dt, df_, 100 * du))
print('   W8b-1 板片厚对 Delta x 收敛（<30%%）: %s' % ('PASS' if dt < 0.30 else 'FAIL'))
print('   W8b-2 f 对 Delta x 收敛（<0.05）: %s' % ('PASS' if df_ < 0.05 else 'FAIL'))
print('   W8b-3 记账：均分度相对差 %.1f%%（不设门槛）' % (100 * du))
