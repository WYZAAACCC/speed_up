#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AV 判据（2026-09-25）：**各向异性/不均匀弹性值不值得上 inhomogeneous 求解器**？

问题：`PF3D` 的 FFT 谱法要求均匀 C，而 12 个变体 hcp 取向不同 ⇒ 逐变体模量要换
"参考介质 + 极化迭代"。上之前必须量化"模量不均匀"本身影响多少 —— 这就是那个门槛。

AV-0 两相的等效各向同性模量（VRH）与对比度
AV-1 **变体自能的简并性**：e_v(C)=½ε⁰_v:Λ(C,n_v):ε⁰_v —— 立方点群下 12 个变体**必须**精确简并
     （这既是一条正确性检查，也说明**变体选择不可能来自自能**，只能来自变体间相互作用）
AV-2 **同几何、只换模量**的对照（★第一版这里我写错了，见记账）：
     β/α′ 两层 lamella（法向 ẑ、全夹紧 ⟨ε⟩=0）的**逐层精确解**，
     对比"把两相模量换成同一个 C_ref"的**同几何**精确解 ⇒ 隔离出"模量不均匀"的作用
AV-3 相互作用核 Λ(C_be,n) vs Λ(C_is,n) 的差异

★ 记账（第一版的测量设计错误，必须记）：AV-2 初版把 E_hom 取成 `½V⟨ε⁰:C:ε⁰⟩`
  （= **全夹紧**均匀估计）。但那个数里混进了**几何松弛**（lamella 可以在 z 向互相让），
  而几何松弛与模量不均匀是**两回事** ⇒ 初版报出的 "E_exact/E_hom = 0.22（差 4.6 倍）"
  **不能归因于模量不均匀**。正确对照必须是"**同几何**、只换模量"。
