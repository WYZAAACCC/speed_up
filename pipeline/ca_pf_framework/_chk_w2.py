#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W2（重写）：平界面 + 常数驱动 ⇒ 界面速度应**精确等于** MΔf（验证配对一致更新 + 速度标定）。

★ 为什么要重写（本轮发现）：旧版用"阶跃初值"（φ=±0.5dx ⇒ 体相 |∇φ|=0），那不是 VDF/SDF 的
  合法构型；同一份代码在阶跃初值下给 v/MΔf = 2.0、在**真 SDF** 初值下给 0.25（窄带）
  ⇒ 当年报的 1.0000 是**构型依赖的巧合**，判据本身不可用。
  现在：真 SDF 初值 + 宽带扩展（`band_cells=20`）⇒ 1.0000（实测见 `_chk_w2.py` 输出）。

判据：|v_实测/(MΔf) − 1| < 0.02；并给反向对照（窄带/无扩展 ⇒ 显著偏离）。
"""
import numpy as np
from windowB_surface import LevelSetMulti

def run(N=48, dx=2e-9, M=1e-9, df=1e7, nstep=40, band_cells=20, extend='edt',
        sdf=True):
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M, df=[0.0, -df], reinit_every=0)
    z = np.arange(N)[None, None, :] * dx
    if sdf:
        g.phi[1] = (z - 0.25 * N * dx) * np.ones((N, N, N))     # 真 SDF
    else:
        g.phi[1] = np.where(z < 0.25 * N * dx, -1e-9, 1e-9) * np.ones((N, N, N))
    g.init_parent()
    n0 = int((g.region() == 1).sum())
    dt = 0.1 * dx / (M * df)
    for _ in range(nstep):
        g.advance(dt, extend=extend, band_cells=band_cells)
    n1 = int((g.region() == 1).sum())
    x_meas = abs(n1 - n0) * dx ** 3 / (N * dx) ** 2
    return x_meas / (nstep * dt) / (M * df)

print('---- W2 平界面速度（配对一致 + 速度标定）----')
r = run()
print('   真 SDF 初值 + 宽带扩展(band=%ddx) : v/MΔf = %.4f   %s'
      % (20, r, 'PASS' if abs(r - 1) < 0.02 else 'FAIL'))
print('   判据：|v/MΔf − 1| < 0.02')
print('   --- 反向对照（说明判据有分辨力）---')
for tag, kw in (('窄带(2dx)', dict(band_cells=2)), ('无扩展', dict(extend=False)),
                ('阶跃初值(退化构型)', dict(sdf=False))):
    rr = run(**kw)
    print('   %-20s : v/MΔf = %.4f   %s' % (tag, rr, '✗ 偏离' if abs(rr - 1) > 0.02 else '（意外）'))