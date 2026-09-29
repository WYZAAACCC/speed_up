"""_bkr_guard.py —— 核对**当前工作区**的 windowB_surface.py 是否已加 de=0 守卫。

背景：审查期间（2026-09-29 16:57）工作区出现了并发改动（+50 行，R-block 实现）。
本脚本回答两个问题：
  1) 当前工作区里 `_pair_normals` 对同变体对（de=0）是给 NaN 还是给垃圾向量？
  2) 给了 NaN 之后，`facet_nref` 是否回退到 `npref`，F3 的 M_eff 是否回到 exp(-3.5)？
"""
import hashlib
import os
import sys
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

src = os.path.join(HERE, 'windowB_surface.py')
print('当前 windowB_surface.py sha256 = %s'
      % hashlib.sha256(open(src, 'rb').read()).hexdigest())
print('（BLOCK_DERIVATION.md 所在提交 b00914f6 冻结的引擎 sha256 = '
      '89ec9471…；归档 _exp/e4_lath6/meta.json 记录的也是这一个）')

import windowB_surface as W                                      # noqa: E402
from windowB_pf3d import C_cubic, argmin_normal                  # noqa: E402
from windowB_ti64_variants import variants                       # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NPF = {v + 1: argmin_normal(C, np.asarray(EPS0[v], float))[0]
       for v in range(len(EPS0))}

g = W.LevelSetMulti(8, 8e-8, C=C, eps0=[EPS0[0], EPS0[0]], gamma=0.15,
                    Mob=1e-9, workers=1)
print('\n1) ncmp[1,2] = %s   finite=%s' % (g.ncmp[1, 2], np.isfinite(g.ncmp[1, 2]).all()))
out = np.asarray(g.facet_nref(1, np.array(2), NPF)).reshape(-1, 3)[0]
print('2) facet_nref(1, larr=2) = %s' % out)
print('   npref[1]               = %s' % NPF[1])
print('   ⇒ %s' % ('回退到 npref ✓（守卫已生效）'
                   if np.allclose(out, NPF[1]) else
                   '**没有**回退（仍是 de=0 退化解）✗'))
n_g = np.array([0.00999987, 0.0, 0.99995])
n1 = NPF[1] / np.linalg.norm(NPF[1])
print('\n3) 对 F3 的惯习面法向 n*_1：')
print('   若用垃圾向量：M_eff/M0 = exp(-3.5*(n*·n_g)^2) = %.4f' % math.exp(-3.5 * float(n1 @ n_g) ** 2))
print('   若回退 npref：M_eff/M0 = exp(-3.5*1)        = %.4f（= 文档 §6.6 假设值）'
      % math.exp(-3.5))
