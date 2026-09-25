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

★★ 记账（**我踩过的坑，必须记**）：
 0. **两套约定必须只用一处**：本仓库同时存在"张量分量无因子"（`lambda_packed`）与
    "工程应变剪切 ×2"（`PF3D._epsh`）。我两次手推 Γ 的**打包**都错在**剪切列**上：
    ① `Γ = S − S·Λ·S`（k=0 自洽，但混合约定下**过度松弛**，lamella 能量被压到 ~0）；
    ② "逐基应力探针 + 行乘 G6"（连对角情形都错）。
 1. ★★ **判据必须包含"含剪切"的 ε⁰**。AS-1b/AS-2 初版 ε⁰ 都是**对角**的 ⇒ 剪切列**从未被
    检验** ⇒ 带 bug 的 Γ 一路"通过"到 AS-3 与 M2-D（那些数字**作废重算**）。
    本项目自己的教训"设计验证算例前先问这个测试能不能看到目标现象"**第二次**应验。
   ⇒ 最终方案：**Γ 的构造在纯张量空间完成**（从平衡方程直接推，`gamma_tensor`），
     再用**对基应力打表**的方式把它转成 6×6（`gamma_packed`）—— 这样"约定"只在
     `eng6` 一处出现，且转换是**从已验证的张量做探针**，不可能再错。
 2. **性能**：初版在每次迭代里对每个相做一次完整 4 阶收缩（nph×81·N³）⇒ N=100 时
    **52 s/步**（非各向异性档只要 2.3 s）。现在"本构"部分预先攒成 6×6 的 `C(x)` 场
    （36·N³），只有 Γ 保持张量式构造并打表为 6×6 ⇒ 单步回到与 `PF3D` 同量级。
