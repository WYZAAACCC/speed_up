#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_aniso_elastic.py --- **各向异性 / 不均匀** 弹性的参考介质 + 极化迭代求解器

为什么需要（门槛结论见 `_chk_aniso.py`）：
  AV-1 12 个 Burgers 变体的弹性**自能精确简并**（~1e-15）⇒ 变体选择**只能**来自变体间相互作用；
  AV-2 模量选择让两相 lamella 弹性能变 **+14.7%(膨胀) / +60.8%(板条型偏)**；
  AV-3 Λ(C_β,n) vs Λ(C_各向同性,n) 最大差 **96%**。
  ⇒ `PF3D` 的"均匀 C"假设不可靠；12 个变体的 hcp 取向不同（模量不均匀）必须显式解。

算法（Moulinec–Suquet 基本格式；全夹紧 ⟨ε⟩=0）：
  τ^n = (C(x) − C⁰):ε^n − C(x):ε⁰(x)
  ε^{n+1} = −Γ⁰ * τ^n                      （只保留 k≠0；k=0 投影掉 = ⟨ε⟩ 固定为 0）
  可选 Barzilai–Borwein 步长加速（只改路径，不改不动点）。

★★ 记账（**两个我踩过的坑，都必须记**）：
 1. **全部在 3×3×3×3 张量空间里做，不做任何"Voigt 打包"**。这个仓库同时存在两种约定
    （`lambda_packed` 是"张量分量无因子"，而 `PF3D._epsh` 把工程应变剪切分量 ×2），
    我两次手推打包都在**剪切分量**上出错：先是 `Γ = S − S·Λ·S` 的恒等式（在混合约定下
    **过度松弛**，lamella 能量被压到 ~0），再是"逐基应力探针 + 行乘 G6"（连对角情形都错）。
    教训：**约定只应在一处出现** ⇒ 内部全张量，出口才用 `eng6` 转 6 分量。
 2. **判据必须包含"含剪切"的 ε⁰**。AS-1b/AS-2 的 ε⁰ 都是**对角**的 ⇒ 剪切列**从未被检验**，
    于是带 bug 的 Γ 一路"通过"到 AS-3 与 M2-D（那些数字**作废**）。
    本项目自己的教训（"设计验证算例前先问这个测试能不能看到目标现象"）在这里第二次应验。

Γ 的张量形式（由平衡方程直接推）：
    A_il = C_ijkl n_j n_k ;  û_l = −A⁻¹_{li} (n·τ)_i ;  ε = sym(n⊗û)
    ⇒ Γ_{pqij} = ½[ n_p A⁻¹_{qi} + n_q A⁻¹_{pi} ] n_j
