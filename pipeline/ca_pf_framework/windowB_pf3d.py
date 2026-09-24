#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_pf3d.py --- Window B 的三维局部精细 PF 引擎（马氏体变体 + FFT 微弹性）

物理（MATH_FRAMEWORK.md §5.1/§5.3/§5.4）:
    F = Int [ f_chem + Sum_v W phi_v^2 (1-phi_v)^2 + Sum_v kappa/2 |grad phi_v|^2 + f_el ] dV
    dphi_v/dt = -L_v dF/dphi_v                      (Allen-Cahn 型; 马氏体变体分数非守恒)
    f_el: sigma = C:(eps - eps0(phi)), div sigma = 0, 周期盒 + 均匀 C
          eps0(phi) = Sum_v phi_v eps0_v  =>  sigma(k) = -Lambda(n):eps0(k)  (k != 0)

== 约定（必须显式记账，改一个就全变） ==
* k=0 模式: Lambda(0) := C  <==> **clamped**（RVE 平均应变固定为 0）。
  此时 E_el = (V/2) <eps0>:C:<eps0> + (k!=0 项)，与 Khachaturyan 一致。
  换成"自由弛豫"(k=0 项置零) 会改变变体选择的自协调行为 —— 见 WINDOWB_PARAMS.md §许可范围。
* FFT 归一化（**上一版 2D 代码在这里错了，见下**）:
      eps_cont(k) = fftn(eps)/N^3        （连续傅里叶变换的离散近似）
      E_el = (V/2) Sum_k eps_cont*(k) : Lambda : eps_cont(k)
      sigma_cont(k) = -Lambda : eps_cont(k)
      sigma(x) = Sum_k sigma_cont(k) e^{ikx} = N^3 * ifftn(sigma_cont)
      ==> 直接用【未归一化】变换: sigma(x) = real(ifftn(-Lambda : fftn(eps)))
  若误用 ifftn(sigma_cont) 而不乘 N^3, sigma 会小 N^3 ~ 2e6 倍:
  弹性能(W 级)看起来"对"，但界面完全感觉不到弹性驱动力 —— 静默物理错误。
  ==> 判据 F2 用【有限差分功能导数】做正对照，专门抓这一类错。

