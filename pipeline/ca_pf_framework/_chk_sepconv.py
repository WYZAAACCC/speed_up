#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_sepconv.py --- `_sep_conv3` 的单元测试（含正/负对照，`MEASUREMENT_SPEC R0`）。"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from scipy import ndimage                                       # noqa: E402
import windowB_surface as W                                     # noqa: E402

g = W.LevelSetMulti(16, 1e-6, gamma=0.15, Mob=1e-9, nv=1, df=[0.0, 1e8], reinit_every=0)
f = np.random.default_rng(0).normal(size=(16, 16, 16))
ok = []
for m in (1, 2, 3):
    k = np.ones(2 * m + 1) / (2 * m + 1)
    o = g._sep_conv3(f, k)
    ref = ndimage.uniform_filter(f, 2 * m + 1, mode='wrap')
    ok.append(np.allclose(o, ref, atol=1e-12))
    print('m=%d  shape=%s  finite=%s  vs scipy.uniform_filter(wrap) 逐位一致=%s  最大差=%.2e'
          % (m, o.shape, np.isfinite(o).all(), ok[-1], np.abs(o - ref).max()))
print('正对照（常值场不变）:', np.allclose(g._sep_conv3(np.ones((16, 16, 16)), np.ones(3) / 3), 1.0))
print('负对照（不平滑 ⇒ 必须与本函数不同）:',
      not np.allclose(g._sep_conv3(f, np.ones(3) / 3), f))
print('⇒ `_sep_conv3` %s' % ('PASS' if all(ok) else 'FAIL'))
sys.exit(0 if all(ok) else 1)
