#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''windowB_elastic.py --- Window B 微弹性地基（FFT 谱法，周期盒、均匀模量）
对应 MATH_FRAMEWORK §5.4：
    σ = C:(ε − ε0),  ∇·σ = 0,  E_el = ½∫(ε−ε0):C:(ε−ε0) dV
周期+均匀 C 时不需要解位移场，能量可在 Fourier 空间闭式给出：
    E_el = (V/2) Σ_k  ε0(k)* : Λ(n) : ε0(k)   ,  n = k/|k|
其中 Λ_ijkl(n) = C_ijkl − C_ijmn n_n [C·n]^{-1}_{mp} n_q C_pqkl   （Khachaturyan 张量）
单元测试（解析判据）：
  T1 均匀 ε0 ⇒ E_el = 0（特征应变被均匀应变完全弛豫）
  T2 单一 Fourier 模式 ⇒ E_el 与 Λ(n) 的解析式逐位一致
  T3 各向同性 C + 纯剪切/体积特征的已知闭式
'''
import numpy as np


def isotropic_C(E, nu):
    """各向同性弹性张量（3x3x3x3）"""
    mu = E / (2.0 * (1.0 + nu)); lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    C = np.zeros((3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    C[i, j, k, l] = lam * (i == j) * (k == l) + \
                                    mu * ((i == k) * (j == l) + (i == l) * (j == k))
    return C


def Lambda(C, n):
    """Khachaturyan 张量 Λ(n) = C − C·n·[C·n·n]^{-1}·n·C （3x3x3x3）"""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    # ★ A[j,l] = C[i,j,k,l] n_i n_k（收缩第 1、3 指标）; 各向同性下 = mu*I+(lam+mu)nn^T。
    #   （旧写法 C_ijkl n_k n_l 给 lam*I+2mu*nn^T, 不湮灭 rank-1 模式 —— 2026-09-24 修）
    A = np.einsum('ijkl,i,k->jl', C, n, n)
    Ainv = np.linalg.inv(A)
    # Γ1[k,l,q,r] = C[i,j,k,l] n_i Ainv[j,m] n_p C[p,m,q,r]
    C1 = np.einsum('ijkl,i,jm,p,pmqr->klqr', C, n, Ainv, n, C)
    return C - C1


def elastic_energy(C, eps0_k, kvecs, V):
    """eps0_k: (Nk,3,3) 特征应变的 Fourier 分量（复数）; kvecs: (Nk,3) 波矢（1/m）"""
    E = 0.0 + 0.0j
    for e0, k in zip(eps0_k, kvecs):
        r = np.linalg.norm(k)
        if r < 1e-30:
            continue                                 # k=0 模式不贡献能量
        L = Lambda(C, k)
        E += np.einsum('ij,ijkl,kl->', np.conj(e0), L, e0)
    return 0.5 * V * E.real


# ---------- 单元测试 ----------
E_mod, nu = 100e9, 0.3
C = isotropic_C(E_mod, nu)
L = 1e-6; V = L ** 3
print('=== Window B 微弹性内核单元测试（各向同性 C: E=%.0f GPa, nu=%.2f）' % (E_mod / 1e9, nu))

# T1: 均匀 ε0（只有 k=0 模式）⇒ E_el = 0
e0uni = np.array([[0.02, 0.0, 0.0], [0.0, -0.01, 0.0], [0.0, 0.0, 0.005]])
Ns = 32; ks = 2*np.pi*np.fft.fftfreq(Ns, d=L/Ns)
K = np.stack(np.meshgrid(ks, ks, ks, indexing='ij'), -1).reshape(-1, 3)
e_k = np.zeros((len(K), 3, 3), complex)
e_k[0] = e0uni * Ns ** 3                      # 只填 k=0（直流分量）
E1 = elastic_energy(C, e_k, K, V)
print('T1 均匀特征应变 => E_el = %.3e J  (解析 = 0)  %s' % (E1, 'PASS' if abs(E1) < 1e-12 else 'FAIL'))

# T2: 单一 Fourier 模式 ⇒ 与 Λ(n) 解析式一致
n = np.array([1.0, 2.0, 3.0]); n /= np.linalg.norm(n)
kv = 2 * np.pi / L * n
e0 = np.array([[0.03, 0.0, 0.0], [0.0, -0.02, 0.0], [0.0, 0.0, -0.01]])
E2 = elastic_energy(C, e0[None, :, :].astype(complex), kv[None, :], V)
Lm = Lambda(C, n)
E2_ana = 0.5 * V * np.einsum('ij,ijkl,kl->', e0, Lm, e0)
print('T2 单模式: 数值 %.6e vs 解析 %.6e  相对差 %.2e  %s' % (
    E2, E2_ana, abs(E2 - E2_ana) / abs(E2_ana), 'PASS' if abs(E2-E2_ana)/abs(E2_ana) < 1e-12 else 'FAIL'))

# T3: 各向同性 + 只保留一个剪切特征分量 ⇒ 有闭式（沿 n 的剪切分量被完全弛豫）
#     对 1D 调制（k ∥ x）且 ε0 = diag(0, -e, e)（纯剪切特征）: Λ 给出 2μ e^2
e3 = 0.05
e0s = np.array([[0.0, 0.0, 0.0], [0.0, -e3, 0.0], [0.0, 0.0, e3]])
kvx = np.array([2 * np.pi / L, 0.0, 0.0])
E3 = elastic_energy(C, e0s[None].astype(complex), kvx[None], V)
E3_ana = 2 * (E_mod / (2 * (1 + nu))) * e3 ** 2 * V
print('T3 纯剪切特征(k∥x): 数值 %.6e vs 解析 2μe²V=%.6e  相对差 %.2e  %s' % (
    E3, E3_ana, abs(E3 - E3_ana) / E3_ana, 'PASS' if abs(E3-E3_ana)/E3_ana < 1e-12 else 'FAIL'))
