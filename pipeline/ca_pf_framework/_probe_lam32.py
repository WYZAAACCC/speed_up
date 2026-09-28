#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_lam32.py —— Λ 用低精度（complex64/float32）存，**误差到底出在哪**？

动机：T3-4 首次判据给出 `max|Δσ|/max|σ| = 0.50` 而 `|ΔE_el|/E_el = 1.9e-9`，
      两者天差地别 ⇒ 必须分清是"界面阶梯噪声的几个坏点"还是"系统性的精度塌陷"。
      看**分布**而不是只看 max（本项目教训：聚合量会掩盖局部错误）。

同时给出**物理相关**的判据：弹性驱动力 `ed = ε⁰:σ` 在**界面带内**的相对误差
（只有界面带的 ed 会影响界面速度）。
"""
import os
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, PF3D, _lam_full               # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(300, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

N, dx = 64, 2.5e-8
L = N * dx
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [2e8] * NV, workers=1, reinit_every=0)
rng = np.random.default_rng(4)
R = 0.16 * L
ns = 0
while ns < 5:
    c = rng.random(3) * (L - 2 * R) + R
    try:
        g.seed_plate(int(rng.integers(1, NV + 1)), c, NPF[1], R, 4 * dx)
        ns += 1
    except ValueError:
        pass
g.init_parent()
reg = g.region()
for v in range(g.nv):
    g.pf.phi[v] = (reg == v + 1)


def calc(prec):
    p = PF3D(N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0, workers=1,
             k0_mode='clamped', lam_prec=prec)
    p.phi[:] = g.pf.phi
    ed = []
    sig = p.sigma_tensor()
    for v in range(p.nv):
        ed.append(np.einsum('p,p...->...', p.e0v_eng[v], sig))
    return sig, np.array(ed), float(p.E_el()), p


s64, e64, E64, p64 = calc('f64')
s32, e32, E32, p32 = calc('f32')
print('Lam dtype: f64=%s  f32=%s   (complex? %s)'
      % (p64.Lam.dtype, p32.Lam.dtype, np.iscomplexobj(p64.Lam)))
print('E_el: %.6e vs %.6e   相对差 %.3e' % (E64, E32, abs(E32 - E64) / abs(E64)))

d = np.abs(s32 - s64)
print()
print('--- σ 的误差分布（分母分别用 max|σ| 与逐点 |σ|）---')
sm = float(np.max(np.abs(s64)))
print('max|σ| = %.4e ; max|Δσ| = %.4e ; max|Δσ|/max|σ| = %.4f' % (sm, d.max(), d.max() / sm))
for q in (50, 90, 99, 99.9, 100):
    print('  |Δσ| 的 %5.1f 分位 = %.4e   （相对 max|σ| = %.3e）'
          % (q, np.percentile(d, q), np.percentile(d, q) / sm))
rms = float(np.sqrt(np.mean(d ** 2)) / np.sqrt(np.mean(s64 ** 2)))
print('  **RMS 相对误差 ||Δσ||₂/||σ||₂ = %.3e**' % rms)

# 物理相关：界面带内的 ed
phiw = np.take_along_axis(g.phi, np.argmin(g.phi, axis=0)[None], 0)[0]
band = np.abs(phiw) <= 2.0 * dx
de = np.abs(e32 - e64)
em = float(np.max(np.abs(e64)))
print()
print('--- 弹性驱动力 ed 的误差 ---')
print('max|ed| = %.4e ; max|Δed| = %.4e ; 全局 max 比 = %.4f' % (em, de.max(), de.max() / em))
dem = de.max(axis=0)          # 逐格点取"最坏变体"
ebm = np.abs(e64).max(axis=0)
print('界面带内（|φ_w| ≤ 2dx，%d 胞）: max|Δed|/max|ed| = %.4f ; 中位相对 = %.3e'
      % (int(band.sum()), float(dem[band].max()) / em,
         float(np.median(dem[band] / np.maximum(ebm[band], 1e-30)))))
frac = float((dem[band] / np.maximum(ebm[band], 1e-30) > 1e-2).mean())
print('界面带内 |Δed|/|ed| > 1%% 的胞占比 = %.4f' % frac)
print()
print('--- Λ 的数值分布（看是否"大数相消"）---')
La = np.asarray(p64.Lam)
print('Lam: |.| min/median/max = %.3e / %.3e / %.3e   (float32 eps=%.1e)'
      % (np.abs(La).min(), np.median(np.abs(La)), np.abs(La).max(), np.finfo(np.float32).eps))
print()
print('--- 隔离：Λ 存 float32 但 einsum 走 float64（只看"存储精度"）---')
p2 = PF3D(N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0, workers=1,
          k0_mode='clamped', lam_prec='f32')
p2.Lam = p2.Lam.astype(np.float64)
p2.phi[:] = g.pf.phi
s2 = p2.sigma_tensor()
d2 = np.abs(s2 - s64)
print('max|Δσ|/max|σ| = %.4f ; RMS 相对 = %.3e'
      % (d2.max() / sm, float(np.sqrt(np.mean(d2 ** 2)) / np.sqrt(np.mean(s64 ** 2)))))
print()
print('--- 隔离：Λ 存 float64 但 einsum 走 float32（只看"运算精度"）---')
p3 = PF3D(N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0, workers=1,
          k0_mode='clamped', lam_prec='f64')
p3.phi[:] = g.pf.phi
Eh = p3._epsh().reshape(6, -1)
sh = -np.einsum('kpq,qk->pk', p3.Lam, Eh.astype(np.float32), dtype=np.float32)
s3 = np.real(p3._ifft(sh.reshape((6, N, N, N))))
d3 = np.abs(s3 - s64)
print('max|Δσ|/max|σ| = %.4f ; RMS 相对 = %.3e'
      % (d3.max() / sm, float(np.sqrt(np.mean(d3 ** 2)) / np.sqrt(np.mean(s64 ** 2)))))