"""
import numpy as np
from scipy import fft as sfft
from windowB_pf3d import VOIGT, G6


def voigt_of(C):
    return np.array([[C[VOIGT[p][0], VOIGT[p][1], VOIGT[q][0], VOIGT[q][1]]
                      for q in range(6)] for p in range(6)])


def eng6(e_t):
    """3x3 张量应变 -> **工程** 6 分量（剪切 ×2），与 `PF3D.e0v_eng` 同约定。"""
    return np.array([e_t[i, j] for (i, j) in VOIGT]) * G6


def _stress_basis(q):
    """第 q 个 Voigt 基应力（**对称张量**；Voigt 分量即张量分量，不乘因子）。"""
    i, j = VOIGT[q]
    T = np.zeros((3, 3))
    T[i, j] = 1.0
    T[j, i] = 1.0
    return T


def gamma_tensor(C, K):
    """Γ_{pqij}(n) 的**张量**形式（(Nk,3,3,3,3)）：`ε = −Γ : τ`。
       由平衡方程直接推：A_il = C_ijkl n_j n_k ; û = −A⁻¹(n·τ) ; ε = sym(n⊗û)
       ⇒ Γ_{pqij} = ½[ n_p A⁻¹_{qi} + n_q A⁻¹_{pi} ] n_j。
       k=0 处 A 奇异 ⇒ 用哑方向占位，调用方把该模式置 0（⟨ε⟩ 固定为 0）。"""
    n = np.asarray(K, float)
    nrm = np.linalg.norm(n, axis=-1, keepdims=True) + 1e-300
    n = np.where(nrm > 1e-9, n / nrm, np.array([1.0, 0.0, 0.0]))
    A = np.einsum('ijkl,nj,nk->nil', C, n, n)
    Ai = np.linalg.inv(A)
    return 0.5 * (np.einsum('np,nqi,nj->npqij', n, Ai, n)
                  + np.einsum('nq,npi,nj->npqij', n, Ai, n))


def gamma_packed(C, K):
    """把**已验证的张量** Γ 打表成 6×6：`e^eng = −Γq·τvec`。
       ★ 做法：对 6 个基应力张量 τ^(q) 逐个施加 Γ_t，把结果**按工程约定**打包成第 q 列
         （`e^eng_p = G6[p]·ε_{VOIGT[p]}`）。⇒ 打包约定只出现在 `eng6` 一处，
         且这是"从张量做探针"，不是手推公式 ⇒ 不会重犯剪切列的错。"""
    G4 = gamma_tensor(C, K)
    Nk = len(K)
    out = np.zeros((Nk, 6, 6))
    for q in range(6):
        T = _stress_basis(q)
        eps_t = -np.einsum('npqij,ij->npq', G4, T)      # 张量应变
        #   eps_t 形状 (Nk,3,3) ⇒ 逐 Voigt 分量取出来、剪切乘 2（工程约定），再取负
        ee = np.array([eps_t[:, i, j] for (i, j) in VOIGT]) * G6[:, None]
        out[:, :, q] = -ee.T
    return out


class AnisoElastic(object):
    """参考介质 + 极化迭代 inhomogeneous 弹性（周期盒、全夹紧 ⟨ε⟩=0）。
       `C_phases`: (nph,3,3,3,3) 每相的 C；`C_ref`: 参考模量；
       `phi`: (nph,N,N,N) 相权重（和为 1）；`e0_list`: (nph,3,3) 张量特征应变。
       返回的 σ 是**工程 6 分量**（与 `PF3D.sigma_tensor()` 逐位一致，AS-1/AS-1b 实测）。"""

    def __init__(self, N, L, C_phases, C_ref, workers=4, project_k0=True):
        self.N, self.L = N, L
        self.V = float(L) ** 3
        self.dx = L / N
        self.nph = len(C_phases)
        self.CV = np.array([voigt_of(C) for C in C_phases])     # (nph,6,6)
        self.Cref6 = voigt_of(C_ref)
        self.kv = 2 * np.pi * np.fft.fftfreq(N, d=self.dx)
        K = np.stack(np.meshgrid(*[self.kv] * 3, indexing='ij'), -1).reshape(-1, 3)
        self.K = K
        self.Gam = gamma_packed(C_ref, K)
        i0 = int(np.argmin((K ** 2).sum(1)))
        if project_k0:
            self.Gam[i0] = 0.0
        self.workers = workers
        self.axs = (1, 2, 3)

    def _fft(self, x):
        return sfft.fftn(x, axes=self.axs, workers=self.workers)

    def _ifft(self, x):
        return sfft.ifftn(x, axes=self.axs, workers=self.workers)

    def solve(self, phi, e0_list, niter=200, tol=1e-10, accel=True, init=None):
        phi = np.asarray(phi, float)
        shp = (6,) + phi.shape[1:]
        CVx = np.tensordot(self.CV, phi, axes=(0, 0))            # (6,6,N,N,N)
        e0x = np.zeros(shp)
        for p in range(self.nph):
            e0x += phi[p] * eng6(np.asarray(e0_list[p], float)).reshape(6, 1, 1, 1)
        Cdiff = CVx - self.Cref6.reshape(6, 6, 1, 1, 1)
        # ★ 记账（性能）：支持**热启动** —— 相邻两步的应变场差别很小，用上一步的 ε 当初值
        #   可把迭代数从 ~35 降到个位数（`LevelSetMulti.elastic_driving` 已接）。
        eps = (np.zeros(shp) if init is None or np.shape(init) != shp
               else np.array(init, float, copy=True))
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
        self.CVx = CVx
        self.eps = eps
        return sig, eps, len(hist), hist

    def sigma6(self, phi, e0_list, **kw):
        """同 `solve`，但只回 σ 的 6 分量（+ 迭代数/历史），供 `PF3D` 口径调用。"""
        sig, eps, nit, hist = self.solve(phi, e0_list, **kw)
        return sig, nit, hist

    def energy(self, phi, e0_list, **kw):
        sig, eps, nit, hist = self.solve(phi, e0_list, **kw)
        el = eps - self._e0x(np.asarray(phi, float), e0_list)
        dens = 0.5 * np.einsum('p...,pq...,q...->...', el, self.CVx, el)
        return float(dens.mean()) * self.V, nit, hist

    def _e0x(self, phi, e0_list):
        shp = (6,) + phi.shape[1:]
        e0x = np.zeros(shp)
        for p in range(self.nph):
            e0x += phi[p] * eng6(np.asarray(e0_list[p], float)).reshape(6, 1, 1, 1)
        return e0x
