#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_dt.py --- 核实 Round 17 里用来判断"碰撞到不到得了"的 `dt` 与每步位移。

Round 17 报告里我写：`dt = 0.15×50nm/(1e-9×3.5e8) = 2.14e-9 s`、每步位移 **0.43 nm**
⇒ 碰撞需 ~1160 步 ⇒ ~12 h ⇒ "碰撞不可达"。**这里把每一步算清楚。**
"""
import numpy as np

dx = 50e-9
M = 1e-9
DF = 3.5e8
v = M * DF                       # m/s
dt = 0.15 * dx / v               # s（T13b/T16 用的就是这一式）
disp = v * dt                    # m/步

print('=' * 88)
print('_chk_dt —— Round 17 的 dt 核算')
print('=' * 88)
print('  M·Δf         = %.4g × %.4g = %.6g m/s' % (M, DF, v))
print('  0.15·Δx      = %.4g m' % (0.15 * dx))
print('  dt           = 0.15Δx/(MΔf) = **%.6g s**' % dt)
print('  每步位移     = v·dt = **%.6g m = %.3f nm**' % (disp, disp * 1e9))
print('-' * 88)
print('  Round 17 我写的是 dt=2.14e-9 s、位移 0.43 nm ⇒ **差 10×**（10 的幂写错了一位）。')
print('  正确：dt = %.3g s、位移 = %.1f nm/步（= 0.15Δx，本来就是按 CFL 定的）。'
      % (dt, disp * 1e9))
print('-' * 88)
print('  ⇒ 碰撞所需的步数（面内半径 300 nm → d/2=800 nm，ΔR=500 nm）：')
print('     名义（全速面内生长）      : %.0f 步' % (500e-9 / disp))
print('     实测修正（有效速度约名义 1/3）: %.0f 步  ← T13b 实测 f 的增长率反推' % (3 * 500e-9 / disp))
print('  ⇒ 按实测步时 38 s ⇒ **%.1f h / 档**（不是 Round 17 说的 12 h）。'
      % (3 * 500e-9 / disp * 38 / 3600))
print('=' * 88)
print('  ⇒ **结论修正**：碰撞（impingement）**并非不可达**，只是需要 ~200 步/档、~2 h。')
print('     Round 17 的"三结果汇聚"里，**来自 T13b 的那一条（碰撞不可达）作废**；')
print('     B3（AR≈晶核 AR）与 T15（Wulff 不可达）两条**不受影响**。')
print('=' * 88)
