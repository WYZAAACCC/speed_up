#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AS 判据（2026-09-25）：**参考介质 + 极化迭代**的 inhomogeneous 弹性求解器
   （实现在 `windowB_aniso_elastic.py`，内部**全张量**、不做 Voigt 打包）。

为什么需要（门槛结论见 `_chk_aniso.py`）：AV-1 变体自能精确简并 ⇒ 选择只由变体间相互作用定；
AV-2 模量选择让 lamella 弹性能变 +14.7%/+60.8%；AV-3 核差 96% ⇒ 均匀 C 近似不可靠。

AS-1  均匀 C（**均匀** ε⁰）⇒ 1 步复现 `PF3D.sigma_tensor()` / `E_el`
AS-1b 均匀 C + **非均匀** ε⁰（**对角**、**含剪切**、**全随机** 三种）⇒ σ 必须与 `PF3D` 一致
      ★ 记账：初版只测"对角"⇒ 剪切成份从未被检验 ⇒ 带 bug 的 Γ 一路过关（σ 含剪切差 56%）。
        本项目教训"设计验证算例前先问这个测试能不能看到目标现象"在这里第二次应验。
AS-2  两相 lamella（各向同性）⇒ 与**逐层闭式解**吻合
AS-3  真实 β/α′ + 12 个变体：E_inh vs 各均匀近似
记账：`E_el` 与"−½<ε⁰σ>"/实空间 ½<ε^el:C:ε^el> 之间有一条 ~0.2–0.8% 的系统差（见文末）。
"""
import numpy as np
import windowB_pf3d as P
from windowB_pf3d import C_iso3, C_hex, C_cubic, C_rot4, rot_z_to, VOIGT, G6
from windowB_aniso_elastic import AnisoElastic, eng6
from windowB_ti64_variants import variants

GPA = 1e9
C_al = C_hex(162.4 * GPA, 92.0 * GPA, 69.0 * GPA, 180.7 * GPA, 46.7 * GPA)   # α/α′ ★文献值待核对
C_be = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)                          # β bcc ★待核对
C_is = C_iso3(113e9, 0.34)
ok = {}


def rec(tag, good, extra=''):
    ok[tag] = bool(good)
    print('   %-52s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


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


def sym(M):
    return 0.5 * (M + np.asarray(M).T)


N, L = 16, 1e-7
C = C_iso3(100e9, 0.3)

print('---- AS-1 均匀 C + 均匀 ε⁰：迭代复现 PF3D ----')
e1 = 1e-2 * np.eye(3)
pf = P.PF3D(N, L, C, [e1], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2, k0_mode='clamped')
pf.phi[:] = 1.0
sig_ref, E_ref = pf.sigma_tensor(), pf.E_el()
sol1 = AnisoElastic(N, L, [C], C)
s6, nit, hist = sol1.sigma6(np.ones((1, N, N, N)), [e1], accel=False)
d = np.abs(s6 - sig_ref).max() / max(np.abs(sig_ref).max(), 1e-30)
E_it = sol1.energy(np.ones((1, N, N, N)), [e1], accel=False)[0]
rec('AS-1 σ 与 PF3D 一致（1e-12）', d < 1e-12, 'rel %.2e（%d 步）' % (d, nit))
rec('AS-1 E_el 与 PF3D 一致（1e-3）', abs(E_it - E_ref) / abs(E_ref) < 1e-3,
    'rel %.2e' % (abs(E_it - E_ref) / abs(E_ref)))

print('---- AS-1b 均匀 C + 非均匀 ε⁰(x)：三种（对角 / 含剪切 / 全随机）----')
w = np.random.default_rng(3).random((N, N, N))
ph2 = np.stack([w, 1.0 - w])
rng = np.random.default_rng(7)
cases = [('对角', e1, np.diag([-5e-3, 2e-2, -1e-2])),
         ('含剪切', e1, np.array([[0.0, 2e-2, 0.0], [2e-2, 0.0, 0.0], [0.0, 0.0, 0.0]])),
         ('全随机', sym(rng.normal(scale=1e-2, size=(3, 3))),
          sym(rng.normal(scale=1e-2, size=(3, 3))))]
sol2 = AnisoElastic(N, L, [C, C], C)
worst = 0.0
for tag, a_, b_ in cases:
    pf2 = P.PF3D(N, L, C, [a_, b_], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2,
                 k0_mode='clamped')
    pf2.phi[0], pf2.phi[1] = ph2[0], ph2[1]
    s2, nit2, _ = sol2.sigma6(ph2, [a_, b_], accel=False)
    dd = np.abs(s2 - pf2.sigma_tensor()).max() / np.abs(pf2.sigma_tensor()).max()
    worst = max(worst, dd)
    E2 = sol2.energy(ph2, [a_, b_], accel=False)[0]
    print('   [%-6s] σ 相对差 = %.2e（%d 步）; E 相对差 = %.2e'
          % (tag, dd, nit2, abs(E2 - pf2.E_el()) / abs(pf2.E_el())))
rec('AS-1b σ 一致（三种 ε⁰ 都要过，1e-12）', worst < 1e-12, '最差 %.2e' % worst)

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


K1, G1, K2, G2 = 118e9, 23.2e9, 107.3e9, 43.4e9     # β/α′ 的 VRH 等效各向同性（★常数待核对）
zz = (np.arange(N) + 0.5) / N
lay2 = (zz < 0.22)
f_eff = float(lay2.mean())
ph = np.zeros((2, N, N, N))
ph[1] = np.where(lay2[None, None, :], 1.0, 0.0)
ph[0] = 1.0 - ph[1]
soll = AnisoElastic(N, L, [ciso(K1, G1), ciso(K2, G2)],
                    ciso(0.5 * (K1 + K2), 0.5 * (G1 + G2)))
print('   离散层：f 请求 0.22 ⇒ 实际 f_eff = %.4f（%d/%d 层）' % (f_eff, int(lay2.sum()), N))
for tag, e0_2 in (('纯膨胀', 1e-2 * np.eye(3)),
                  ('板条型偏', np.diag([-1e-2, -1e-2, 2e-2]))):
    E_it = soll.energy(ph, [np.zeros((3, 3)), e0_2], niter=4000, tol=1e-13)[0]
    E_cl = lamella_closed(K1, G1, K2, G2, e0_2, f_eff) * soll.V
    r = abs(E_it - E_cl) / abs(E_cl)
    rec('AS-2 lamella[%s] == 闭式（1e-9）' % tag, r < 1e-9, 'rel %.2e' % r)

print('---- AS-3 真实 β/α′ + 12 个变体：E_inh vs 各均匀近似 ----')
eps0, Fs, meta = variants()
nv = len(eps0)
Cv_list = [C_rot4(C_al, rot_z_to(np.asarray(meta[v]['n'], float) /
                                 np.linalg.norm(meta[v]['n']))) for v in range(nv)]
rng = np.random.default_rng(11)
xx = (np.arange(N) + 0.5) / N
XYZ = np.stack(np.meshgrid(xx, xx, xx, indexing='ij'), -1)
ph3 = np.zeros((nv + 1, N, N, N))
for v in range(nv):
    c = rng.random(3) * 0.7 + 0.15
    ph3[v + 1] = (np.linalg.norm(XYZ - c, axis=-1) < 0.28).astype(float)
occ = ph3[1:].sum(0)
ph3[1:] = np.where(occ[None] > 0, ph3[1:] / np.maximum(occ[None], 1e-30), 0.0)
ph3[0] = 1.0 - ph3[1:].sum(0)
e0l = [np.zeros((3, 3))] + [eps0[v] for v in range(nv)]
f_v = ph3[1:].sum(axis=(1, 2, 3)) / N ** 3
Cavg = (1 - f_v.sum()) * C_be + sum(f_v[v] * Cv_list[v] for v in range(nv))
sol3 = AnisoElastic(N, L, [C_be] + Cv_list, Cavg)
E_inh = sol3.energy(ph3, e0l, niter=400, tol=1e-11)[0]
print('   变体总体积分数 = %.3f ; E_inh = %.6e J' % (f_v.sum(), E_inh))
for tag, Cref in (('β 立方', C_be), ('α′ hcp', C_al), ('旧用各向同性', C_is)):
    E_h = AnisoElastic(N, L, [Cref] * (nv + 1), Cref).energy(
        ph3, e0l, niter=400, tol=1e-11)[0]
    print('   均匀 C = %-14s E_hom = %.6e J ⇒ E_inh/E_hom = %.3f（偏差 %+.1f%%）'
          % (tag, E_h, E_inh / E_h, 100 * (E_inh / E_h - 1)))

print()
print('==== AS 总判定: %s (%d/%d) ====' % ('PASS' if all(ok.values()) else 'FAIL',
                                           sum(ok.values()), len(ok)))
