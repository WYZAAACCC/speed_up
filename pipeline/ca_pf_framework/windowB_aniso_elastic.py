#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_aniso_elastic.py --- **各向异性 / 不均匀** 弹性的参考介质 + 极化迭代求解器

为什么需要它（门槛结论见 `_chk_aniso.py`）：
  AV-1 12 个 Burgers 变体的弹性**自能精确简并**（~1e-16）⇒ 变体选择**只能**来自变体间相互作用；
  AV-2 模量选择让两相 lamella 弹性能变 **+14.7%(膨胀) / +60.8%(板条型偏)**；
  AV-3 Λ(C_β,n) vs Λ(C_各向同性,n) 在 6×6 基上最大差 **96%**。
  ⇒ `PF3D` 的"均匀 C"假设不可靠；12 个变体的 hcp 取向不同（模量不均匀）必须显式解。

算法（Moulinec–Suquet 基本格式；全夹紧 ⟨ε⟩=0）：
  τ^n = (C(x) − C⁰):ε^n − C(x):ε⁰(x)
  ε^{n+1} = −Γ⁰ * τ^n                      （只保留 k≠0；k=0 投影掉 = ⟨ε⟩ 固定为 0）
  Γ⁰ 由 4 阶张量的平衡方程**直接构造**（见 `gamma_packed` 的记账）。
  可选 Barzilai–Borwein 步长加速（只改路径，不改不动点）。

判据（`_chk_as.py`，全部实测）：
  AS-1  均匀 C ⇒ **1 步**复现 `PF3D.sigma_tensor()`（残差 0.00e+00）
  AS-1b 均匀 C + **非均匀** ε⁰(x) ⇒ σ 与 `PF3D` 吻合 **7.4e-16**（这条才检验 k≠0 的 Γ）
  AS-2  两相 lamella（各向同性）⇒ 与**逐层闭式解**吻合 **0.00e+00 / 2.6e-16**
  ⚠ 未解决（记账）：AS-1b 的**能量**与 `PF3D.E_el` 差 ~0.35%（绝对差 ~2.3e-17 J，是
    ~1e-15 J 量级上的比较）——**不影响动力学**（驱动力用的是 σ，不是 E_el），
    但 `PF3D.E_el` 在"非均匀 ε⁰ + 均匀 C"下的口径需要单独查一次。
