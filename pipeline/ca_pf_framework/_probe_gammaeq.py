#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_gammaeq.py —— 探针：`Gamma_eq` 是不是**静默返回 0**（`except Exception` 吞掉）？

动机：T4 的对照档 `max|Γ_mol| = 0`，若 `Gamma_eq ≡ 0` 则 `update_Gamma` 的
      "局部平衡交换"永远不动 ⇒ **界面化学通道其实早就名存实亡**，
      而"k_part=0.6303 造成分配"这一说法也就站不住（Stefan 改了立刻被 undo）。
正对照：直接算 `gamma_eq_langmuir(0.036, T, H)`，非零才说明参数链是活的。
"""
import os
import sys
import traceback

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

g = W.LevelSetMulti(16, 16 * 2e-9, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, -1e8])
c = np.full((16, 16, 16), 0.036)
Geq = g.Gamma_eq(c)
print('g.T = %.2f K' % g.T)
print('Gamma_eq(0.036): mean=%.6e  max|.|=%.6e' % (float(Geq.mean()), float(np.abs(Geq).max())))

print('\n--- 直接走 gibbs_physics（正对照）---')
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gibbs'))
try:
    from gibbs_physics import gamma_eq_langmuir, dH_seg_from_anchor
    H, extra = dH_seg_from_anchor()
    print('import OK;  H = %r  extra = %r' % (H, extra))
    for cc in (0.01, 0.036, 0.10):
        print('   gamma_eq_langmuir(%.3f, %.1f, H) = %.6e' % (cc, g.T, gamma_eq_langmuir(cc, g.T, H)))
except Exception:
    print('!! gibbs_physics 不可用 —— 这正是 Gamma_eq 静默返回 0 的原因：')
    traceback.print_exc()

print('\n--- 再走一次 Gamma_eq，看是否仍为 0（缓存/module 已在 sys.modules 里）---')
Geq2 = g.Gamma_eq(c)
print('Gamma_eq 第二次: max|.|=%.6e' % float(np.abs(Geq2).max()))