"""
import numpy as np
from scipy import fft as sfft
from windowB_pf3d import VOIGT, G6


def eng6(e_t):
    """3x3 张量应变 -> **工程** 6 分量（剪切 ×2），与 `PF3D.e0v_eng` 同约定。"""
    return np.array([e_t[i, j] for (i, j) in VOIGT]) * G6


def gamma_tensor(C, K):
    """Γ_{pqij}(n) 的**张量**形式（(Nk,3,3,3,3)）：`ε = −Γ : τ`。
       k=0 处 A 奇异 ⇒ 用哑方向占位，调用方负责把该模式置 0（⟨ε⟩ 固定为 0）。"""
    n = np.asarray(K, float)
    nrm = np.linalg.norm(n, axis=-1, keepdims=True) + 1e-300
    n = np.where(nrm > 1e-9, n / nrm, np.array([1.0, 0.0, 0.0]))
    A = np.einsum('ijkl,nj,nk->nil', C, n, n)          # A_il
    Ai = np.linalg.inv(A)                              # A⁻¹_{li}
    G = 0.5 * (np.einsum('np,nqi,nj->npqij', n, Ai, n)
               + np.einsum('nq,npi,nj->npqij', n, Ai, n))
    return G, np.asarray(K, float)


class AnisoElastic(object):
    """参考介质 + 极化迭代 inhomogeneous 弹性（周期盒、全夹紧 ⟨ε⟩=0）。
       `C_phases`: (nph,3,3,3,3) 每相的 C；`C_ref`: 参考模量。
       `phi`: (nph,N,N,N) 相权重（和为 1）；`e0_list`: (nph,3,3) 张量特征应变。"""

    def __init__(self, N, L, C_phases, C_ref, workers=4, project_k0=True):
        self.N, self.L = N, L
        self.V = float(L) ** 3
        self.dx = L / N
        self.nph = len(C_phases)
        self.Cp = [np.asarray(C, float) for C in C_phases]
        self.Cref = np.asarray(C_ref, float)
        self.kv = 2 * np.pi * np.fft.fftfreq(N, d=self.dx)
        K = np.stack(np.meshgrid(*[self.kv] * 3, indexing='ij'), -1).reshape(-1, 3)
        self.K = K
        self.Gam, _ = gamma_tensor(self.Cref, K)
        i0 = int(np.argmin((K ** 2).sum(1)))
        if project_k0:
            self.Gam[i0] = 0.0
        self.workers = workers
        self.axs = (2, 3, 4)          # tau/eps 的形状是 (3,3,N,N,N) ⇒ 空间轴 = 2,3,4

    def _fft(self, x):
        return sfft.fftn(x, axes=self.axs, workers=self.workers)

    def _ifft(self, x):
        return sfft.ifftn(x, axes=self.axs, workers=self.workers)

    def _C_apply(self, C, e):
        """C:ε（张量），e: (3,3,N,N,N)"""
        return np.einsum('ijkl,kl...->ij...', C, e)

    def _fields(self, phi, e0_list):
        e0x = np.zeros((3, 3) + phi.shape[1:])
        for p in range(self.nph):
            e0x += phi[p] * np.asarray(e0_list[p], float)[:, :, None, None, None]
        return e0x

    def solve(self, phi, e0_list, niter=200, tol=1e-10, accel=True):
        phi = np.asarray(phi, float)
        e0x = self._fields(phi, e0_list)
        shp = (3, 3) + phi.shape[1:]
        eps = np.zeros(shp)
        eps_p = None
        hist = []
        for it in range(niter):
            el = eps - e0x
            sig = np.zeros(shp)
            for p in range(self.nph):
                sig += phi[p] * self._C_apply(self.Cp[p], el)
            tau = sig - self._C_apply(self.Cref, eps)
            th = self._fft(tau).reshape(3, 3, -1).transpose(2, 0, 1)   # (Nk,3,3)
            eh = -np.einsum('npqij,nij->npq', self.Gam, th)            # (Nk,3,3)
            enew = np.real(self._ifft(eh.transpose(1, 2, 0).reshape(
                (3, 3) + phi.shape[1:])))
            enew = 0.5 * (enew + enew.swapaxes(0, 1))                  # 保对称
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
        el = eps - e0x
        sig = np.zeros(shp)
        for p in range(self.nph):
            sig += phi[p] * self._C_apply(self.Cp[p], el)
        self.eps, self.sig = eps, sig
        return sig, eps, len(hist), hist

    def sigma6(self, *a, **kw):
        sig, eps, nit, hist = self.solve(*a, **kw)
        return np.stack([sig[i, j] for (i, j) in VOIGT]), nit, hist

    def energy(self, phi, e0_list, **kw):
        sig, eps, nit, hist = self.solve(phi, e0_list, **kw)
        e0x = self._fields(np.asarray(phi, float), e0_list)
        el = eps - e0x
        dens = np.zeros(phi.shape[1:])
        for p in range(self.nph):
            dens += 0.5 * phi[p] * np.einsum('ij...,ijkl,kl...->...', el,
                                             self.Cp[p], el)
        return float(dens.mean()) * self.V, nit, hist