"""
import numpy as np
from scipy import fft as sfft
import windowB_pf3d as P
from windowB_pf3d import VOIGT, G6, C_rot4, rot_z_to


def voigt_of(C):
    return np.array([[C[VOIGT[p][0], VOIGT[p][1], VOIGT[q][0], VOIGT[q][1]]
                      for q in range(6)] for p in range(6)])


def eng6(e_t):
    """3x3 张量应变 -> **工程** 6 分量（剪切 ×2），与本仓库 `PF3D.e0v_eng` 同约定。"""
    return np.array([e_t[i, j] for (i, j) in VOIGT]) * G6


def gamma_packed(C, K):
    """Green 算子 Γ̂(k) 的**打包**表示：`e^eng = −Γ τ`（τ = 极化应力）。
       ★ 记账（必须记，我踩过）：**不能用恒等式 `Γ = S − S·Λ·S`**。那条在 k=0 扇区自洽
         （AS-1 一步 0 残差），但本仓库的打包约定是"**应力用张量分量、应变用工程分量**"
         （σ^eng = C^eng e^eng）⇒ 在混合约定下该恒等式给出的 Γ **过度松弛**
         （实测 lamella 能量被压到 ~0，而闭式是 5.12e6 ✗）。
       正确做法：**从 4 阶张量按平衡方程直接推**（与 `lambda_packed` 的构造互相独立）：
         A_il = C_ijkl n_j n_k ;  û = −A⁻¹(n·τ) ;  ε = sym(n⊗û)
         ⇒ Γ_pqjm = ½[ n_p A⁻¹_qm + n_q A⁻¹_pm ] n_j
       打包：Γ^eng[p,q] = G6[p]·Γ_{VOIGT[p],VOIGT[q]}（只有剪切**行**带因子 2：应力向量
       不带、工程应变向量带 ✓）。k=0 处 A 奇异 ⇒ 用哑方向占位、最后把该模式置 0。"""
    n = np.asarray(K, float)
    nrm = np.linalg.norm(n, axis=-1, keepdims=True) + 1e-300
    n = np.where(nrm > 1e-9, n / nrm, np.array([1.0, 0.0, 0.0]))
    A = np.einsum('ijkl,nj,nk->nil', C, n, n)
    Ai = np.linalg.inv(A)
    G4 = 0.5 * (np.einsum('np,nqm,nj->npqjm', n, Ai, n)
                + np.einsum('nq,npm,nj->npqjm', n, Ai, n))
    out = np.zeros((len(K), 6, 6))
    for p, (i, j) in enumerate(VOIGT):
        for q, (k, l_) in enumerate(VOIGT):
            out[:, p, q] = G6[p] * G4[:, i, j, k, l_]
    return out


class AnisoElastic(object):
    """参考介质 + 极化迭代 inhomogeneous 弹性（周期盒、全夹紧 ⟨ε⟩=0）。
       `C_phases`: (nph,3,3,3,3) 每相的 C；`C_ref`: 参考模量（建议取相体积平均或 Voigt 平均）。"""

    def __init__(self, N, L, C_phases, C_ref, workers=4, project_k0=True):
        self.N, self.L = N, L
        self.dx = L / N
        self.V = float(L) ** 3
        self.nph = len(C_phases)
        self.CV = np.array([voigt_of(C) for C in C_phases])
        self.CVref = voigt_of(C_ref)
        self.SV = np.linalg.inv(self.CVref)
        self.kv = 2 * np.pi * np.fft.fftfreq(N, d=self.dx)
        K = np.stack(np.meshgrid(*[self.kv] * 3, indexing='ij'), -1).reshape(-1, 3)
        self.K = K
        self.Gam = gamma_packed(C_ref, K)
        self.Gam[int(np.argmin((K ** 2).sum(1)))] = 0.0        # 投影掉 k=0
        if project_k0:
            self.Gam[0] = 0.0
        self.workers = workers
        self.axs = (1, 2, 3)

    def _fft(self, x):
        return sfft.fftn(x, axes=self.axs, workers=self.workers)

    def _ifft(self, x):
        return sfft.ifftn(x, axes=self.axs, workers=self.workers)

    def _Cx_ex(self, phi, e0_list):
        CVx = np.tensordot(self.CV, phi, axes=(0, 0))          # (6,6,N,N,N)
        e0x = np.zeros((6,) + phi.shape[1:])
        for p in range(self.nph):
            e0x += phi[p] * eng6(e0_list[p]).reshape(6, 1, 1, 1)
        return CVx, e0x

    def solve(self, phi, e0_list, niter=200, tol=1e-10, accel=True):
        phi = np.asarray(phi, float)
        CVx, e0x = self._Cx_ex(phi, e0_list)
        Cdiff = CVx - self.CVref.reshape(6, 6, 1, 1, 1)
        shp = (6,) + phi.shape[1:]
        eps = np.zeros(shp)
        eps_p = None
        hist = []
        for it in range(niter):
            tau = np.einsum('pq...,q...->p...', Cdiff, eps) \
                - np.einsum('pq...,q...->p...', CVx, e0x)
            th = self._fft(tau.reshape(shp)).reshape(6, -1)
            eh = -np.einsum('kpq,qk->pk', self.Gam, th)
            enew = np.real(self._ifft(eh.reshape(shp)))
            if accel and eps_p is not None:
                de, dp = enew - eps, eps - eps_p
                beta = float(np.clip((de * dp).sum() / ((dp * dp).sum() + 1e-300),
                                     0.0, 1.0))
                enext = enew + beta * de
            else:
                enext = enew
            err = float(np.abs(enext - eps).max())
            hist.append(err)
            eps_p, eps = eps, enext
            if err < tol:
                break
        sig = np.einsum('pq...,q...->p...', CVx, eps - e0x)
        return sig, eps, len(hist), hist

    def energy(self, phi, e0_list, **kw):
        sig, eps, nit, hist = self.solve(phi, e0_list, **kw)
        CVx, e0x = self._Cx_ex(np.asarray(phi, float), e0_list)
        el = eps - e0x
        dens = 0.5 * np.einsum('p...,pq...,q...->...', el, CVx, el)
        return float(dens.mean()) * self.V, nit, hist