#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g2_diag.py —— 诊断 G2 单元测试 P5（"纯母相"却返回 iface）的根因。"""
import inspect
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N = 8
g = WS.LevelSetMulti(N, 1.0, nv=4, gamma=0.0, Mob=1.0)
reg = np.zeros((N, N, N), np.int16)
reg[:, :, :4] = 1
reg[:, :, 4:] = 2

cp = np.zeros((N, N, N), bool)
cp[0, 0, 0] = True

print("签名:", inspect.signature(g._test_stack_iface_ok))
print("cover 形状/类型:", cp.shape, cp.dtype, " True 个数:", int(cp.sum()))
print("reg[cp] =", reg[cp], " dtype:", reg[cp].dtype)
print("(reg[cp]==0).all() =", bool((reg[cp] == 0).all()))
print("np.unique(reg[cp]) =", np.unique(reg[cp]))

# ⚠ 关键怀疑：位置参数顺序。签名是 (cover, reg, k_new, vmap)
ret = g._test_stack_iface_ok(cp, reg, 3, {1: 1, 2: 4, 3: 2, 4: 3})
print("直接调用（cp, reg, 3, VM）= ", ret)

# 用关键字调用，排除顺序问题
ret2 = g._test_stack_iface_ok(cover=cp, reg=reg, k_new=3, vmap={1: 1, 2: 4, 3: 2, 4: 3})
print("关键字调用               = ", ret2)
