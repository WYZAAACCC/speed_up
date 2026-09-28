#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_chk.py --- 语法 + 导入 + 快速冒烟（改完引擎后的第一道闸）"""
import os
import sys
import ast

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

for fn in ('windowB_surface.py', 'windowB_par.py', '_r1_exp.py', '_r1_calib.py',
           '_r1_smoke.py'):
    p = os.path.join(HERE, fn)
    try:
        ast.parse(open(p, encoding='utf-8').read())
        print('  syntax OK  %s' % fn)
    except SyntaxError as e:
        print('  ✗ SYNTAX ERROR %s : %s' % (fn, e))
        sys.exit(1)

import numpy as np
import windowB_surface as W
import windowB_par as P
print('  import OK  numpy %s' % np.__version__)

# 子盒与全域必须**逐位相同**（这是 bbox 加速的正确性门槛）
rng = np.random.default_rng(0)
N = 48
phi = rng.standard_normal((N, N, N))
# 造一个"带"：以中心球面为界
X = (np.arange(N) + 0.5) / N - 0.5
gx, gy, gz = X[:, None, None], X[None, :, None], X[None, None, :]
r = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
sdf = (r - 0.25) * (1.0 / N)
sdf = sdf + 0.05 * rng.standard_normal((N, N, N)) * (np.abs(sdf) < 0.06)
dx = 1.0 / N

for nth in (1, 3):
    p = P.ParCtx(nth)
    for it in (3, 12):
        full = W.sussman_reinit(sdf.copy(), dx, iters=it, band_cells=6.0, par=p)
        bb = W._band_bbox(sdf, 6.0, dx, 4)
        sub = W.sussman_reinit(sdf.copy(), dx, iters=it, band_cells=6.0,
                               bbox=bb, par=p)
        # 只比"带内"（回写本来只改带内；带外因子盒路径不动而全域路径可能动）
        m = np.abs(sdf) <= 6.0 * dx
        same_band = np.array_equal(
            np.ascontiguousarray(full[m]).view(np.uint8),
            np.ascontiguousarray(sub[m]).view(np.uint8))
        dmax = float(np.max(np.abs(full[m] - sub[m])))
        # 全域路径在带外改了没有？
        outside_changed = float(np.max(np.abs(full[~m] - sdf[~m])))
        print('  nth=%d iters=%-3d  bbox=%s  带内逐位相同=%-5s (max|Δ|=%.3e)  '
              '全域路径带外变化=%.3e'
              % (nth, it, tuple(s.stop - s.start for s in bb), same_band, dmax,
                 outside_changed))
    p.close()
print('CHK DONE')
