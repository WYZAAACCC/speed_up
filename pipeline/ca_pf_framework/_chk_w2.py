#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W2（第二次重写）：平界面 + 常数驱动 ⇒ 界面速度应**精确等于** MΔf。

★ 判据口径第二次重写（本轮）：`region()` **计数法** ⇒ **亚胞射线交点**
  （`LevelSetMulti.iface_offset`，与 S1 的 `radius_rays` 同一口径）。为什么必须换：
    · 计数法在**均匀亚胞平移**下**失明**（推进 0.4·dx 不跨任何胞心 ⇒ 读数 0.000）；
    · 而平移恰为整数胞时它又**逐位精确**（旧版 40×0.1dx = 4dx 正是这种巧合）。
  两个极端都是**构型依赖**的 ⇒ 旧版判据没有分辨力。

★ 初值也必须重写（本轮）：旧的"半空间 SDF"（φ = z − z0）与**周期模板**自洽性冲突
  —— `_upwind_grad` 用 `np.roll`（周期 BC），而半空间 SDF **不是周期函数**：
  wrap 处跳变 47·dx ⇒ 该胞 |∇φ| 被算成 **47**（真值 1）⇒ 每步被推 4.7dx，
  3 步后凭空造出第二个界面（射线口径 n_cross 2304→4608）✗。
  周期自洽的初值是 **slab**（厚 a = N/2·dx，一列两个界面，wrap 跳变 = 1·dx = 真值 ✓）。

判据：射线口径 |v|/(MΔf) − 1| < 0.02。
对照：(a) 分辨力对照（总平移 0.4dx：射线 1.000、计数 0.000）；
      (b) 窄带 / 无扩展 / 半空间初值 / 阶跃初值 ⇒ 显著偏离。
"""
import numpy as np
from windowB_surface import LevelSetMulti


def _seed(N, dx, kind='slab'):
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=1e-9, df=[0.0, -1e7],
                      reinit_every=0)
    z = (np.arange(N)[None, None, :] + 0.5) * dx
    L = N * dx
    if kind == 'slab':                       # ★ 周期自洽
        a = (N // 2) * dx
        g.phi[1] = np.where(z <= a, -np.minimum(z, a - z),
                            np.minimum(z - a, L - z)) * np.ones((N, N, N))
        g.near0 = a
    elif kind == 'halfspace':                # ✗ 与周期模板冲突（负对照）
        g.phi[1] = (z - 0.25 * N * dx) * np.ones((N, N, N))
        g.near0 = 0.25 * N * dx
    else:                                    # 阶跃（退化构型）
        g.phi[1] = np.where(z < 0.25 * N * dx, -1e-9, 1e-9) * np.ones((N, N, N))
        g.near0 = 0.25 * N * dx
    g.init_parent()
    return g


def run(N=48, dx=2e-9, M=1e-9, df=1e7, nstep=40, band_cells=20, extend='edt',
        kind='slab', pair_kernel=False, iface_band=2.0, verb=False,
        per_field=False):
    """返回 (v_ray, v_cnt)：均为 |速度|/(MΔf)。"""
    g = _seed(N, dx, kind)
    near = g.near0
    _, z0 = g.iface_offset(1, 0, 2, near=near)
    c0 = int((g.region() == 1).sum())
    dt = 0.1 * dx / (M * df)
    for _ in range(nstep):
        g.advance(dt, extend=extend, band_cells=band_cells,
                  pair_kernel=pair_kernel, iface_band=iface_band,
                  per_field=per_field)
    _, z1 = g.iface_offset(1, 0, 2, near=near)
    c1 = int((g.region() == 1).sum())
    v_ray = abs(z1 - z0) / (nstep * dt) / (M * df)
    v_cnt = abs(c1 - c0) / float(N * N) * dx / (nstep * dt) / (M * df)
    if verb:
        d = g.phi[1] - g.phi[0]
        wrap = abs(d[N // 2, N // 2, 0] - d[N // 2, N // 2, N - 1]) / dx
        print('      [z0=%.4f z1=%.4f dx ; 计数层 %d->%d ; wrap跳变=%.1f dx]'
              % (z0 / dx, z1 / dx, c0 // (N * N), c1 // (N * N), wrap))
    return v_ray, v_cnt


if __name__ == '__main__':
    print('---- W2 平界面速度（口径 = 亚胞射线交点）----')
    r, c = run(verb=True)
    print('   周期 slab 初值 + EDT 扩展(20dx) : 射线 v/MDf = %.4f | 计数 = %.4f   %s'
          % (r, c, 'PASS' if abs(r - 1) < 0.02 else 'FAIL'))
    print('   判据：|v/MDf - 1| < 0.02（射线口径）')
    print('   --- 分辨力对照（总平移 0.4dx：射线应 1.0、计数应 0.0）---')
    r4, c4 = run(nstep=4, verb=True)
    print('   nstep=4 (0.4dx)        : 射线 %.4f | 计数 %.4f   %s'
          % (r4, c4, '射线有分辨力 OK' if abs(r4 - 1) < 0.02 and abs(c4) < 1e-9
             else '（意外）'))
    print('   --- 反向对照（射线口径）---')
    for tag, kw in (('窄带(2dx)', dict(band_cells=2)), ('无扩展', dict(extend=False)),
                    ('半空间初值(与周期模板冲突)', dict(kind='halfspace')),
                    ('阶跃初值(退化构型)', dict(kind='step'))):
        rr, _cc = run(**kw)
        print('   %-24s : 射线 %.4f   %s'
              % (tag, rr, 'X 偏离' if abs(rr - 1) > 0.02 else '（意外）'))
