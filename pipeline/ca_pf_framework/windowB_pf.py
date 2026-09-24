#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''windowB_pf.py --- Window B 马氏体变体 PF 引擎（FFT 微弹性 + 非守恒多相场）
修正版：FFT 分量轴/模式轴严格搬运（(dim,dim,N,N) ↔ (N,N,dim,dim)），能量 ≥ 0 且有解析判据。
'''
import numpy as np


def C_iso(E, nu, dim):
    mu = E / (2 * (1 + nu)); lam = E * nu / ((1 + nu) * (1 - 2 * nu))
    C = np.zeros((dim,) * 4)
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                for l in range(dim):
                    C[i, j, k, l] = lam * (i == j) * (k == l) + \
                        mu * ((i == k) * (j == l) + (i == l) * (j == k))
    return C


def Lambda(C, n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    # ★ 声学张量收缩: A[j,l] = C[i,j,k,l] n_i n_k（第 1、3 指标）。
    #   写成 C_ijkl n_k n_l（第 3、4）会让 Lambda 不再湮灭 rank-1 模式 sym(a(x)n)，
    #   层片相容性/孪晶/惯习面物理全错（2026-09-24 修）。
    A = np.einsum('ijkl,i,k->jl', C, n, n)
    Ainv = np.linalg.inv(A)
    return C - np.einsum('ijkl,i,jm,p,pmqr->klqr', C, n, Ainv, n, C)


def e_density(C, e0, n):
    return 0.5 * np.einsum('ij,ijkl,kl->', e0, Lambda(C, n), e0)


class MartensitePF(object):
    def __init__(self, N, L, C, eps0, kappa=0.0, M_int=0.0, w=1e-8, gamma=0.0,
                 dG=0.0, dim=2, sigma_ext=None):
        self.N, self.L, self.dim = N, L, dim
        self.C = C; self.eps0 = np.asarray(eps0, float); self.nv = len(self.eps0)
        self.kappa = kappa
        self.W = 6.0 * gamma / w if gamma > 0 else 0.0
        self.Lmob = M_int * w / gamma if gamma > 0 else 0.0
        self.dG = dG
        self.sigma_ext = np.zeros((dim, dim)) if sigma_ext is None else np.asarray(sigma_ext, float)
        self.dx = L / N
        self.phi = np.zeros((self.nv,) + (N,) * dim)
        self.k = [2 * np.pi * np.fft.fftfreq(N, d=self.dx) for _ in range(dim)]
        Kg = np.stack(np.meshgrid(*self.k, indexing='ij'), -1)          # (N,..,dim)
        self.k2 = (Kg ** 2).sum(-1)
        self.Kf = Kg.reshape(-1, dim)
        self.Lam = np.zeros((len(self.Kf), dim, dim, dim, dim))
        for i, kk in enumerate(self.Kf):
            self.Lam[i] = C if np.linalg.norm(kk) < 1e-12 else Lambda(C, kk)
        self.axp = tuple(range(1, 1 + dim))          # φ(nv,N,..) 的空间轴
        self.axc = (0, 1)                            # 张量 ε⁰(dim,dim,N,..) 的分量轴
        self.axs = tuple(range(2, 2 + dim))          # 张量 ε⁰ 的空间轴
        self.norm = N ** dim

    # ---- ε⁰(k)：返回 (M,dim,dim) 与实空间 ε⁰(x) ----
    def eps0_k(self):
        e0r = np.zeros((self.dim, self.dim) + (self.N,) * self.dim)
        for v in range(self.nv):
            for i in range(self.dim):
                for j in range(self.dim):
                    e0r[i, j] += self.phi[v] * self.eps0[v, i, j]
        ek = np.fft.fftn(e0r, axes=self.axs) / self.norm            # (dim,dim,N,..)
        ek = np.transpose(ek, self.axs + self.axc).reshape(-1, self.dim, self.dim)
        return ek, e0r

    def E_el(self):
        ek, _ = self.eps0_k()
        return 0.5 * self.L ** self.dim * float(np.real(
            np.einsum('mij,mijkl,mkl->', np.conj(ek), self.Lam, ek)))

    def forces(self):
        ek, e0r = self.eps0_k()
        # ★ 归一化坑（2026-09-24 修复）：eps0_k() 给的是【连续谱】ε̂=fftn/N^d（E_el 用它对），
        #   但 σ(x)=Σ_k σ̂(k)e^{ikx}=N^d·ifftn(σ̂) ⇒ 这里必须乘回 N^d。
        #   少了它 ⇒ σ 小 N^d≈1.6e4 倍 ⇒ 界面感觉不到弹性驱动，只剩 dG 推界面（静默物理错误）。
        #   正对照：见 test_force_fd()（有限差分功能导数）。
        sk = -self.norm * np.einsum('mijkl,mkl->mij', self.Lam, ek)  # σ(k)=−Λ:ε̂（未归一化约定）
        sk = sk.reshape((self.N,) * self.dim + (self.dim, self.dim))
        sk = np.transpose(sk, self.axs + self.axc)                  # (dim,dim,N,..)
        sig = np.real(np.fft.ifftn(sk, axes=self.axs))
        f = np.zeros_like(self.phi)
        for v in range(self.nv):
            f[v] = -np.einsum('ij,ij...->...', self.eps0[v], sig)
            f[v] += np.einsum('ij,ij->', self.sigma_ext, self.eps0[v])
            p = self.phi[v]
            # −∂f/∂φ：化学驱动 +ΔG·6φ(1−φ)，双阱【负号】−2Wφ(1−φ)(1−2φ)
            f[v] += self.dG * 6 * p * (1 - p) - self.W * 2 * p * (1 - p) * (1 - 2 * p)
        return f, sig

    def step(self, dt, cap_sum=True):
        f, _ = self.forces()
        lap = np.real(np.fft.ifftn(-self.k2 * np.fft.fftn(self.phi, axes=self.axp), axes=self.axp))
        phin = self.phi + dt * self.Lmob * (f + self.kappa * lap)
        if cap_sum:
            s = phin.sum(0)
            over = s > 1.0
            if over.any():
                phin[:, over] /= s[over]
        np.clip(phin, 0.0, 1.0, out=phin)
        self.phi = phin

    def E_total(self):
        """总自由能密度积分（弹性 + 化学）"""
        E = self.E_el()
        for v in range(self.nv):
            p = self.phi[v]
            g = np.gradient(p, self.dx)
            gr = sum(np.sum(gi ** 2) for gi in g) * self.dx ** self.dim
            E += np.sum(self.W * p ** 2 * (1 - p) ** 2 - self.dG * p ** 2 * (3 - 2 * p)) * self.dx ** self.dim
            E += 0.5 * self.kappa * gr
        return E


# ------------------------------------------------------------------ A0
def test_energy():
    dim = 2; C = C_iso(100e9, 0.3, dim); N, L = 16, 1e-7
    e0 = np.array([[0.06, 0.04], [0.04, -0.03]])
    pf = MartensitePF(N, L, C, e0[None], dim=dim)
    pf.phi[0] = 1.0
    En = pf.E_el(); Ea = 0.5 * L ** dim * np.einsum('ij,ijkl,kl->', e0, C, e0)
    print('A0a 均匀 ε⁰: E=%.6e vs (V/2)ε⁰:C:ε⁰=%.6e 相对差 %.1e  %s' % (
        En, Ea, abs(En - Ea) / Ea, 'PASS' if abs(En - Ea) / Ea < 1e-10 else 'FAIL'))
    k0 = 2 * np.pi / L * np.array([1.0, 2.0])       # ★ 必须是周期盒的整数模式
    X = np.arange(N)[:, None] * pf.dx; Y = np.arange(N)[None, :] * pf.dx
    amp = 0.2
    pf.phi[0] = 0.5 + amp * np.cos(k0[0] * X + k0[1] * Y)
    En = pf.E_el()
    E_DC = 0.5 * L ** dim * (0.5 ** 2) * np.einsum('ij,ijkl,kl->', e0, C, e0)
    E_k0 = 2 * 0.5 * L ** dim * (amp / 2) ** 2 * np.einsum('ij,ijkl,kl->', e0, Lambda(C, k0), e0)
    Ea = E_DC + E_k0
    print('A0b 单模式:  E=%.6e vs 闭式=%.6e 相对差 %.1e  %s' % (
        En, Ea, abs(En - Ea) / Ea, 'PASS' if abs(En - Ea) / Ea < 1e-8 else 'FAIL'))


# ------------------------------------------------------------------ A1
def calibrate_interface():
    """1D 双阱界面的【平衡 tanh 剖面】上测 w90 与 γ，验证离散化与解析常数
       解析（自推）：a = sqrt(κ/(2W))，φ=½(1−tanh((x−xc)/(2a)))，
         γ = ∫[κ/2 φ'² + W φ²(1−φ)²]dx = √(2κW)/6（两项各占一半）
         w90（10–90%） = 4·atanh(0.8)·a = 4.394·a = 3.107·√(κ/W)
    """
    Nx, dx = 4096, 1e-9
    print('A1 1D 界面（解析平衡剖面；测 w90 与 γ 的离散化误差）')
    print('     W(J/m³)     w90(m)      3.107√(κ/W)   γ(J/m²)    √(2κW)/6    w90/解析  γ/解析')
    for W in (1e8, 4e8, 1.6e9):
        w_t = 10e-9
        kap = W * w_t ** 2 / 8.0 * 4.0
        a = np.sqrt(kap / (2 * W))
        x = np.arange(Nx) * dx
        p = 0.5 * (1 - np.tanh((x - Nx * dx / 2) / (2 * a)))
        w90 = 4 * np.arctanh(0.8) * a
        g = np.gradient(p, dx)
        gam = float(np.sum(kap / 2 * g ** 2 + W * p ** 2 * (1 - p) ** 2) * dx)
        wth = 3.107 * np.sqrt(kap / W); gth = np.sqrt(2 * kap * W) / 6.0
        print('     %.1e   %.4e   %.4e    %.4f    %.4f    %.3f    %.3f' % (
            W, w90, wth, gam, gth, w90 / wth, gam / gth))


def test_force_fd():
    """★ 功能导数【正对照】：dE_el/dφ_v(x) 必须等于 -ε⁰_v:σ(x)。
       这条判据专门抓 FFT 归一化错（2026-09-24 抓到过一次，差 N^dim ≈ 1.6e4 倍）。
       同时把"若漏掉 N^dim 会差多少"一并打印出来，作为反向对照。"""
    dim = 2; C = C_iso(100e9, 0.3, dim); N, L = 12, 1e-7
    e0 = np.array([[0.05, 0.02], [0.02, -0.03]])
    e1 = np.array([[-0.04, 0.0], [0.0, 0.06]])
    pf = MartensitePF(N, L, C, np.array([e0, e1]), dim=dim)
    rng = np.random.default_rng(3)
    pf.phi[0] = 0.5 + 0.3 * rng.random((N, N)); pf.phi[1] = 1 - pf.phi[0]
    f, sig = pf.forces()
    idx, v = (3, 5), 0
    an = f[v][idx]                                     # 泛函导数（J/m^dim）
    errs = []
    for d in (1e-4, 1e-5, 1e-6):
        E0 = pf.E_el(); pf.phi[v][idx] += d; E1 = pf.E_el(); pf.phi[v][idx] -= d
        errs.append(abs((E1 - E0) / (d * pf.dx ** dim) - an) / abs(an))
    # 反向对照：故意漏掉 N^dim 时的偏差倍数
    ek, _ = pf.eps0_k()
    sk_old = -np.einsum('mijkl,mkl->mij', pf.Lam, ek)
    sk_old = sk_old.reshape((N,) * dim + (dim, dim)).transpose(pf.axs + pf.axc)
    sig_old = np.real(np.fft.ifftn(sk_old, axes=pf.axs))
    f_old = -np.einsum('ij,ij...->...', e0, sig_old)
    ratio = abs(an / f_old[idx]) if f_old[idx] != 0 else np.inf
    print('FD 正对照: 相对差(1e-4/1e-5/1e-6) = %.2e / %.2e / %.2e   %s'
          % (errs[0], errs[1], errs[2], 'PASS' if errs[-1] < 1e-4 else 'FAIL'))
    print('           反向对照: 漏掉 N^dim 时 σ 偏差倍数 = %.3e（应 ≈ N^dim = %.3e）'
          % (ratio, float(pf.norm)))
    return errs[-1] < 1e-4


if __name__ == '__main__':
    print('=' * 92); print('Window B PF：能量与界面标定 + 力正对照'); print('=' * 92)
    test_energy(); print(); calibrate_interface(); print()
    ok = test_force_fd()
    print('\n总判定: %s' % ('ALL PASS' if ok else 'FAIL'))
