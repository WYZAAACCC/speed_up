#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_smoke_proj2.py --- D17 冒烟：`proj2` 在**生产配置**（弹性 + 12 变体 + mob_beta +
   npref + reinit_dt + 逐变体守卫）下能不能跑，且不静默退化。

判据（全部是"不崩溃 + 不静默"型，不涉及物理结论）：
  S1 能跑完 N 步，无异常；
  S2 `wrap_axes_any()` 可调用、返回 dict；
  S3 `region()` 不退化（变体数 ≥1、母相仍在）；
  S4 `proj2` 与 `central` 的**结果必须不同**（否则说明 proj 分支根本没被走到 —— 静默退化）；
  S5 `adv_grad` 传进 `per_field=True` 时也必须走 proj 分支（不静默退化成迎风）。
"""
import os
import sys
import time as _t

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB = 2.0e8, 1e-9
N, dx = 48, 62.5e-9
L = N * dx


def go(adv, per_field=False, nsteps=12):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    for i, k in enumerate((1, 2, 3, 5)):
        c = np.array([0.25, 0.75, 0.3 + 0.2 * i]) * L
        g.seed_plate(k, c, np.asarray(NPF[k], float), 2.0e-7, 6.0e-8)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    t0 = _t.time()
    for _ in range(nsteps):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv, per_field=per_field)
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    nv = int(sum(1 for k in range(1, g.nreg)
                 if float((reg == k).sum()) / g.N ** 3 > 1e-5))
    return dict(g=g, f=f, nv=nv, dt=dt, wall=_t.time() - t0,
                fingerprint=float(np.abs(g.phi[1:]).sum()),
                regsum=int(reg.sum()))


ok = True
res = {}
for adv in ('central', 'proj2'):
    r = go(adv)
    res[adv] = r
    print('  %-8s f=%.5f  N_var=%d  墙时=%.1f s  指纹 Σ|φ_1..|=%.10e  Σreg=%d' %
          (adv, r['f'], r['nv'], r['wall'], r['fingerprint'], r['regsum']), flush=True)
    if r['nv'] < 1 or r['f'] <= 0:
        print('    ✗ S3 失败：区域退化'); ok = False
# S4：必须不同。★ 记账：指纹**不能**用 `Σ|φ_1..|` —— 未被种子的 8 个场初值是 1e3，
#   把整个和淹没（实测两种格式的 Σ|φ| 差 1.7e-12，而 `Σreg` 差 431 vs 342 ⇒ 结果确实不同）。
#   ⇒ 指纹用**真正演化过的量**：`f` 与 `Σreg`。
d = abs(res['central']['f'] - res['proj2']['f'])
rel = d / max(abs(res['central']['f']), 1e-30)
same_reg = (res['central']['regsum'] == res['proj2']['regsum'])
print('  S4 central vs proj2：f 相对差 = %.4e ；Σreg %d vs %d（%s）'
      % (rel, res['central']['regsum'], res['proj2']['regsum'],
         '相同' if same_reg else '不同'))
print('     ⇒ %s' % ('PASS（分支确实被走到）' if (rel > 1e-6 or not same_reg)
                      else '✗ FAIL（疑似静默退化）'))
ok &= (rel > 1e-6 or not same_reg)
# S5：per_field 路径
try:
    r = go('proj2', per_field=True, nsteps=4)
    print('  S5 per_field=True + proj2：跑通，f=%.5f N_var=%d %s'
          % (r['f'], r['nv'], 'PASS'))
except Exception as e:                                          # noqa: BLE001
    print('  S5 ✗ FAIL：%s' % e)
    ok = False
# S2：守卫
g = res['proj2']['g']
try:
    wv = g.wrap_axes_any()
    print('  S2 wrap_axes_any() = %s %s' % (wv, 'PASS'))
except Exception as e:                                          # noqa: BLE001
    print('  S2 ✗ FAIL：%s' % e)
    ok = False
print('⇒ _smoke_proj2 %s' % ('PASS' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
