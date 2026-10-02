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

import windowB_acct as acct
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


def C_cubic(C11, C12, C44):
    """立方（bcc/fcc）弹性常数 -> 完整张量（4 重轴 = x/y/z）。
       ★ 判据见 `_chk_hex.py` HX-7：90°/180° 绕 x/y/z 的不变性在机器精度内成立。"""
    CV = np.zeros((6, 6))
    CV[0, 0] = CV[1, 1] = CV[2, 2] = C11
    CV[0, 1] = CV[1, 0] = CV[0, 2] = CV[2, 0] = CV[1, 2] = CV[2, 1] = C12
    CV[3, 3] = CV[4, 4] = CV[5, 5] = C44
    return C_from_voigt(CV)


def C_rot4(C, R):
    """把 4 阶弹性张量按**材料系转动** R 转到实验室系：C'_{ijkl} = R_ia R_jb R_kc R_ld C_abcd。
       对 hcp（横向各向同性）张量，转动只需给出 c 轴的去向 —— 绕 c 轴的面内转角不影响 C ✓
       （这一点在 `_chk_hex.py` HX-6 用 Kelvin 谱 + 迹不变量复核）。"""
    R = np.asarray(R, float)
    return np.einsum('ia,jb,kc,ld,abcd->ijkl', R, R, R, R, C)