== 界面标定（自推 + A1 判据验证） ==
  双阱 f = W phi^2 (1-phi)^2, 梯度 kappa/2|grad phi|^2; 1D 平衡 tanh 剖面 a = sqrt(kappa/2W)
  gamma = Int[kappa/2 phi'^2 + W phi^2(1-phi)^2] dx = sqrt(2 kappa W)/6 = W a / 3
  w90 = 4 atanh(0.8) a = 4.394449 a = 3.10691 sqrt(kappa/W)      (10%-90% 宽度)
       ⚠ w90 = 3.1069 *sqrt(kappa/W)*，不是 3.1069*a；两者差 sqrt(2)（本轮实测抓到过）
  ==> 由 (gamma, w90) 反解:  W = 13.18329 gamma / w90 ,  kappa = 1.36547 gamma w90
"""
import numpy as np
from scipy import fft as sfft

VOIGT = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
G6 = np.array([1.0, 1.0, 1.0, 2.0, 2.0, 2.0])      # 张量->全和 的因子（对称性）
W_GAMMA = 13.183297                                 # W     = W_GAMMA * gamma / w90
K_GAMMA = 1.365472                                  # kappa = K_GAMMA * gamma * w90
W90_OVER_A = 4.394449                               # w90 / a = 4 atanh(0.8)


def C_from_voigt(CV):
    """6x6 Voigt -> 3x3x3x3 完整弹性张量（带次对称）"""
    C = np.zeros((3, 3, 3, 3))
    for p, (i, j) in enumerate(VOIGT):
        for q, (k, l) in enumerate(VOIGT):
            C[i, j, k, l] = C[j, i, k, l] = C[i, j, l, k] = C[j, i, l, k] = CV[p, q]
    return C


def C_iso3(E, nu):
    mu = E / (2 * (1 + nu))
    lam = E * nu / ((1 + nu) * (1 - 2 * nu))
    CV = np.zeros((6, 6))
    CV[:3, :3] = lam
    CV[0, 0] = CV[1, 1] = CV[2, 2] = lam + 2 * mu
    CV[3, 3] = CV[4, 4] = CV[5, 5] = mu
    return C_from_voigt(CV)


def C_hex(C11, C12, C13, C33, C44, C66=None):
    """hcp/hex 弹性常数 -> 完整张量（c 轴 = z）"""
    if C66 is None:
        C66 = 0.5 * (C11 - C12)
    CV = np.zeros((6, 6))
    CV[0, 0] = CV[1, 1] = C11
    CV[0, 1] = CV[1, 0] = C12
    CV[0, 2] = CV[2, 0] = CV[1, 2] = CV[2, 1] = C13
    CV[2, 2] = C33
    CV[3, 3] = CV[4, 4] = C44
    CV[5, 5] = C66
    return C_from_voigt(CV)


def lambda_packed(C, K, chunk=4096, k0_mode='free'):
    """Khachaturyan 张量 Lambda(n) 的 Voigt 6x6 打包，对每个 k 给 6x6。
       定义 LambdaP[p,q] = Lambda_{VOIGT[p], VOIGT[q]}（完整张量分量, 不带因子）。
       k0_mode='clamped' -> Lambda(0) = C   （RVE 平均应变固定在 0）
       k0_mode='free'    -> Lambda(0) = 0   （traction-free: 平均应力 = 0, 盒子自由变形）
       ★ 实测: 'clamped' 会引入 ~5e8 J/m^3 的"平均场"弹性力, 它远大于可解析界面宽下的
         势垒 (7.5e7) => 纯层片被打散成多变体混合。'free' 下相容对的弹性驱动力严格为 0,
         层片稳定。对"自协调/变体选择"研究, 标准且物理的选择是 'free'。"""
    Nk = K.shape[0]
    Lp = np.zeros((Nk, 6, 6))
    for s in range(0, Nk, chunk):
        e = min(s + chunk, Nk)
        n = K[s:e]
        nrm = np.linalg.norm(n, axis=1)
        good = nrm > 1e-10
        Lam = np.zeros((e - s, 3, 3, 3, 3))
        if good.any():
            ng = n[good] / nrm[good, None]
            # ★ 声学张量 A 的正确收缩: A[j,l] = C[i,j,k,l] n_i n_k （第 1、3 指标）
            #   各向同性下应为 mu*I + (lam+mu) n n^T。写成 C_ijkl n_k n_l 会得到
            #   lam*I + 2mu n n^T —— 这样 Lambda 不再湮灭 rank-1 模式 sym(a(x)n)，
            #   层片相容性/孪晶物理全错（2026-09-24 由 rank-1 与纯体积两条解析判据抓到）。
            A = np.einsum('ijkl,bi,bk->bjl', C, ng, ng)
            Ainv = np.linalg.inv(A)
            #   Lambda = C - C1,  C1[k,l,q,r] = C[i,j,k,l] n_i A^{-1}[j,m] n_p C[p,m,q,r]
            G1 = np.einsum('ijkl,bi,bjm,bp,pmqr->bklqr', C, ng, Ainv, ng, C)
            Lam[good] = C[None, :, :, :, :] - G1
        Lam[~good] = C[None, :, :, :, :] if k0_mode == 'clamped' else 0.0
        for p, (i, j) in enumerate(VOIGT):
            for q, (k, l) in enumerate(VOIGT):
                Lp[s:e, p, q] = Lam[:, i, j, k, l]
    return Lp


def e_density(C, e0, n):
    """单模式弹性能密度 0.5 e0:Lambda(n):e0（解析用）"""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    A = np.einsum('ijkl,k,l->ij', C, n, n)
    C1 = np.einsum('ijmn,n,mp,q,pqkl->ijkl', C, n, np.linalg.inv(A), n, C)
    return 0.5 * np.einsum('ij,ijkl,kl->', e0, C - C1, e0)


class PF3D(object):
    def __init__(self, N, L, C, eps0, gamma, w90, Lmob, dG=0.0, sigma_ext=None,
                 workers=8, obstacle=False, k0_mode='free'):
        self.k0_mode = k0_mode
        self.N, self.L, self.dim = N, L, 3
        self.C = C
        self.V = float(L) ** 3
        self.dx = L / N
        self.eps0 = np.asarray(eps0, float)
        self.nv = len(self.eps0)
        self.gamma, self.w90 = gamma, w90
        # ★ 界面势有两种; 见文件头"界面势"一节。**默认 obstacle=False**（2026-09-24 甄别结论）:
        #   obstacle=True: f_int = W Sum_{a<b} phi_a phi_b  —— 多相场"双障碍"势。
        #       它强力惩罚"同一格点被多个变体分享"，故"每格单一变体"是稳定解。
        #       标定: gamma = W w /4,  w = pi sqrt(kappa/2W)  =>  W = 4gamma/w, kappa = 8 gamma w/pi^2
        #       ⚠ 但它要求 Delta f > W 才能推进界面（v=0 否则）——那是"形核势垒"语义,
        #         不适合描述【被驱动的界面传播】。
        #   obstacle=False (默认): f_int = W Sum_{a<b} phi_a^2 phi_b^2 （四次/双阱）,
        #       传播动力学 v ∝ L*Delta f 与 W 无关（标准 Allen-Cahn 行为）⇒ 适合马氏体。
        #       它的代价: 稀释混合在四次势下几乎免费（12 变体各 3% 只需 ~1e-5 W）,
        #       所以【必须】配 k0_mode='free'，否则被平均场弹性力打散（实测见 _scan_forms.py）。
        self.obstacle = obstacle
        if obstacle:
            self.W = 4.0 * gamma / w90
            self.kappa = 8.0 * gamma * w90 / np.pi ** 2
        else:
            self.W = W_GAMMA * gamma / w90
            self.kappa = K_GAMMA * gamma * w90
        self.Lmob = Lmob
        self.dG = dG
        self.sigma_ext = np.zeros((3, 3)) if sigma_ext is None else np.asarray(sigma_ext, float)
        self.workers = workers
        self.phi = np.zeros((self.nv, N, N, N))
        # 变体的 6 分量张量分量 & 工程分量
        self.e0v = np.array([[self.eps0[v][i, j] for (i, j) in VOIGT] for v in range(self.nv)])
        self.e0v_eng = self.e0v * G6[None, :]
        self.sext_e0 = np.array([np.einsum('ij,ij->', self.sigma_ext, self.eps0[v])
                                 for v in range(self.nv)])
        self.kv = 2 * np.pi * np.fft.fftfreq(N, d=self.dx)
        K = np.stack(np.meshgrid(*[self.kv] * 3, indexing='ij'), -1).reshape(-1, 3)
        self.K = K
        self.Lam = lambda_packed(C, K, k0_mode=k0_mode)
        self.N3 = float(N) ** 3
        self._k2 = (K ** 2).sum(1)
        self.axs = (1, 2, 3)

    # ---------------- 场 ----------------
    def eps0_fields(self):
        e = np.zeros((6, self.N, self.N, self.N))
        for p in range(6):
            for v in range(self.nv):
                e[p] += self.e0v[v, p] * self.phi[v]
        return e

    def _fft(self, x):
        return sfft.fftn(x, axes=self.axs, workers=self.workers)

    def _ifft(self, x):
        return sfft.ifftn(x, axes=self.axs, workers=self.workers)

    def _epsh(self):
        """工程应变分量的未归一化 FFT: (6, N,N,N)"""
        e = self.eps0_fields()
        e[3:] *= 2.0
        return self._fft(e)

    def sigma_tensor(self):
        """sigma(x) = real(ifftn(-Lambda : fftn(eps)))  （见文件头归一化说明）"""
        Eh = self._epsh().reshape(6, -1)
        sh = -np.einsum('kpq,qk->pk', self.Lam, Eh)
        sh = sh.reshape((6, self.N, self.N, self.N))
        return np.real(self._ifft(sh))

    def E_el(self):
        Eh = self._epsh().reshape(6, -1) / self.N3
        return 0.5 * self.V * float(np.real(np.einsum('pk,kpq,qk->', np.conj(Eh), self.Lam, Eh)))

    def E_chem_grad(self):
        """返回 (E_barrier, E_chem, E_grad)"""
        Eb = Eg = Ec = 0.0
        cell = self.dx ** 3
        n0 = np.clip(1.0 - self.phi.sum(0), 0.0, 1.0)
        phi_all = np.concatenate([n0[None], self.phi], 0)
        S2 = (phi_all ** 2).sum(0)
        if self.obstacle:
            Eb = float(self.W * 0.5 * np.sum(1.0 - S2) * cell)   # Sum_{a<b} phi_a phi_b
        else:
            Eb = float(np.sum(self.W * 0.5 * (S2 ** 2 - (phi_all ** 4).sum(0))) * cell)
        Ec = float(-self.dG * np.sum(1.0 - n0) * cell)
        for v in range(self.nv):
            p = self.phi[v]
            for ax in range(p.ndim):
                g = np.roll(p, -1, axis=ax) - p
                Eg += 0.5 * self.kappa * np.sum(g ** 2) / self.dx ** 2 * cell
        return Eb, Ec, Eg

    def E_total(self):
        Eb, Ec, Eg = self.E_chem_grad()
        return self.E_el() + Eb + Ec + Eg

    # ---------------- 力与时间步 ----------------
    def forces(self):
        sig = self.sigma_tensor()
        f = np.zeros_like(self.phi)
        m = self.phi.sum(0)                                  # 总转变分数
        S2 = (self.phi ** 2).sum(0)
        drive = self.dG * 6 * m * (1 - m)                     # d/dm[-dG m^2(3-2m)] 的驱动力
        for v in range(self.nv):
            f[v] = -np.einsum('p,p...->...', self.e0v_eng[v], sig) + self.sext_e0[v]
            p = self.phi[v]
            f[v] += drive - self.W * (2 * p * (1 - p) * (1 - 2 * p)
                                      + 2 * p * (S2 - p ** 2))
        return f, sig

    def laplacian(self, p):
        lap = -2.0 * self.dim * p
        for ax in range(p.ndim):            # p 是单个标量场 (N,N,N)
            lap = lap + np.roll(p, 1, axis=ax) + np.roll(p, -1, axis=ax)
        return lap / self.dx ** 2

    # ---- 多相场成对形式（MATH_FRAMEWORK §5.3）----
    #  13 个相: alpha=0 是母相 beta, 1..nv 是 12 个变体; 约束 Sum_alpha phi_alpha = 1 由构造保证
    #   f_int = Sum_{a<b} W phi_a^2 phi_b^2 ,  f_chem = -dG Sum_{v>=1} phi_v （只对变体给驱动）
    #   dphi_v/dt = -L [ dF/dphi_v - (1/13) Sum_alpha dF/dphi_alpha ]
    #  ★ 这样"Σφ>1"根本不会出现：不需要投影/归一，也不会有 12 个变体各长到 1 的问题。
    def dfdphi(self):
        n0 = 1.0 - self.phi.sum(0)
        n0 = np.clip(n0, 0.0, 1.0)
        phi_all = np.concatenate([n0[None], self.phi], 0)       # (1+nv, N,N,N)
        m = phi_all.sum(0)
        if self.obstacle:
            out = self.W * (m[None] - phi_all)                  # d/dphi_a [W Sum_{a<b} phi_a phi_b]
        else:
            S2 = (phi_all ** 2).sum(0)
            out = 2.0 * self.W * phi_all * (S2 - phi_all ** 2)  # 四次/双阱
        sig = self.sigma_tensor()
        for v in range(self.nv):
            out[1 + v] += -self.dG - np.einsum('p,p...->...', self.e0v_eng[v], sig) \
                + self.sext_e0[v]
        return n0, phi_all, out, sig

    def step(self, dt):
        """半隐式谱步：把最刚的 -kappa*grad^2 项做隐式，彻底解除 dt ~ dx^2/(kappa L) 限制。
           dphi_v/dt = -L[(df/dphi_v - mean) - kappa lap(phi_v)]
           => 在 k 空间  phin = (ph - dt L * fft(df/dphi_v - mean)) / (1 + dt L kappa k^2)
           ★ 显式格式在薄界面下超标（实测 dt=1.6e-11 vs 极限 4.8e-12），会发散把结构冲掉。"""
        n0, phi_all, dF, _ = self.dfdphi()
        mean = dF.mean(0)                                       # (1/13) Sum_alpha dF/dphi_alpha
        g = dF[1:] - mean[None]
        gh = self._fft(g)
        ph = self._fft(self.phi)
        fac = 1.0 + dt * self.Lmob * self.kappa * self._k2.reshape((self.N,) * self.dim)
        self.phi = np.real(self._ifft((ph - dt * self.Lmob * gh) / fac))
        np.clip(self.phi, 0.0, 1.0, out=self.phi)
        s = self.phi.sum(0)                                     # 安全网（应为 1，仅修舍入）
        bad = s > 1.0
        if bad.any():
            self.phi[:, bad] /= s[bad]

    def step_explicit_cap(self, dt):
        """旧版（显式 + 投影）保留作对照；已知会把混合态摊平，不推荐"""
        f, _ = self.forces()
        for v in range(self.nv):
            self.phi[v] += dt * self.Lmob * (f[v] + self.kappa * self.laplacian(self.phi[v]))
        np.clip(self.phi, 0.0, 1.0, out=self.phi)
        s = self.phi.sum(0)
        bad = s > 1.0
        if bad.any():
            self.phi[:, bad] /= s[bad]

    # ---------------- 工具 ----------------
    def f_of_eps(self, eps):
        """给定 eps 张量, 返回 6 分量张量向量"""
        return np.array([eps[i, j] for (i, j) in VOIGT])


# ==================================================================== 判据
def test_A0(dim=3):
    print('---- A0: 微弹性谱法解析判据（三维）----')
    N, L = 16, 1e-7
    C = C_iso3(100e9, 0.3)
    e0 = np.array([[0.06, 0.04, 0.0], [0.04, -0.03, 0.01], [0.0, 0.01, -0.02]])
    ok = True
    for mode, Eth in (('clamped', 0.5 * L ** 3 * np.einsum('ij,ijkl,kl->', e0, C, e0)),
                      ('free', 0.0)):
        pf = PF3D(N, L, C, e0[None], gamma=0.0, w90=1e-8, Lmob=0.0, workers=1,
                  k0_mode=mode)
        pf.phi[0] = 1.0
        En = pf.E_el()
        rel = abs(En - Eth) / max(abs(Eth), 1e-30)
        print('  A0a 均匀 eps0 [%s]: E=%.6e vs 解析 %.6e  相对差 %.1e  %s'
              % (mode, En, Eth, rel, 'PASS' if rel < 1e-10 else 'FAIL'))
        ok &= rel < 1e-10
    pf = PF3D(N, L, C, e0[None], gamma=0.0, w90=1e-8, Lmob=0.0, workers=1, k0_mode='free')

    k0 = 2 * np.pi / L * np.array([1.0, 2.0, 1.0])
    X = np.arange(N)[:, None, None] * pf.dx
    Y = np.arange(N)[None, :, None] * pf.dx
    Z = np.arange(N)[None, None, :] * pf.dx
    amp = 0.2
    pf.phi[0] = 0.5 + amp * np.cos(k0[0] * X + k0[1] * Y + k0[2] * Z)
    E_k0 = 2 * 0.5 * L ** 3 * (amp / 2) ** 2 * np.einsum('ij,ijkl,kl->', e0, _lam_full(C, k0), e0)
    for mode in ('clamped', 'free'):
        pf = PF3D(N, L, C, e0[None], gamma=0.0, w90=1e-8, Lmob=0.0, workers=1, k0_mode=mode)
        pf.phi[0] = 0.5 + amp * np.cos(k0[0] * X + k0[1] * Y + k0[2] * Z)
        En = pf.E_el()
        E_DC = (0.5 * L ** 3 * (0.5 ** 2) * np.einsum('ij,ijkl,kl->', e0, C, e0)
                if mode == 'clamped' else 0.0)
        Eth = E_DC + E_k0
        print('  A0b 单模式 [%s]: E=%.6e vs 闭式=%.6e  相对差 %.1e  %s'
              % (mode, En, Eth, abs(En - Eth) / abs(Eth), 'PASS' if abs(En - Eth) / abs(Eth) < 1e-9 else 'FAIL'))
        ok &= abs(En - Eth) / abs(Eth) < 1e-9
    return ok


def _lam_full(C, k):
    n = np.asarray(k, float)
    n = n / np.linalg.norm(n)
    A = np.einsum('ijkl,i,k->jl', C, n, n)              # A[j,l] = C[i,j,k,l] n_i n_k
    C1 = np.einsum('ijkl,i,jm,p,pmqr->klqr', C, n, np.linalg.inv(A), n, C)
    return C - C1


def test_F1():
    """sigma 管线正对照: 均匀 eps0 => sigma = -C:eps0 （逐位）"""
    print('---- F1: sigma 管线对照（均匀 eps0 => sigma = -C:e0，位级）----')
    N, L = 8, 1e-8
    C = C_iso3(100e9, 0.3)
    e0 = np.array([[0.01, 0.002, 0.0], [0.002, -0.004, 0.0], [0.0, 0.0, 0.003]])
    ok = True
    for mode, San in (('clamped', -np.einsum('ijkl,kl->ij', C, e0)),
                      ('free', np.zeros((3, 3)))):
        pf = PF3D(N, L, C, e0[None], gamma=0.0, w90=1e-8, Lmob=0.0, workers=1, k0_mode=mode)
        pf.phi[0] = 1.0
        sig = pf.sigma_tensor()
        err = max(np.abs(sig[p, ...] - San[i, j]).max() for p, (i, j) in enumerate(VOIGT))
        sc = max(np.abs(San).max(), 1e-30)
        print('  [%s] max|sigma - sigma_ana| / |sigma_ana| = %.2e   %s'
              % (mode, err / sc if San.any() else err, 'PASS' if (err / sc if San.any() else err) < 1e-12 else 'FAIL'))
        ok &= (err / sc if San.any() else err) < 1e-12
    return ok


def test_F2():
    """功能导数正对照: dE_el/dphi_v(x) 必须等于 -e0_v:sigma(x)"""
    print('---- F2: 功能导数有限差分对照（抓 FFT 归一化错）----')
    N, L, nv = 12, 1e-7, 2
    C = C_iso3(100e9, 0.3)
    rng = np.random.default_rng(3)
    eps = np.array([np.array([[0.05, 0.02, 0.0], [0.02, -0.03, 0.0], [0.0, 0.0, -0.02]]),
                    np.array([[-0.04, 0.0, 0.01], [0.0, 0.06, -0.01], [0.01, -0.01, -0.02]])])
    pf = PF3D(N, L, C, eps, gamma=0.0, w90=1e-8, Lmob=0.0, workers=1)
    pf.phi[0] = 0.5 + 0.3 * rng.random((N, N, N))
    pf.phi[1] = 1.0 - pf.phi[0]
    f, sig = pf.forces()
    idx = (3, 5, 7)
    v = 0
    an = f[v][idx]                                     # 泛函导数 = -e0_v:sigma  (J/m^3)
    errs, fds = [], []
    for d in (1e-4, 1e-5, 1e-6):
        E0 = pf.E_el()
        pf.phi[v][idx] += d
        E1 = pf.E_el()
        pf.phi[v][idx] -= d
        fd = (E1 - E0) / (d * pf.dx ** 3)              # 泛函导数: 必须除体元
        errs.append(abs(fd - an) / abs(an))
        fds.append(fd)
    print('  delta = 1e-4/1e-5/1e-6 的相对差 = %.2e / %.2e / %.2e  (应随 delta 线性下降)'
          % tuple(errs))
    print('  dE/dphi_%d%s (FD,delta=1e-6) = %+.8e ;  -e0:sigma (解析) = %+.8e   %s'
          % (v, idx, fds[-1], an, 'PASS' if errs[-1] < 1e-4 else 'FAIL'))
    # 注: FD 精度地板实测 ~4e-6（在 E_el ~1e-13 J 上做有限差分），故判据取 1e-4
    return errs[-1] < 1e-4 and errs[0] > errs[-1]


def test_A0cd():
    """Lambda 的两条【已知解析答案】——这两条才真正约束 A 的收缩方式
       A0c  rank-1 相容模式 eps = sym(a(x)n)  =>  eps:Lambda(n):eps = 0 （精确）
       A0d  纯体积 eps = e0*I            =>  0.5 eps:Lambda(n):eps = 2 mu e0^2 (1+nu)/(1-nu)
       （注意: 均匀 eps0、单 Fourier 模式、纯剪切特征 这三条判据【都检测不到】A 的错，
        因为它们对 n 的依赖退化了 —— 这正是之前"测试全过但物理是错的"的原因。）"""
    print('---- A0c/A0d: Lambda 的 rank-1 湮灭 与 纯体积闭式（敏感判据）----')
    E_mod, nu = 113e9, 0.34
    C = C_iso3(E_mod, nu)
    mu = E_mod / (2 * (1 + nu))
    rng = np.random.default_rng(0)
    w1 = 0.0
    for _ in range(5):
        a = rng.normal(size=3)
        n = rng.normal(size=3)
        a /= np.linalg.norm(a)
        n /= np.linalg.norm(n)
        eps = 0.5 * (np.outer(a, n) + np.outer(n, a))
        v = float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))
        w1 = max(w1, abs(v) / (mu * np.sum(eps ** 2)))
    print('  [A0c] max |eps:Lam:eps| /(mu|eps|^2) = %.2e   %s'
          % (w1, 'PASS' if w1 < 1e-12 else 'FAIL'))
    w2 = 0.0
    e0 = 0.01
    for nn in ([1, 0, 0], [1, 1, 0], [0.3, -0.5, 0.81]):
        n = np.array(nn, float)
        n /= np.linalg.norm(n)
        v = 0.5 * float(np.einsum('ij,ijkl,kl->', e0 * np.eye(3), _lam_full(C, n), e0 * np.eye(3)))
        vth = 2 * mu * e0 ** 2 * (1 + nu) / (1 - nu)
        w2 = max(w2, abs(v - vth) / vth)
    print('  [A0d] 纯体积 vs 2 mu e0^2 (1+nu)/(1-nu) 最大相对差 = %.2e   %s'
          % (w2, 'PASS' if w2 < 1e-12 else 'FAIL'))
    return w1 < 1e-12 and w2 < 1e-12


def test_A1():
    """界面标定: 解析 tanh 剖面上测 w90 与 gamma，与 (W,kappa) 反解式的往返一致"""
    print('---- A1: (gamma, w90) <-> (W, kappa) 往返 + 离散化误差 ----')
    Nx, dx = 8192, 5e-10
    ok = True
    for gam_t, w90_t in ((0.15, 4e-8), (0.15, 2e-8), (0.30, 4e-8)):
        W = W_GAMMA * gam_t / w90_t
        kap = K_GAMMA * gam_t * w90_t
        a = np.sqrt(kap / (2 * W))
        x = np.arange(Nx) * dx
        p = 0.5 * (1 - np.tanh((x - Nx * dx / 2) / (2 * a)))
        g = np.gradient(p, dx)
        gam_num = float(np.sum(kap / 2 * g ** 2 + W * p ** 2 * (1 - p) ** 2) * dx)
        # 直接测 w90: 10% 与 90% 位置
        lo = np.interp(0.9, p[::-1], x[::-1])          # p 随 x 单调递减, interp 要求 xp 递增
        hi = np.interp(0.1, p[::-1], x[::-1])
        w90_num = hi - lo
        print('  gamma_in=%.3f w90_in=%.1e nm -> gamma_num=%.5f (差 %+.2f%%)  w90_num=%.3e nm (比 %.4f)'
              % (gam_t, w90_t * 1e9, gam_num, 100 * (gam_num / gam_t - 1), w90_num * 1e9,
                 w90_num / w90_t))
        ok &= abs(gam_num / gam_t - 1) < 5e-3 and abs(w90_num / w90_t - 1) < 1e-2
    print('  判定: %s' % ('PASS' if ok else 'FAIL'))
    return ok


if __name__ == '__main__':
    print('=' * 96)
    print('Window B 三维 PF 引擎: 解析判据')
    print('=' * 96)
    res = {}
    res['A0'] = test_A0()
    res['A0cd'] = test_A0cd()
    res['A1'] = test_A1()
    res['F1'] = test_F1()
    res['F2'] = test_F2()
    print('\n' + '=' * 96)
    print('总判定: %s' % ('ALL PASS' if all(res.values()) else 'FAIL -> ' + str(
        [k for k, v in res.items() if not v])))
    raise SystemExit(0 if all(res.values()) else 1)
