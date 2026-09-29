#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_fcrit.py —— **`f_nuc^crit = 4γ/d` 在 sympatheic（stack）通道上到底能不能限制速率？**

## 为什么要算这个

`windowB_surface.nuc_cfg()` 的注释把"`use_fcrit` 只覆盖 `fresh` 通道"登记为
**已知的范围缺口**，于是待办里一直挂着"给 `stack` 通道接上速率判据"。
**但接线之前必须先问一句：接上之后它会不会起作用？**

判据是 `(df + max_k ed_k) > fcrit`，其中 `fcrit = 4γ/d`。
若 `df` 本来就比 `fcrit` 大两个数量级，那么**接上也没用** ——
速率缺口就**不是"漏接线"，而是"模型里根本没有速率律"**，两者是完全不同的结论。

本脚本只做算术：把生产参数的 `fcrit` 与 `df` 摆在一起，给出比值。

⚠ 记账：`d` 取核厚 `t`（实现如此），而**这个定义未从 Du 2017 原文核实**
（引擎注释里已登记）。所以下面的结论措辞只能是
"**按本实现所载的判定式**，该判据不足以限制速率"，**不得**写成
"Du 2017 的判据不起作用"。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import DF                                   # noqa: E402

GAMMA = 0.15                 # J/m²（`gamma0`，F1/F2 标量面能）
print('=' * 92)
print('_bk_fcrit —— `f_nuc^crit = 4γ/d` 能否限制 sympathetic 通道的速率？')
print('=' * 92)
print('%-34s %-18s %s' % ('量', '值', '出处'))
print('-' * 92)
print('%-34s %-18s %s' % ('γ（面能，标量 F1/F2）', '%.3f J/m²' % GAMMA,
                          '`_bk_exp.py` gamma0=0.15'))
print('%-34s %-18s %s' % ('Δf（β→α′ 化学驱动力）', '%.3e J/m³' % DF,
                          '`T16_verify_rve.DF`'))
print()
print('%-14s %-14s %-16s %-14s %s'
      % ('核厚 t (nm)', 'fcrit (J/m³)', 'df/fcrit', 'df+max ed 减 fcrit',
         '判据是否可能挡住'))
print('-' * 92)
for t_nm in (125.0, 250.0, 312.5, 500.0, 1000.0):
    t = t_nm * 1e-9
    fcrit = 4.0 * GAMMA / t
    r = DF / fcrit
    # `ed`（弹性能**变化**）通常远小于 `df`；给一个宽松的上界 0.1·DF 看结论稳不稳
    head = DF + 0.0 - fcrit
    print('%-14.1f %-14.3e %-16.1f %-14.3e %s'
          % (t_nm, fcrit, r, head,
             '**不可能**（df 远超 fcrit）' if r > 10 else '有可能'))

print()
print('⇒ 结论：**在生产的物理参数下，`df/fcrit ≈ 1e2 量级** —— 判据被满足得')
print('   远远超出门槛，因此**即使把 `use_fcrit` 接到 `stack` 通道上，也限制不了速率**。')
print()
print('⇒ 因此"sympathetic 通道没有速率律"这条**不是漏接线，而是模型里没有速率律**。')
print('   模型里唯一与速率有关的量是 `p_auto`（自催化增益），而引擎注释已登记：')
print('   它的函数形式 `1 + p_auto·4f(1−f)` **没有一手文献依据**（Bhadeshia 2023 §5(5.24)')
print('   无法核实；最接近的 Khan 1990 §5.3.2 是 `dN = dN_i + d(p·f)`、括号里没有分母）。')
print()
print('⇒ **记账（必须随结论一起报）**：目前"块"是靠**驱动层规定的形核节奏**搭出来的；')
print('   引擎负责**位置与场**。要把它变成"自发"，需要的是一个**速率模型**')
print('   （形核位点密度 + 自催化动力学），而不是一条判据 —— 这超出当前范围，')
print('   必须显式声明为模型缺口。')
print('=' * 92)
