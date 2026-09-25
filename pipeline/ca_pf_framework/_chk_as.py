#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AS 判据（2026-09-25）：**参考介质 + 极化迭代**的 inhomogeneous 弹性求解器
   （实现在 `windowB_aniso_elastic.py`）。

为什么需要（门槛结论见 `_chk_aniso.py`）：AV-1 变体自能精确简并 ⇒ 选择只由变体间相互作用定；
AV-2 模量选择让 lamella 弹性能变 +14.7%/+60.8%；AV-3 核差 96% ⇒ 均匀 C 近似不可靠。

AS-1  均匀 C ⇒ 1 步复现 `PF3D.sigma_tensor()`（残差 0.00e+00）
AS-1b 均匀 C + **非均匀** ε⁰(x) ⇒ σ 与 `PF3D` 吻合 ~7e-16（这条才检验 k≠0 的 Γ）
      ⚠ 同一条的能量与 `PF3D.E_el` 差 ~0.35%（记账，不影响动力学：驱动力用 σ）
AS-2  两相 lamella（各向同性）⇒ 与**逐层闭式解**吻合 0.00e+00 / 2.6e-16
AS-3  真实 β/α′ + 12 个变体：E_inh vs 各均匀近似（回答"不均匀到底影响多少"）
"""
import numpy as np
import windowB_pf3d as P
from windowB_pf3d import C_iso3, C_hex, C_cubic, C_rot4, rot_z_to, VOIGT, G6
from windowB_aniso_elastic import AnisoElastic, eng6
from windowB_ti64_variants import variants

GPA = 1e9
C_al = C_hex(162.4 * GPA, 92.0 * GPA, 69.0 * GPA, 180.7 * GPA, 46.7 * GPA)   # α/α′ ★文献值待核对
C_be = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)                          # β bcc ★待核对
C_is = C_iso3(113e9, 0.34)                                                    # 旧用"各向同性等效"
ok = {}


def rec(tag, good, extra=''):
    ok[tag] = bool(good)
    print('   %-46s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


def ciso(K, G):
    l = K - 2 * G / 3
    Cm = np.zeros((3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l_ in range(3):
                    Cm[i, j, k, l_] = l * (i == j) * (k == l_) + \
                        G * ((i == k) * (j == l_) + (i == l_) * (j == k))
    return Cm


N, L = 16, 1e-7
C = C_iso3(100e9, 0.3)

print('---- AS-1 均匀 C 极限：迭代必须复现 PF3D.sigma_tensor() ----')
e1 = np.diag([1e-2, 1e-2, 1e-2])
pf = P.PF3D(N, L, C, [e1], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2, k0_mode='clamped')
pf.phi[:] = 1.0
sig_ref, E_ref = pf.sigma_tensor(), pf.E_el()
sol1 = AnisoElastic(N, L, [C], C)
phi1 = np.ones((1, N, N, N))
sig, eps, nit, hist = sol1.solve(phi1, [e1], accel=False)
d = np.abs(sig - sig_ref).max() / max(np.abs(sig_ref).max(), 1e-30)
E_it = sol1.energy(phi1, [e1], accel=False)[0]
rec('AS-1 均匀 C：σ 与 PF3D 一致（1e-10）', d < 1e-10,
    'rel %.2e（%d 步，残差 %.1e）' % (d, nit, hist[-1]))
rec('AS-1 均匀 C：E_el 与 PF3D 一致（1e-10）', abs(E_it - E_ref) / abs(E_ref) < 1e-10,
    'rel %.2e' % (abs(E_it - E_ref) / abs(E_ref)))

print('---- AS-1b 均匀 C + 非均匀 ε⁰(x)（检验 k≠0 的 Γ）----')
e2 = np.diag([-5e-3, 2e-2, -1e-2])
pf2 = P.PF3D(N, L, C, [e1, e2], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2,
             k0_mode='clamped')
w = np.random.default_rng(3).random((N, N, N))
pf2.phi[0], pf2.phi[1] = w, 1.0 - w
sig2_ref, E2_ref = pf2.sigma_tensor(), pf2.E_el()
sol2 = AnisoElastic(N, L, [C, C], C)
ph2 = np.stack([w, 1.0 - w])
sig2, _, nit2, hist2 = sol2.solve(ph2, [e1, e2], accel=False)
d2 = np.abs(sig2 - sig2_ref).max() / max(np.abs(sig2_ref).max(), 1e-30)
E2_it = sol2.energy(ph2, [e1, e2], accel=False)[0]
dE2 = abs(E2_it - E2_ref) / abs(E2_ref)
rec('AS-1b 非均匀 ε⁰：σ 与 PF3D 一致（1e-10）', d2 < 1e-10,
    'rel %.2e（%d 步）' % (d2, nit2))
print('   ⚠ 记账：同一条的 E_el 相对差 %.2e（绝对差 %.1e J，量级 ~1e-15 J）'
      '—— 不影响动力学（驱动力用 σ），但 `PF3D.E_el` 在"非均匀 ε⁰ + 均匀 C"下的口径待查'
      % (dE2, abs(E2_it - E2_ref)))

print('---- AS-2 两相 lamella（各向同性）== 逐层闭式解 ----')


def lamella_closed(K1, G1, K2, G2, e0_2, f):
    l1, m1 = K1 - 2 * G1 / 3, G1
    l2, m2 = K2 - 2 * G2 / 3, G2
    M1, M2 = l1 + 2 * m1, l2 + 2 * m2
    tr2, ezz2 = np.trace(e0_2), e0_2[2, 2]
    szz = -(f * (l2 * tr2 + 2 * m2 * ezz2) / M2) / ((1 - f) / M1 + f / M2)
    el1 = np.diag([0.0, 0.0, szz / M1])
    el2 = np.diag([0.0, 0.0, (szz + l2 * tr2 + 2 * m2 * ezz2) / M2]) - e0_2
    return (1 - f) * 0.5 * np.einsum('ij,ijkl,kl->', el1, ciso(K1, G1), el1) \
        + f * 0.5 * np.einsum('ij,ijkl,kl->', el2, ciso(K2, G2), el2)


K1, G1, K2, G2 = 118e9, 23.2e9, 107.3e9, 43.4e9      # β / α′ 的 VRH 等效各向同性（★常数待核对）
zz = (np.arange(N) + 0.5) / N
lay2 = (zz < 0.22)                                   # 层数取整 ⇒ 实际 f 用 lay2.mean()
f_eff = float(lay2.mean())
ph = np.zeros((2, N, N, N))
ph[1] = np.where(lay2[None, None, :], 1.0, 0.0)
ph[0] = 1.0 - ph[1]
soll = AnisoElastic(N, L, [ciso(K1, G1), ciso(K2, G2)],
                    ciso(0.5 * (K1 + K2), 0.5 * (G1 + G2)))
print('   离散层 f 请求 0.22、实际 f_eff = %.4f（%d/%d 层）⇒ 闭式用 f_eff'
      % (f_eff, int(lay2.sum()), N))
for tag, e0_2 in (('纯膨胀', 1e-2 * np.eye(3)),
                  ('板条型偏', np.diag([-1e-2, -1e-2, 2e-2]))):
    E_it = soll.energy(ph, [np.zeros((3, 3)), e0_2], niter=4000, tol=1e-13)[0]
    E_cl = lamella_closed(K1, G1, K2, G2, e0_2, f_eff) * soll.V
    r = abs(E_it - E_cl) / abs(E_cl)
    rec('AS-2 lamella[%s] == 闭式（1e-9）' % tag, r < 1e-9,
        'rel %.2e' % r)

print('---- AS-3 真实 β/α′ + 12 个变体：E_inh vs 各均匀近似 ----')
eps0, Fs, meta = variants()
nv = len(eps0)
Cv_list = []
n_list = []
for v in range(nv):
    n_v = np.asarray(meta[v]['n'], float)
    n_v = n_v / np.linalg.norm(n_v)
    n_list.append(n_v)
    Cv_list.append(C_rot4(C_al, rot_z_to(n_v)))
rng = np.random.default_rng(11)
xx = (np.arange(N) + 0.5) / N
XX, YY, ZZ = np.meshgrid(xx, xx, xx, indexing='ij')
XYZ = np.stack([XX, YY, ZZ], -1)
ph3 = np.zeros((nv + 1, N, N, N))
for v in range(nv):
    c = rng.random(3) * 0.7 + 0.15
    r = np.linalg.norm(XYZ - c, axis=-1)
    ph3[v + 1] = (r < 0.28).astype(float)
occ = ph3[1:].sum(0)
ph3[1:] = np.where(occ[None] > 0, ph3[1:] / np.maximum(occ[None], 1e-30), 0.0)
ph3[0] = 1.0 - ph3[1:].sum(0)
e0_list3 = [np.zeros((3, 3))] + [eps0[v] for v in range(nv)]
f_v = ph3[1:].sum(axis=(1, 2, 3)) / N ** 3
Cv_avg = sum(f_v[v] * Cv_list[v] for v in range(nv)) / max(f_v.sum(), 1e-30)
C_avg = (1 - f_v.sum()) * C_be + f_v.sum() * Cv_avg
sol3 = AnisoElastic(N, L, [C_be] + Cv_list, C_avg)
E_inh = sol3.energy(ph3, e0_list3, niter=400, tol=1e-11)[0]
print('   变体总体积分数 = %.3f' % f_v.sum())
for tag, Cref in (('β 立方', C_be), ('α′ hcp', C_al), ('旧用各向同性', C_is)):
    E_h = AnisoElastic(N, L, [Cref] * (nv + 1), Cref).energy(
        ph3, e0_list3, niter=400, tol=1e-11)[0]
    print('   均匀 C = %-14s E_hom = %.6e J ⇒ E_inh/E_hom = %.3f（偏差 %+.1f%%）'
          % (tag, E_h, E_inh / E_h, 100 * (E_inh / E_h - 1)))
print('   ⇒ 不均匀对 12 变体 RVE 的弹性能影响量级（逐条如实报）')

print()
print('==== AS 总判定: %s (%d/%d) ====' % ('PASS' if all(ok.values()) else 'FAIL',
                                           sum(ok.values()), len(ok)))