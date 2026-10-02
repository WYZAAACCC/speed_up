#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_probe.py --- 探针：打印 `PF3D` 里 `Lam` / `Eh` 的**真实 shape 与 dtype**。

为什么必须先探针：`el.sig.contract` 的候选重写（GEMM / matmul / 手工 q 循环）
是否可行、是否可能逐位，**完全取决于 `Lam` 的布局与 dtype**
（`einsum('kpq,qk->pk')` 里 `k` 有多大、`p/q` 是什么、是否 float32）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_pf3d as P3

C = None
try:
    from T16_verify_rve import C as _C, EPS0 as _E
    C, EPS0 = _C, _E
except Exception as e:
    print('  ⚠ 取不到 T16 的 C/EPS0：%r' % (e,))
    EPS0 = [np.diag([0.01, -0.006, 0.004]) * (1 + 0.1 * i) for i in range(12)]
    C = None

N = int(os.environ.get('PROBE_N', '32'))
DX = 62.5e-9
eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(12)]
kw = {}
print('  PF3D 构造（N=%d, nv=%d）...' % (N, len(eps)))
pf = P3.PF3D(N, N * DX, C, eps, gamma=0.25, w90=1e-9, Lmob=1e-9, workers=1)
print('  ✅ 构造完成')
for nm in ('Lam', '_lam32', '_lam_cplx', '_fft_mode', 'nv', 'N', 'N3', 'axs'):
    v = getattr(pf, nm, '（无）')
    if isinstance(v, np.ndarray):
        print('    %-12s shape=%s dtype=%s nbytes=%.2f MB'
              % (nm, v.shape, v.dtype, v.nbytes / 2 ** 20))
    else:
        print('    %-12s %r' % (nm, v))
# 真实 Eh
pf.phi[0] = 1.0
e0 = pf.eps0_fields()
print('    eps0_fields shape=%s dtype=%s' % (e0.shape, e0.dtype))
Eh = pf._epsh(None)
print('    _epsh        shape=%s dtype=%s nbytes=%.2f MB'
      % (Eh.shape, Eh.dtype, Eh.nbytes / 2 ** 20))
Eh2 = Eh.reshape(6, -1)
print('    Eh.reshape(6,-1) → %s %s' % (Eh2.shape, Eh2.dtype))
sh = -np.einsum('kpq,qk->pk', pf.Lam, Eh2)
print('    einsum 输出  shape=%s dtype=%s' % (sh.shape, sh.dtype))
print('    ⇒ 契约：sh[p,k] = Σ_q Lam[k,p,q]·Eh[q,k]，'
      'k=%d 个模式、p,q 各 6' % sh.shape[1])
np.save('_r581_probe_Lam.npy', pf.Lam)
np.save('_r581_probe_Eh.npy', Eh2)
print('  已存 _r581_probe_Lam.npy / _r581_probe_Eh.npy（供 _r581_L3_contract.py 用真数据）')
