#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r563_wrapdiag.py --- 记账器"没挂上"的最小复现（先修量具，再谈结论）。

`_r561` 的表里 `region()/argmin2()/elastic_*()` 全是 **0 次**，而 `_minmod` 有 24 次。
两种可能：
  (a) 我的 `_wrap` 对**类方法**没生效（量具 bug）；
  (b) `advance()` 真的没走那条路（引擎 bug）。
本脚本用**最小可判定**的方式分开它们：先看 `__wrapped__` 标记是否挂上，
再直接调一次 `g.region()` 看计数器动不动。**正对照**：同一套 `_wrap` 用到模块函数上，
它必须动（`_r561` 里 `_minmod` 动过 ⇒ 说明机制本身没问题）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
import windowB_pf3d as P3                                      # noqa: E402
import windowB_par as PAR                                      # noqa: E402

CNT = {}


def _wrap(cls, name, tag):
    orig = getattr(cls, name)

    def _f(*a, **kw):
        CNT[tag] = CNT.get(tag, 0) + 1
        return orig(*a, **kw)
    _f.__name__ = name
    _f.__r563_tag = tag
    setattr(cls, name, _f)
    return orig


L = []
A = L.append

A('  type(LevelSetMulti) = %s   module=%s' % (W.LevelSetMulti, W.LevelSetMulti.__module__))
_orig_region = _wrap(W.LevelSetMulti, 'region', 'region')
A('  挂上后 W.LevelSetMulti.region 有 __r563_tag? %s'
  % getattr(W.LevelSetMulti.region, '__r563_tag', None))
A('  PAR.ParCtx.argmin2 挂上: %s'
  % getattr(_wrap(PAR.ParCtx, 'argmin2', 'argmin2'), '__name__', None))

eps = [np.asarray(np.eye(3) * 0.01 * (-1) ** i, float) for i in range(6)]
try:
    from T16_verify_rve import C, EPS0
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(6)]
    A('  用 T16_verify_rve 的 C/EPS0')
except Exception as e:
    A('  T16 导入失败(%s)，用玩具 eps0' % e)

g = W.LevelSetMulti(16, 1.0, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                    df=[0.0] + [3.0e8] * 6, workers=4, reinit_every=20,
                    reinit_dt=1e-4, reinit_band_cells=6.0, phi_prec='f64')
g.init_parent()
A('  type(g) = %s' % type(g))
A('  type(g).region is W.LevelSetMulti.region ? %s' % (type(g).region is W.LevelSetMulti.region))
A('  type(g.par) = %s   module=%s' % (type(g.par), type(g.par).__module__))
A('  type(g.par) is PAR.ParCtx ? %s' % (type(g.par) is PAR.ParCtx))

n0 = CNT.get('region', 0)
r = g.region()
A('  直接调 g.region() → 计数 %d → %d   ⇒ %s'
  % (n0, CNT.get('region', 0),
     '✅ 类方法挂得上（_r561 的 0 是**引擎没走那条路**）'
     if CNT.get('region', 0) > n0 else '❌ 类方法挂不上（量具 bug）'))

n1 = CNT.get('argmin2', 0)
try:
    g.par.argmin2(g.phi)
except Exception as e:
    A('  argmin2 调用异常: %r' % (e,))
A('  直接调 g.par.argmin2() → 计数 %d → %d   ⇒ %s'
  % (n1, CNT.get('argmin2', 0),
     '✅' if CNT.get('argmin2', 0) > n1 else '❌'))

A('')
A('  === 现在跑一步真 advance，看它到底调了什么 ===')
for kk in list(CNT):
    del CNT[kk]
# 把**所有**候选都挂上（含 advance 自己）
for nm in ('region', 'elastic_driving', 'elastic_driving_pair', '_finish_advance',
           'reinitialize', 'advance', '_advance_perfield', 'nucleate'):
    if hasattr(W.LevelSetMulti, nm):
        _wrap(W.LevelSetMulti, nm, nm)
for nm in ('argmin2', 'argmin', 'gradient', 'upwind_flux_vec', 'for_each', 'map0',
           'map0_two'):
    if hasattr(PAR.ParCtx, nm):
        _wrap(PAR.ParCtx, nm, 'par.' + nm)
_o = {}
for nm in ('upwind_flux_vec', 'upwind_grad2', 'upwind_grad', '_minmod', '_bbox_pad'):
    if hasattr(W, nm):
        setattr(W, nm, _wrap(type('M', (), {}), nm, 'mod.' + nm)) if False else None
# 模块函数用同样的手法
def _wrapmod(mod, name):
    orig = getattr(mod, name)

    def _f(*a, **kw):
        CNT['mod.' + name] = CNT.get('mod.' + name, 0) + 1
        return orig(*a, **kw)
    _f.__name__ = name
    setattr(mod, name, _f)
_wrapmod(W, 'upwind_flux_vec')
_wrapmod(W, '_minmod')
_wrapmod(P3.PF3D, 'eps0_fields')
_wrapmod(P3.PF3D, 'sigma_tensor')

g.advance(dt=1e-8)
for k in sorted(CNT):
    A('    %-28s %5d' % (k, CNT[k]))

A('')
A('  关键判定：')
got = {k: CNT.get(k, 0) for k in ('region', 'argmin2', 'elastic_driving',
                                  'elastic_driving_pair', 'par.argmin2',
                                  'par.for_each', 'sigma_tensor')}
A('    %s' % got)
A('  ⇒ %s' % ('✅ advance 确实调了 region/argmin2（那么 _r561 的 0 是**时序**问题）'
              if got['region'] > 0 else '❌ advance 一步里 region 计数仍为 0'))

out = '\n'.join(L)
print(out)
with open(os.path.join(HERE, '_w2_r563_wrapdiag.log'), 'w', encoding='utf-8') as fh:
    fh.write(out + '\n')