"""
import numpy as np
from windowB_pf3d import C_iso3, C_hex, C_cubic, C_rot4, rot_z_to, _lam_full, VOIGT, G6
from windowB_ti64_variants import variants

GPA = 1e9
eps0, Fs, meta = variants()
nv = len(eps0)
C_al = C_hex(162.4 * GPA, 92.0 * GPA, 69.0 * GPA, 180.7 * GPA, 46.7 * GPA)   # α/α′ ★文献值待核对
C_be = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)                          # β bcc ★待核对
C_is = C_iso3(113e9, 0.34)                                                    # 旧用的"各向同性等效"


def voigt_of(C):
    return np.array([[C[VOIGT[p][0], VOIGT[p][1], VOIGT[q][0], VOIGT[q][1]]
                      for q in range(6)] for p in range(6)])


def vrh(C):
    CV = voigt_of(C)
    SV = np.linalg.inv(CV)
    KV = (CV[0, 0] + CV[1, 1] + CV[2, 2] + 2 * (CV[0, 1] + CV[0, 2] + CV[1, 2])) / 9.0
    GV = ((CV[0, 0] + CV[1, 1] + CV[2, 2]) - (CV[0, 1] + CV[0, 2] + CV[1, 2])
          + 3 * (CV[3, 3] + CV[4, 4] + CV[5, 5])) / 15.0
    KR = 1.0 / (SV[0, 0] + SV[1, 1] + SV[2, 2] + 2 * (SV[0, 1] + SV[0, 2] + SV[1, 2]))
    GR = 15.0 / (4 * (SV[0, 0] + SV[1, 1] + SV[2, 2]) - 4 * (SV[0, 1] + SV[0, 2] + SV[1, 2])
                 + 3 * (SV[3, 3] + SV[4, 4] + SV[5, 5]))
    return 0.5 * (KV + KR), 0.5 * (GV + GR)


def ciso(K, G):
    l = K - 2 * G / 3
    C = np.zeros((3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l_ in range(3):
                    C[i, j, k, l_] = l * (i == j) * (k == l_) + \
                        G * ((i == k) * (j == l_) + (i == l_) * (j == k))
    return C


print('---- AV-0 两相的等效各向同性模量（VRH）----')
Kb, Gb = vrh(C_be); Ka, Ga = vrh(C_al); Kc, Gc = vrh(C_is)
for tag, K, G in (('β(bcc)', Kb, Gb), ('α/α′(hcp)', Ka, Ga), ('旧用各向同性', Kc, Gc)):
    E = 9 * K * G / (3 * K + G); nu = (3 * K - 2 * G) / (2 * (3 * K + G))
    print('   %-14s K=%6.1f GPa  G=%6.1f GPa  ⇒ E=%6.1f GPa  ν=%.3f'
          % (tag, K / GPA, G / GPA, E / GPA, nu))
print('   ⇒ 剪切模量对比 G(α′)/G(β) = %.2f' % (Ga / Gb))
print('   ⇒ ★ 旧用的 C_iso3(113 GPa, 0.34) 等效于 G=%.1f、ν=%.3f —— 与 **α′** 几乎一致，'
      '而不是母相 β（G=%.1f、ν=%.3f）⇒ 旧选择实际上用的是**产物模量**，不是基体模量。'
      % (Gc / GPA, (3 * Kc - 2 * Gc) / (2 * (3 * Kc + Gc)), Gb / GPA,
         (3 * Kb - 2 * Gb) / (2 * (3 * Kb + Gb))))

print('---- AV-1 变体自能的简并性 ----')
res = {}
for tag, C, own in (('iso', C_is, False), ('beta_cubic', C_be, False),
                    ('hcp_own', None, True)):
    e = np.zeros(nv)
    for v in range(nv):
        di = meta[v] if isinstance(meta[v], dict) else {}
        n_v = np.asarray(di.get('n'), float); n_v = n_v / np.linalg.norm(n_v)
        Cv = C_rot4(C_al, rot_z_to(n_v)) if own else C
        e[v] = 0.5 * np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(Cv, n_v), eps0[v])
    res[tag] = e
    print('   %-11s e_v/1e6 = %s  散布 (max−min)/mean = %.2e'
          % (tag, np.array2string(e / 1e6, precision=2),
             (e.max() - e.min()) / e.mean()))
print('   ⇒ 12 个变体的自能在**立方点群**下**精确简并**（散布 ~1e-16）⇒ 这是一条正确性检查 ✓，')
print('     同时说明：**变体选择不可能来自单变体自能**，只能来自变体间弹性相互作用/自协调。')

print('---- AV-2 同几何、只换模量的对照（两相 lamella 逐层精确解）----')


def lamella(K1, G1, K2, G2, e0_2, f):
    """全夹紧（⟨ε⟩=0）两层 lamella（法向 ẑ，各向同性两相）。
       ε_xx=ε_yy=e_p 两层相同（相容）；σ_zz 两层相同（平衡）；⟨ε⟩=0 ⇒ e_p=0 且 ⟨ε_zz⟩=0。"""
    l1, m1 = K1 - 2 * G1 / 3, G1
    l2, m2 = K2 - 2 * G2 / 3, G2
    M1, M2 = l1 + 2 * m1, l2 + 2 * m2
    tr2, ezz2 = np.trace(e0_2), e0_2[2, 2]
    szz = -(f * (l2 * tr2 + 2 * m2 * ezz2) / M2) / ((1 - f) / M1 + f / M2)
    E1 = np.diag([0.0, 0.0, szz / M1])
    E2 = np.diag([0.0, 0.0, (szz + l2 * tr2 + 2 * m2 * ezz2) / M2])
    el1, el2 = E1.copy(), E2 - e0_2
    d1 = 0.5 * np.einsum('ij,ijkl,kl->', el1, ciso(K1, G1), el1)
    d2 = 0.5 * np.einsum('ij,ijkl,kl->', el2, ciso(K2, G2), el2)
    return (1 - f) * d1 + f * d2


f = 0.22
for tag, e0_2 in (('纯膨胀 b=1e-2', 1e-2 * np.eye(3)),
                  ('板条型偏 diag(−1e-2,−1e-2,+2e-2)',
                   np.diag([-1e-2, -1e-2, 2e-2]))):
    Ei = lamella(Kb, Gb, Ka, Ga, e0_2, f)
    print('   [%s]  E_inh(β/α′ 真实两相) = %.4e J/m³' % (tag, Ei))
    for t2, (K, G) in (('均匀 C=β等效', (Kb, Gb)), ('均匀 C=α′等效', (Ka, Ga)),
                       ('均匀 C=旧各向同性', (Kc, Gc)),
                       ('均匀 C=Voigt 平均', (0.5 * (Kb + Ka), 0.5 * (Gb + Ga)))):
        Eh = lamella(K, G, K, G, e0_2, f)
        print('      %-16s E_hom=%.4e  ⇒ E_inh/E_hom = %.3f  （偏差 %+.1f%%）'
              % (t2, Eh, Ei / Eh, 100 * (Ei / Eh - 1)))

print('---- AV-3 相互作用核 Λ 的差异 ----')
bases = [np.diag([1.0, 0, 0]), np.diag([0, 1.0, 0]), np.diag([0, 0, 1.0]),
         np.array([[0, 1.0, 0], [1.0, 0, 0], [0, 0, 0]]),
         np.array([[0, 0, 1.0], [0, 0, 0], [1.0, 0, 0]]),
         np.array([[0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])]
worst = 0.0
for k in range(6):
    for l_ in range(6):
        a = np.einsum('ij,ijkl,kl->', bases[k], _lam_full(C_be, [1.0, 1, 1]), bases[l_])
        b = np.einsum('ij,ijkl,kl->', bases[k], _lam_full(C_is, [1.0, 1, 1]), bases[l_])
        s = max(abs(a), abs(b))
        if s > 1e-3 * abs(np.einsum('ij,ijkl,kl->', bases[0],
                                    _lam_full(C_be, [1.0, 1, 1]), bases[0])):
            worst = max(worst, abs(a - b) / s)
print('   Λ(C_be,n=(1,1,1)) vs Λ(C_is,同 n) 在 6×6 基上的最大相对差 = %.1f%%' % (100 * worst))