def rot_z_to(n):
    """给出任一正交阵 R 使 R @ ẑ = n̂（用于把 hcp 张量的 c 轴转到 n̂）。"""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(z, n)
    na = np.linalg.norm(ax)
    if na < 1e-12:
        return np.eye(3) if n[2] > 0 else np.diag([1.0, -1.0, -1.0])
    ax = ax / na
    th = np.arccos(np.clip(z @ n, -1.0, 1.0))
    Kx = np.array([[0.0, -ax[2], ax[1]], [ax[2], 0.0, -ax[0]], [-ax[1], ax[0], 0.0]])
    return np.eye(3) + np.sin(th) * Kx + (1.0 - np.cos(th)) * (Kx @ Kx)


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
    """
    ★★★ R561–R567（算子优化，**全部默认关**）★★★
    ---------------------------------------------------------------
    本轮对**弹性热路径**做了逐算子审计（量具：`_r561_opfacct.py` 记账、
    `_r562_opbench.py` 替身擂台、`_r566_b4iso.py` / `_r567_nyqfix.py` 隔离与修正），
    在**生产宿主**（WSL + conda `ml`，numpy 2.5.3）上实测：

    | 开关 | 改什么 | 实测加速 | 与旧路的差 |
    |---|---|---|---|
    | `eps0_mode='einsum'` | `6×nv` 次整场 `+=` → `einsum('vp,v...->p...')` | **1.76×** | **0.000e+00（逐位）** |
    | `eps0_mode='gemm'`   | 同上 → BLAS `e0v.T @ phi2d` | **18.1×** | 2.7e-16（1–2 ulp） |
    | `fft_mode='rfft'`    | `fftn/ifftn`(c2c 全谱) → `rfftn/irfftn`(半谱) | **1.71×**（整链） | **6.1e-16** |
    | `lam_prec='f32'`    | （旧开关，非本轮） | — | 见 T3 |

    ⚠⚠ **`fft_mode='rfft'` 为什么必须配 Nyquist 修正**（`§R567`，本轮新发现）：
      `σ = real(ifftn(−Λ ⊙ fftn(ε)))` 里的 `real(...)` **一直在隐式做 Hermite 投影**
      （`real(ifftn(X)) = ifftn(½(X + conj(X∘mirror)))`）。而 `sh = −Λ⊙Eh` 在
      **三个 Nyquist 面**（i=N/2 / j=N/2 / m=N/2）上**不是 Hermite 的**——因为
      `kv[N/2] = −π/dx`，它的负 `+π/dx` **不在格点上**，所以索引镜像给出的 k **向量**
      不是 `−κ`，于是 `Λ(κ(mirror)) ≠ Λ(κ)`（实测 `|ΔΛ|/max|Λ| = 3.25e-01`）。
      `irfftn` 用的是**未投影**的半谱 ⇒ 与旧路差 **6.33e-2**（占 max|σ|，够大，不能忽略）。
      **修法（`§R567` N1 实测 6.1e-16，且非 Nyquist 处逐位为 0 ⇒ 热路径零代价）**：
          `Λ_eff = Λ(κ)`                          （非 Nyquist 面）
          `Λ_eff = ½[Λ(κ) + Λ(κ(mirror))]`          （Nyquist 面）
      于是 `irfftn(−Λ_eff ⊙ rfftn(ε)) ≡ real(ifftn(−Λ ⊙ fftn(ε)))`（到舍入）。
      顺带收益：`Lam` 常驻 **288 → 144 B/胞**、谱内存减半。
    """

    def __init__(self, N, L, C, eps0, gamma, w90, Lmob, dG=0.0, sigma_ext=None,
                 workers=8, obstacle=False, k0_mode='free', T=None, dG_of_T=None,
                 phi_dtype=np.float64, lam_prec='f64',
                 fft_mode='c2c', eps0_mode='loop'):
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
        # ---- T2.1b (2026-09-25): T 依赖驱动力的入口 ----
        #    dG_of_T 是**可调用** dG(T)（见 windowB_km.dG_chem）。给了它 + T 就按 T 设 dG；
        #   不给则完全维持旧行为（常数 dG）。**热循环 / athermal 相变必须用 set_T() 改温度**，
        #   而不是重建对象（重建会丢掉场）。
        #   ⚠ athermal 语义：马氏体没有热激活 ⇒ 每个 T 上系统跑到该 T 的**平衡分数** f_eq(T)；
        #     动力学只决定"多快到达"，不决定"到达哪"。判据 T2.1b-3 用这条做指纹。
        self.dG_of_T = dG_of_T
        self.T = T
        self.dG = float(dG_of_T(T)) if (dG_of_T is not None and T is not None) else dG
        self.sigma_ext = np.zeros((3, 3)) if sigma_ext is None else np.asarray(sigma_ext, float)
        self.workers = workers
        # ★ T3：`self.phi` 的分配移到下面（与 `Lam` 一起，见 phi_dtype/lam_prec 的记账）
        # 变体的 6 分量张量分量 & 工程分量
        self.e0v = np.array([[self.eps0[v][i, j] for (i, j) in VOIGT] for v in range(self.nv)])
        self.e0v_eng = self.e0v * G6[None, :]
        self.sext_e0 = np.array([np.einsum('ij,ij->', self.sigma_ext, self.eps0[v])
                                 for v in range(self.nv)])
        self.kv = 2 * np.pi * np.fft.fftfreq(N, d=self.dx)
        with acct.bcost('build.kgeom'):
            K = np.stack(np.meshgrid(*[self.kv] * 3, indexing='ij'), -1).reshape(-1, 3)
        self.K = K
        acct.bmem('build.kgeom.bytes', K)
        # ★★ T3（2026-09-28）：`Lam` 是**常驻最大单项**（(N³,6,6) float64 = **288 B/胞**，
        #   N=96 时 255 MB）。它是 FFT 空间的 Green 算子，量级 O(1)、条件数 O(1)，
        #   用 float32 存的相对误差 ~1e-7（判据要求 <1e-5，见 T3_verify_fastpath 的正对照）
        #   ⇒ 288 → 144 B/胞。`sigma_tensor` 的 einsum **强制 float32 输出**，
        #   否则 numpy 会把 Lam 升成 float64 临时量（反而多 255 MB）。
        #   `E_el()` 是**诊断路径**（不在每步热路径上），它显式升到 float64（有一次性临时量）。
        self.phi_dtype = phi_dtype
        self.phi = np.zeros((self.nv, N, N, N), dtype=phi_dtype)
        # ★★★ R579（goal §4）：**流式 ε⁰** 的两个挂钩。
        #   `_h_src = None`（默认）⇒ 走旧的"读 `self.phi`"路 ⇒ **逐位不变**。
        #   `_h_src = callable(v0, v1) -> (v1-v0,N,N,N)` 时，`eps0_fields()` 改走
        #   `eps0_fields_stream()` ⇒ **不需要** `pf.phi` 那个 (nv,N³) float64 常驻数组。
        self._h_src = None
        self._h_chunk = 4
        # ★★★ R580（P1）：诊断专用的"弹性求解那一刻的 ε⁰"（`(6,N³)` f64 = 48 B/胞固定）。
        #   `None` = 还没有过弹性求解 ⇒ 物化路径下那时 `pf.phi` 是全零 bool ⇒ ε⁰ ≡ 0。
        #   只有 `_h_src is not None`（onfly）时才会被填；默认路径**永远是 None**。
        self._eps0_lag = None
        # ★★ T3：`Lam` 用低精度存。`lam_prec` 为 'f32' 时存 float32（288→144 B/胞），
        #   `sigma_tensor` 的 einsum 强制 float32 输出（否则 numpy 会把 Lam 升成
        #   float64 临时量，反而多占 255 MB）。`E_el()` 走显式升精度（诊断路径）。
        self._lam32 = (str(lam_prec).lower() in ('f32', 'float32', 'single'))
        # ★★ R567：`fft_mode` —— 'c2c'（旧路，逐位不变）/ 'rfft'（实数 FFT 半谱）
        self._fft_mode = str(fft_mode).lower()
        if self._fft_mode not in ('c2c', 'rfft'):
            raise ValueError('fft_mode 只支持 c2c / rfft，收到 %r' % (fft_mode,))
        self._eps0_mode = str(eps0_mode).lower()
        if self._eps0_mode not in ('loop', 'einsum', 'gemm'):
            raise ValueError('eps0_mode 只支持 loop / einsum / gemm，收到 %r'
                             % (eps0_mode,))
        self._half = N // 2 + 1
        self._nyq_n = 0                      # 被 Nyquist 修正的点数（记账用）
        _Kc = K                              # 全谱 k 网格（float64）
        # ★★ T3 记账（旧坑，务必保留）：`lambda_packed` 返回的可能是 **complex128**
        #   ⇒ 按 float32 存会**丢掉虚部**（只发一个 ComplexWarning），实测
        #   `max|Δσ|/max|σ| = 0.50` ✗ —— 而**能量**只差 1.9e-9（二次型对虚部不敏感）
        #   ⇒ **只看能量会漏掉这个错**。复数就存 complex64（同样 144 B/胞）。
        #
        # ★★★ R574 **修我自己埋的第二条性能坑**：原来这里先无条件算一遍**全谱**
        #   `lambda_packed(C, K)`，rfft 分支再把它**整个丢掉**、改算半谱
        #   ⇒ 建引擎时白算一张最大的表。`_r574` D2 实测 c2c→rfft 建表 **+7.4 s**
        #   （N=64；`lambda_packed` 是 O(N³)，N=160 时这笔浪费是分钟级）。
        #   ⇒ 现在只有 `c2c` 才算全谱表。
        if self._fft_mode != 'rfft':
            with acct.bcost('build.lam.c2c'):
                _lam = np.asarray(lambda_packed(C, K, k0_mode=k0_mode))
        if self._fft_mode == 'rfft':
            # ---- 半谱网格 + Nyquist 面的 Hermite 修正（见类 docstring）----
            #   rfftn 的半轴 = **最后一个轴**（实测 `_r562` B3）⇒ 半谱形状 (N,N,N//2+1)
            with acct.bcost('build.lam.rfft_grid'):
                _idx = np.stack(np.meshgrid(np.arange(N), np.arange(N),
                                            np.arange(self._half), indexing='ij'),
                                -1).reshape(-1, 3)
                _ii, _jj, _mm = _idx[:, 0], _idx[:, 1], _idx[:, 2]
                _Kh = np.stack(np.meshgrid(self.kv, self.kv, self.kv[:self._half],
                                           indexing='ij'), -1).reshape(-1, 3)
                _nyq = (_ii == N // 2) | (_jj == N // 2) | (_mm == N // 2)
            with acct.bcost('build.lam.rfft_half'):
                _lam = np.asarray(lambda_packed(C, _Kh, k0_mode=k0_mode))
            with acct.bcost('build.lam.rfft_nyq'):
                if _nyq.any():
                    _mir = (((N - _ii) % N) * N + ((N - _jj) % N)) * N + ((N - _mm) % N)
                    _lam[_nyq] = 0.5 * (_lam[_nyq]
                                        + np.asarray(lambda_packed(
                                            C, _Kc[_mir[_nyq]], k0_mode=k0_mode)))
                    self._nyq_n = int(_nyq.sum())
                _lam = np.ascontiguousarray(_lam)
            # ★★ R570/R571（**冒烟在真实路径上抓到的缺陷**）：`E_el()` 是**全谱**二次型
            #   `Σ_k q(k)`，半谱求和必须带**配对权重**。`_r571_elcheck.py` 直测（N=32）：
            #     半轴平面索引 m；「另一半」= m ∈ [N/2+1, N−1]
            #     ⇒ `Σ_full q = 2·Σ_half q − Σ_{m=0} q − Σ_{m=N/2} q`
            #     实测 `Σ_half w·q / Σ_full`：w=2 全体 **1.0631**；
            #       w=1 当 i/j/m 任一=N/2 **1.00047**；
            #       **w=1 当 m∈{0,N/2} ⇒ 1.00000000** ✅
            #   ⚠ **`q` 必须用 `Λ_eff`（带 Nyquist 平均的那个），不是未平均的 `Λ_true`**：
            #     同权重下 `Λ_true` 给 **1.00101**（差 0.1%），`Λ_eff` 给 **1.00000000**。
            #     这一点与直觉相反（σ 用 Λ_eff 是因为 `real()` 投影；能量用它是因为
            #     Nyquist 面上 k 与 mirror(k) 互为负 ⇒ `q_eff(k)+q_eff(mk)` 恰好等于
            #     全谱那一对的和）。**第一版漏了权重 ⇒ `E_el_J` 差 37.7%。**
            self._wmask = ((_mm == 0) | (_mm == N // 2))
            del _idx, _ii, _jj, _mm, _Kh, _nyq
            if '_mir' in dir():
                del _mir
        if self._lam32:
            self.Lam = np.asarray(_lam, dtype=(np.complex64 if np.iscomplexobj(_lam)
                                               else np.float32))
        else:
            self.Lam = np.asarray(_lam, dtype=(np.complex128 if np.iscomplexobj(_lam)
                                               else np.float64))
        self._lam_cplx = bool(np.iscomplexobj(self.Lam))
        acct.bmem('build.Lam.bytes', self.Lam)
        acct.bmem('build.phi.bytes', self.phi)
        # ★ T3：K 只在建 Lam / _k2 时用到 ⇒ 存 float32（24→12 B/胞）；不再需要时可由
        #   调用方置 None（`LevelSetMulti` 就这么做）。
        self.K = np.asarray(K, dtype=np.float32) if self._lam32 else K
        self.N3 = float(N) ** 3
        self._k2 = (K.astype(np.float64) ** 2).sum(1)
        self.axs = (1, 2, 3)
        # ★★★ R576（goal §8 的配套要求）：**"半轴 = 最后一个轴"必须运行期断言，不能只写在注释里。**
        #   为什么：这条是 scipy 的实现细节，而整条 rfft 路径（半谱 k 网格、Nyquist 修正、
        #   `E_el` 的 `_wmask`、`sh.reshape((6,N,N,_half))`）**全部**建立在它之上。
        #   若哪天 axes 顺序变了而半轴换到别的轴，`reshape` 的**形状仍然对得上**
        #   （(6,N,N,N/2+1) 依旧合法）⇒ **语义错位而不报错**。这正是本仓库最怕的一类错。
        #   ⇒ 用一把 (1,2,2,2) 小探针**实测**，与 `self.axs` / `self._half` 交叉验证。
        if self._fft_mode == 'rfft':
            #   ⚠ 探针尺寸必须**互不相同且 ≥3**：用 (1,2,2,2) 时 `2//2+1 == 2`
            #     ⇒ 半轴变到哪个轴形状都一样，探针**没有分辨力**（量具必须先自证）。
            _probe = np.zeros((1, 4, 6, 8))
            _pshape = sfft.rfftn(_probe, axes=self.axs).shape
            # ⚠ 第一版把 `_want` 写成"只列 axes 那几维" ⇒ 漏掉了**未被变换的前导轴**
            #   （探针是 (1,4,6,8) 而 axes=(1,2,3)）⇒ 断言**误报**。
            #   断言自己也要能过正对照：这里按"逐轴判断"重建，不做任何省略。
            _last = self.axs[-1]
            _want = tuple(_probe.shape[a] // 2 + 1 if a == _last else _probe.shape[a]
                          for a in range(_probe.ndim))
            if _pshape != _want:
                raise RuntimeError(
                    'rfft 半轴假设失效：`sfft.rfftn(axes=%r)` 给出 %r，预期 %r。'
                    '整条 rfft 路径（Lam 半谱网格 / _wmask / reshape）都以'
                    '"半轴 = axes 的最后一个"为前提 ⇒ 必须先修这里再启用 rfft。'
                    % (self.axs, _pshape, _want))
            del _probe, _pshape, _want
        del _lam, K

    # ---------------- 场 ----------------
    def eps0_fields(self):
        """`ε⁰(x)` 的 6 个 Voigt 分量场 `(6,N,N,N)`，由 `Σ_v e0v[v,p]·φ_v` 装配。

        ★★ R562（算子优化）：三种实现，**默认 `loop` = 旧路，逐位不变**。
          实测（`_r562_opbench.py` B1，生产宿主 WSL/conda ml/numpy 2.5.3）：
            旧 loop        0.0368 s   1.00×   基准
            einsum         0.0210 s   1.76×   max|Δ|/max = **0.000e+00（逐位）**
            GEMM           0.0020 s   18.1×   max|Δ|/max = 2.7e-16（1–2 ulp）
          `einsum` 逐位相同这条**在两个宿主上各测过一次**（Windows numpy 2.1.3 也 0.0）
          ⇒ 它可以直接当"等价加速"用；GEMM 只差 1–2 ulp，但**不是逐位**，
          故两者都保留成显式开关，由使用方按需要的严格度选。

        ★★★ R579（goal §4）：`self._h_src is not None` 时走**流式**路
          （见 `eps0_fields_stream`）—— `pf.phi` 那个 `(nv,N³)` 常驻数组**不再需要**。
        """
        if self._h_src is not None:
            with acct.mark('el.e0.stream'):
                e = self.eps0_fields_stream(self._h_src, chunk=self._h_chunk,
                                            slab=getattr(self, '_h_slab', 0))
            # ★★★ R580（P1）：流式装配**不物化 h**，但**必须把它算出的 ε⁰ 存一份**
            #   —— 否则诊断 `E_el()` 会用"当前"的 h，与归档的物化路径**口径不同**
            #   （实测 `E_el_J` 差到 3.1×）。代价 48 B/胞固定，与 nv 无关。
            #   ⚠ 必须 copy：`_epsh` 随后会就地 `e[3:] *= 2.0`。
            self._eps0_lag = e.copy()
            return e
        _m = self._eps0_mode
        if _m == 'einsum':
            with acct.mark('el.e0.einsum'):
                return np.ascontiguousarray(
                    np.einsum('vp,v...->p...', self.e0v, self.phi))
        if _m == 'gemm':
            with acct.mark('el.e0.gemm'):
                return (self.e0v.T @ self.phi.reshape(self.nv, -1)).reshape(
                    6, self.N, self.N, self.N)
        e = np.zeros((6, self.N, self.N, self.N))
        with acct.mark('el.e0.loop'):
            for p in range(6):
                for v in range(self.nv):
                    e[p] += self.e0v[v, p] * self.phi[v]
        return e

    def eps0_fields_stream(self, h_at, chunk=4, slab=0):
        r"""★★★ R579（goal §4）：**不物化**软指示场 `h` 的 ε⁰ 装配。

        ## 它省什么
        生产走 `elastic_soft=True` ⇒ `pf.phi` 从 bool 升成 **float64**
        ⇒ `(nv,N³)` 常驻 **8 B/胞·nv**。N=160 实测 `a = 16.000 B/胞`
        （`g.phi` 8 + `pf.phi` 8）；C5（10 µm 填 30%）需要 `a ≤ 4.6`
        ⇒ **这一项是 C5 的必要条件之一**（`R579_OPOPT4.md §2`）。

        ## 为什么必须**分块**（而不是"现算一个大 h 再 einsum"）
        现算一个 `(nv,N³)` 的 `h` ⇒ **常驻降了、峰值没降** ⇒ 对内存墙**毫无帮助**。
        必须按 `v` 分块、把 `h` 限制在 `chunk` 份 `(N,N,N)` 上。

        ## 逐位等价（可证，不是近似）
        累积写成
        ```python
        for v0 in range(0, nv, chunk):
            h = h_at(v0, v1)                 # (v1-v0, N,N,N)
            for j in range(v1 - v0):
                for p in range(6):
                    e[p] += e0v[v0 + j, p] * h[j]
        ```
        对**固定 p** 而言，沿 `v` 的累加次序仍是**升序**，且每一步都是
        `e[p] += e0v[v,p] * h_v` —— 与 `eps0_mode='loop'` 的
        `for p: for v: e[p] += e0v[v, p] * phi[v]` **完全同一串运算**
        （`p` 循环彼此独立）⇒ **逐位相同**。判据见 `_r579_pfphi.py`。

        `h_at(v0, v1)` 由调用方给（`LevelSetMulti._soft_h_at`），返回
        `(v1-v0, N,N,N)` 的软指示场切片。

        ★★★★★ R581-L2（goal §(4) L2）：`slab > 0` 时走**首轴空间分块**。
          ## 为什么（**用生产口径的记账表定靶，不是猜的**）
          生产（`onfly` + N=96/nv=48）实测 `el.epsh` = **47.5% 单步**，其中 1.10 s
          就是本函数。**不是算子重，是缓存**：`e` 是 `(6,N³)` float64 = **48 B/胞**
          （N=96 ⇒ 40.5 MB，超过 L3），而下面 288 次整场 axpy 每次都把 `e[p]` 与 `h[j]`
          从 DRAM 过一遍 ⇒ 288 × 14 MB ≈ **4.1 GB/步**，而 `e` 只是累加器。
          ## 为什么**必然逐位**
          分块只改**外层循环的切法**，`x0:x1` 是**同一批胞**；对**每个胞**而言，
          沿 `v` 的累加次序、每一步的 `e0v[v,p]*h_v` 表达式**一字不变**
          ⇒ 逐位相同（`_r581_L2_epsh.py` + `_r581_L2_sweep.py`：**42 档组合全部
          `array_equal`**；两个负对照（chunk 内 v 倒序 / 少一维）都有分辨力）。
          ## 实测（微基准，交错配对）
          首轴 slab：N=64 **1.885×**（slab=4,chunk=2）、N=96 **1.812×**（slab=2,chunk=4）。
          ⚠ **末轴** slab **更慢**（0.55–0.62×）—— `e[p,:,:,z0:z1]` 是跨行切片。
          ⚠ 大 slab 反而更慢（工作集溢出 cache）⇒ 最优区间窄在 slab∈{2,4,8}。
        """
        if int(slab) > 0:
            return self._eps0_fields_stream_tiled(h_at, chunk, int(slab))
        e = np.zeros((6, self.N, self.N, self.N))
        e0v = self.e0v
        for v0 in range(0, self.nv, int(chunk)):
            v1 = min(v0 + int(chunk), self.nv)
            h = h_at(v0, v1)
            for j in range(v1 - v0):
                hj = h[j]
                for p in range(6):
                    e[p] += e0v[v0 + j, p] * hj
            del h, hj
        return e

    def _eps0_fields_stream_tiled(self, h_at, chunk, slab):
        """★ R581-L2：**首轴空间分块**版（累加次序与 :meth:`eps0_fields_stream` 一致 ⇒ 逐位）。"""
        N = self.N
        e = np.zeros((6, N, N, N))
        e0v = self.e0v
        for x0 in range(0, N, slab):
            x1 = min(x0 + slab, N)
            for v0 in range(0, self.nv, int(chunk)):
                v1 = min(v0 + int(chunk), self.nv)
                h = h_at(v0, v1, x0, x1)
                for j in range(v1 - v0):
                    hj = h[j]
                    for p in range(6):
                        e[p, x0:x1] += e0v[v0 + j, p] * hj
                del h, hj
        return e

    def eps0_fields_idx(self, idx):
        """★★ T3（2026-09-28）：**按区域编号直接装配** ε⁰ 场，不走 nv 个指示场。

        `idx`：(N,N,N) 整数，0 = 母相，v = 变体 v（1..nv，与 `region()`/`karr` 同约定）。

        为什么需要：`eps0_fields` 的 `Σ_v e0v[v,p]·phi_v` 要 **6×nv = 72 次整场乘加**
        （N=96 时每次 7 MB）；而每个格点**只属于一个区域** ⇒ 直接 gather 只要
        **6 次**（`e[p] = e0v[idx-1, p]`，母相处置 0）。
        实测这条是本框架弹性耗时的大头（T3 后弹性占比 24%）。
        ⚠ 数值等价性：`Σ_v e0v[v,p]·[idx==v+1]` 与 `e0v[idx-1,p]·[idx>0]` 逐位相同
        （每格只有一个 v 命中；母相两项都为 0）⇒ 由 `T3_verify_fastpath.py` T3-3 把关。
        """
        e = np.zeros((6, self.N, self.N, self.N))
        pos = idx > 0
        ii = np.clip(idx.astype(np.intp) - 1, 0, self.nv - 1)
        for p in range(6):
            e[p] = np.where(pos, self.e0v[ii, p], 0.0)
        return e

    def _fft(self, x):
        with acct.mark('el.fft_fwd'):
            return sfft.fftn(x, axes=self.axs, workers=self.workers)

    def _ifft(self, x):
        with acct.mark('el.fft_inv'):
            return sfft.ifftn(x, axes=self.axs, workers=self.workers)

    # ★★ R567：实数 FFT（半谱）。半轴 = **最后一个轴** ⇒ `x` 形状 (…,N,N,N) 出去是
    #   (…,N,N,N//2+1)。`irfftn` 必须显式给 `s=`，否则输出末轴会是 2*(half-1)。
    def _rfft(self, x):
        with acct.mark('el.rfft_fwd'):
            return sfft.rfftn(x, axes=self.axs, workers=self.workers)

    def _irfft(self, x):
        with acct.mark('el.rfft_inv'):
            return sfft.irfftn(x, axes=self.axs, s=(self.N,) * self.dim,
                               workers=self.workers)

    def _epsh(self, idx=None, lag=False):
        """工程应变分量的未归一化 FFT: (6, N,N,N)。idx 给定时走 T3 的 gather 路径。

        ★★★ R580（P1）：`lag=True` 时**用"弹性求解那一刻"存下的 ε⁰**（见 `_eps0_lag`），
        以复刻归档路径的诊断语义。见 `_eps0_lag` 的说明与 `R580_VERIFY.md §5`。
        """
        with acct.mark('el.epsh'):
            # ⚠⚠ 派遣条件**必须**带 `self._h_src is not None`：
            #   否则**物化档**（`_h_src is None`、`_eps0_lag is None`）下
            #   `lag=True` 会拿到"全零"，`E_el()` 直接变 0 —— **把默认路径弄坏**。
            #   （这正是 `_r580_p1check.py` 的 Q2 抓到的：materialized=0 vs onfly=1.9e5。）
            if idx is None and lag and self._h_src is not None:
                e = self._eps0_for_diag()
            elif idx is None:
                e = self.eps0_fields()
            else:
                e = self.eps0_fields_idx(idx)
            e[3:] *= 2.0
            return self._fft(e)

    def _epsh_r(self, idx=None, lag=False):
        """★ R567：同 `_epsh`，但返回**半谱** `(6,N,N,N//2+1)`（实数 FFT）。"""
        with acct.mark('el.epsh_r'):
            if idx is None and lag and self._h_src is not None:
                e = self._eps0_for_diag()
            elif idx is None:
                e = self.eps0_fields()
            else:
                e = self.eps0_fields_idx(idx)
            e[3:] *= 2.0
            return self._rfft(e)

    def _eps0_for_diag(self):
        r"""★★★ R580（P1）：给**诊断**用的 ε⁰ —— **逐位复刻归档路径**的那一个。

        ## 为什么需要它
        `--pf-phi onfly` 下 `eps0_fields()` 从**当前** `g.phi` 现算软指示场 h；
        而归档的物化路径里，`E_el()` 读的是 `pf.phi` —— 那是**上一次弹性求解开始时**
        写进去的 h。`advance()` 在弹性求解之后还要推进 `g.phi`
        ⇒ 测量时刻的 `g.phi` **比那个 h 晚一步**。

        实测（`_r580_bisect.sh` + `_r580_elj.py`，30 步真实路径）：
        `E_el_J` 在前 5 行只差 ~4e-3，而 `--eng-cadence 30` 那一步差 **3.1×**
        （4.309e-11 → 1.353e-10）。**求解器没错**（`Vt`/`f_var`/`nslab_n`/`nf3` 末值全同），
        但 `E_el_J` 被一堆分析脚本用 ⇒ **不能静默改口径**。

        ## 做法
        在 `eps0_fields()` 每次**流式**装配完时，把结果存一份 `_eps0_lag`；
        诊断（`E_el`）改读它。语义上等价于"读上一次写进 `pf.phi` 的那个 h"。

        ## 代价（记账）
        `(6,N³)` float64 = **48 B/胞**，**与 nv 无关**。
        对比它替掉的 `pf.phi`（`8·nv` B/胞）：nv=782 时 **48 vs 6256 ⇒ 省 130×**。
        ⚠ 它是**固定项** ⇒ 进内存定律的 `c`（不是 `a`）：N=160 时 +196.6 MB。
        ⇒ 已把 `c` 由 344 更新为 **392 B/胞**、`nv_max` 由 602 更新为 **597**（见 `R580_VERIFY.md §5`）。

        ## 还没有 stash 时（首次弹性求解之前）
        物化路径下那时 `pf.phi` **还是全零的 bool** ⇒ ε⁰ ≡ 0（实测 step 0 的 `E_el_J` = 0）
        ⇒ 这里必须**同样返回全零**，否则 step 0 就会分叉。
        """
        if self._eps0_lag is not None:
            return self._eps0_lag.copy()      # ⚠ 必须 copy：`_epsh` 会就地 `e[3:] *= 2`
        return np.zeros((6, self.N, self.N, self.N))

    def sigma_tensor(self, idx=None):
        """sigma(x) = real(ifftn(-Lambda : fftn(eps)))  （见文件头归一化说明）

        ★ T3：`lam_prec='f32'` 时**强制 float32 的 einsum**。若不强制，numpy 会把
          float32 的 `Lam` 升成 float64 临时量（N=96 时多占 255 MB），白白吃掉收益。
        ★ R567：`fft_mode='rfft'` 时走半谱（半轴 = 末轴），`Lam` 也已带上 Nyquist 面的
          Hermite 修正 ⇒ 与 c2c 路**等价到舍入**（判据 `_r567_nyqfix.py` N1 = 6.1e-16）。"""
        if self._fft_mode == 'rfft':
            Eh = np.ascontiguousarray(self._epsh_r(idx)).reshape(6, -1)
            with acct.mark('el.sig.contract'):
                if self._lam32:
                    _dt = np.complex64 if self._lam_cplx else np.float32
                    sh = -np.einsum('kpq,qk->pk', self.Lam,
                                    Eh.astype(_dt, copy=False), dtype=_dt)
                else:
                    sh = -np.einsum('kpq,qk->pk', self.Lam, Eh)
            return self._irfft(sh.reshape((6, self.N, self.N, self._half)))
        Eh = self._epsh(idx).reshape(6, -1)
        with acct.mark('el.sig.contract'):
            if self._lam32:
                _dt = np.complex64 if self._lam_cplx else np.float32
                sh = -np.einsum('kpq,qk->pk', self.Lam,
                                Eh.astype(_dt, copy=False), dtype=_dt)
            else:
                sh = -np.einsum('kpq,qk->pk', self.Lam, Eh)
        sh = sh.reshape((6, self.N, self.N, self.N))
        with acct.mark('el.sig.real'):
            return np.real(self._ifft(sh))

    def E_el(self):
        """★ T3：这是**诊断路径**（不在每步热路径）。`lam_prec='f32'` 时显式升到 float64
        以保证判据精度 —— 代价是一次性 255 MB 临时量（只在调用时存在）。
        ★ R567：`fft_mode='rfft'` 时在半谱上算同一个二次型
        （`Σ_k conj(ε(k)):Λ:ε(k)`，k 遍历半谱即可，因为被加项在 k↔−k 上相同）。

        ★★★ R580（P1）：**一律走 `lag=True`** —— 在 `--pf-phi onfly` 下读
        `_eps0_lag`（弹性求解那一刻的 ε⁰），从而与归档的物化路径**逐位一致**；
        在默认（物化）路径下 `lag=True` 是**空操作**（`_h_src is None` ⇒ 走原路）。
        """
        if self._fft_mode == 'rfft':
            # ★ R570/R571：半谱二次型必须带**配对权重**（判据与实测见 `__init__` 的记账）。
            #   `Σ_full q = 2·Σ_half q − Σ_{m∈{0,N/2}} q`，且 `q` 用 `Λ_eff`。
            Eh = np.ascontiguousarray(self._epsh_r(lag=True)).reshape(6, -1) / self.N3
            Lam = (self.Lam.astype(np.complex128 if self._lam_cplx else np.float64)
                   if self._lam32 else self.Lam)
            q = np.real(np.einsum('pk,kpq,qk->k', np.conj(Eh), Lam, Eh))
            return 0.5 * self.V * float(2.0 * q.sum() - q[self._wmask].sum())
        Eh = self._epsh(lag=True).reshape(6, -1) / self.N3
        if self._lam32:
            Lam = self.Lam.astype(np.complex128 if self._lam_cplx else np.float64)
        else:
            Lam = self.Lam
        return 0.5 * self.V * float(np.real(np.einsum('pk,kpq,qk->',
                                                      np.conj(Eh), Lam, Eh)))

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
        S2 = (self.phi ** 2).sum(0)
        # ★★ 记账（2026-09-25，T2.1b 顺带修的**内部不一致**）：
        #   原写法 drive = dG*6m(1-m) 是 d/dm[-dG m^2(3-2m)] —— 那对应化学能 -dG*m^2(3-2m)，
        #   而本类自己的 E_chem_grad() 用的是**线性** Ec = -dG*m（=> 泛函导数恒为 -dG），
        #   dfdphi()/step() 用的也是 -dG。**同一个类里两套化学插值** ⇒ 不一致。
        #   后果（原写法）：m=0 时驱动力恒为 0（无法从"母相"自发开始）、且动力学被人为按 m 调制；
        #   与 E_total() 不自洽 ⇒ 用 forces() 的路径与用 dfdphi() 的路径会给出不同的 f_eq(T)。
        #   现统一为线性（= E_chem_grad/dfdphi 的形式）：drive = dG（每个变体拿到完整驱动力）。
        #   影响面（已核）：所有现存调用点都是 dG=0（FD 自检、P2 外载择优）或"旧版对照"
        #   => **对既有判据数值零影响**；只有 dG!=0 的动力学路径会变（那正是 T2.1b 要的）。
        drive = self.dG
        for v in range(self.nv):
            # ★★ T1 修（P0-1，2026-09-28）：符号 `−` → `+`。
            #   `forces()` 返回的是**驱动力**（判据：化学项写成 `+dG`、界面项写成 `−W(...)`），
            #   而弹性驱动的驱动力是 **+ε⁰_v:σ**（变分法：驱动力 = −δF_el/δφ_v）。
            #   独立数值判决见 `T1_verify_edsign.py`（球 R=120 nm：真实 D_corr=−1.43e8，
            #   修前返回 +1.66e8 ⇒ 符号相反；修后比值 +1.12~+1.17 ∈ [0.8,1.3] ✓）。
            #   ⚠ `dfdphi()` 里那一项是 **−ε⁰:σ**，**它是对的**（那是 dF/dφ，不是驱动力）
            #   ⇒ 两处相差一个整体负号是**设计如此**，不要"统一"掉。
            f[v] = +np.einsum('p,p...->...', self.e0v_eng[v], sig) + self.sext_e0[v]
            p = self.phi[v]
            f[v] += drive - self.W * (2 * p * (1 - p) * (1 - 2 * p)
                                      + 2 * p * (S2 - p ** 2))
        return f, sig

    def set_T(self, T):
        """把温度设到 T（若定义了 dG_of_T 则同步更新 dG）。[T]"""
        self.T = float(T)
        if self.dG_of_T is not None:
            self.dG = float(self.dG_of_T(self.T))
        return self.dG

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


# ============================================================================
# ★★★ 2026-09-29 Round 141：**收敛的** `argmin_n 0.5·e:Lam(C,n):e`
#
# 为什么必须加这一段
# ----------------
# `MEASUREMENT_SPEC` 的全部各向异性轴（`n*`、`w`、`ncmp`）原先都来自
#     「在 **400（或 600）个随机法向**里取 `0.5·e:Lam(C,n):e` 最小」
# 实测（`_chk_habit2.py` / `_chk_pairnorm.py`，日志 `_w2_habit2.log` / `_w2_pairnorm.log`）：
#   * 该泛函的极小**极窄**：40,000 点 Fibonacci 仍比精修值高 3–9 倍；
#     400 点则高 **21–654 倍**（`E(NPF)/E_min`）。
#   * 变体-变体界面（`ncmp`）：`E/E_best20k` 中位 **25**、最大 **6943**；
#     与最优点的夹角中位 **88°**，**36/66 对 > 20°**。
#   * 两个 rank-1 解的弹性自能只差 **8.6%** ⇒ 能量判据对"选支"几乎无分辨力
#     ⇒ 抽样一抖就翻支（实测 `NPF` 与引擎 `wtab` 在一半变体上差 ~90°）。
# ⇒ **这不是精度问题，是可复现性问题**：同一个物理输入在不同进程给出不同的轴。
#
# 本函数只做一件事：**把"抽样 argmin"换成收敛的 argmin**（Fibonacci + 局部模式搜索）。
# ⚠ 记账：**选支规则不变**（仍是 `max |n·nref|`，见 `LevelSetMulti._rank1_axes`）；
#    换的只是 `nref` 的求法 ⇒ 分支可能相对旧行为改变，但**从此可复现**。
# ============================================================================
def _lam_full_batch(C, NS):
    """向量化的 `_lam_full`：`NS (S,3)` ⇒ `(S,3,3,3,3)`。
       与逐点 `_lam_full` 的关系由 `_chk_lam_batch.py` 做正对照（要求逐位/1e-15）。"""
    n = np.asarray(NS, float)
    n = n / np.linalg.norm(n, axis=1)[:, None]
    A = np.einsum('ijkl,si,sk->sjl', C, n, n)           # (S,3,3)
    Ai = np.linalg.inv(A)
    B = np.einsum('ijkl,si->sjkl', C, n)                # B[s,j,k,l]
    D = np.einsum('sjkl,sjm->sklm', B, Ai)              # D[s,k,l,m]
    C1 = np.einsum('sklm,sp,pmqr->sklqr', D, n, C)      # C1[s,k,l,q,r]
    return C[None, ...] - C1


def _fib_sphere(S):
    """Fibonacci 球面（S 个近均匀点）。"""
    i = np.arange(S, dtype=float)
    ph = np.pi * (3.0 - np.sqrt(5.0)) * i
    z = 1.0 - 2.0 * (i + 0.5) / S
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    NS = np.stack([r * np.cos(ph), r * np.sin(ph), z], axis=1)
    return NS / np.linalg.norm(NS, axis=1)[:, None]


def E_normal(C, e, NS):
    """`0.5·e:Lam(C,n):e`，`NS (S,3)` ⇒ `(S,)`。"""
    L = _lam_full_batch(C, NS)
    return 0.5 * np.einsum('ij,sijkl,kl->s', np.asarray(e, float), L,
                           np.asarray(e, float))


def argmin_normal(C, e, nsamp=20000, iters=140, nsamp_loc=256, r0=0.35,
                  decay=0.955, seed=0, rtol=1e-7):
    """★ 收敛的 `argmin_n 0.5·e:Lam(C,n):e`。

    两段：① 20,000 点 Fibonacci 全局扫描；② 半径按 `decay` 收缩的局部模式搜索，
    每轮 256 个随机方向。收敛判据：单轮相对改善 `< rtol`（或耗尽 `iters`）。

    返回 `(n_star, E_star, E_glob_scan / E_star)` —— 第三个量是**收敛指标**，
    应 ≈1（`>1.05` 即说明全局扫描没找到盆地，须加大 `nsamp`）。
    """
    NS = _fib_sphere(int(nsamp))
    v = E_normal(C, e, NS)
    j = int(np.argmin(v))
    v_glob = float(v[j])
    best, vb = NS[j].copy(), v_glob
    rng = np.random.default_rng(seed)
    r = r0
    for _ in range(int(iters)):
        d = rng.normal(size=(int(nsamp_loc), 3))
        d /= np.linalg.norm(d, axis=1)[:, None]
        cand = best[None, :] + r * d
        cand /= np.linalg.norm(cand, axis=1)[:, None]
        vv = E_normal(C, e, cand)
        k = int(np.argmin(vv))
        if vv[k] < vb * (1.0 - rtol):
            best, vb = cand[k].copy(), float(vv[k])
        r *= decay
    return best, vb, v_glob / max(vb, 1e-300)



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
    """功能导数正对照: dE_el/dphi_v(x) 必须等于 -e0_v:sigma(x)

    ⚠⚠ **2026-10-01 修（第 42 个自查错误，`§180`）**：本测试**从 T1/P0-1 修复起就一直是 FAIL**，
    而 FAIL 的原因是**测试过期**、不是引擎错：
      * T1（P0-1）把 `forces()` 的弹性项从 `−ε⁰:σ` 改成 **`+ε⁰:σ`**（驱动力口径，已由
        `T1_verify_edsign.py` 独立判决 PASS）；
      * 而本测试原来写 `an = f[v][idx]`，**注释仍写"泛函导数 = −e0_v:sigma"** ——
        修复后 `f` 变成 `+ε⁰:σ`，于是判据变成拿 `+ε⁰:σ` 比 `−ε⁰:σ`
        ⇒ 相对差**恰好 2.00** 且**不随 δ 下降**（实测 1e-4/1e-5/1e-6 全是 2.00e+00）。
      * ⇒ 现在**直接从 `sig` 算** `−ε⁰_v:σ`（这才是 `dE_el/dφ_v`），
        并额外断言 `forces()` 确实等于 `+ε⁰:σ`（把两套约定的**关系**也钉住）。
    """
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
    # ★ 修：泛函导数 = −ε⁰_v:σ（**直接从 sig 算**，不要再借道 `forces()`）
    e0s = -np.einsum('p,p...->...', pf.e0v_eng[v], sig)
    an = e0s[idx]                                      # 泛函导数 (J/m^3)
    # ★ 附加断言：`forces()` 的弹性项必须恰好是 **+ε⁰:σ**（= −泛函导数）
    drive_ok = abs(f[v][idx] - (-an)) / max(abs(an), 1e-30)
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
    print('  [附加] `forces()` 弹性项 vs `+e0:sigma` 的相对差 = %.2e  %s（预期 0：驱动力口径）'
          % (drive_ok, 'PASS' if drive_ok < 1e-12 else 'FAIL'))
    # 注: FD 精度地板实测 ~4e-6（在 E_el ~1e-13 J 上做有限差分），故判据取 1e-4
    return (errs[-1] < 1e-4 and errs[0] > errs[-1] and drive_ok < 1e-12)


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
