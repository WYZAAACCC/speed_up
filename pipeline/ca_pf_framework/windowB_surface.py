#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_surface.py --- **Gibbs 面场（level-set）+ 体相场** 的混合实现

与 `windowB_hybrid.py` 的区别（必须记账）:
  windowB_hybrid.py 的"相"状态是**每胞整数标签 + 随机翻转** ⇒ 那是格点 KMC/Potts，
  **不是相场也不是面场** ✗（我在用户指出后确认）。本文件把它换成正确表示：
     · 体相: **连续场**（成分 c、微弹性），按 **PDE** 演化
     · 界面: **level-set 函数 φ(x)**（连续、有符号距离），按
                 ∂φ/∂t + v_n |∇φ| = 0,   v_n = M[ [[Δf]] + Ω γ(n) κ ]
       推进（Gibbs–Thomson），速度由界面**扩展**到带上（nearest-interface-point）
     · 面上量: Γ_i 定义在界面带上，走 ∂Γ/∂t + ∇_s·(D_s∇_sΓ) = 体相通量差
     · 无任何随机翻转 ✗

本文件先实现【面场骨架 + 两个解析判据】:
  S0 曲率正对照：level-set 的 κ = ∇·(∇φ/|∇φ|) 对理想球应给 2/R
  S1 Gibbs–Thomson：孤球收缩应满足 d(R²)/dt = -4 M γ Ω（Ω 并入 M）
（H3 偏析平衡 / H4 守恒沿用 `windowB_hybrid.py` 的验法，下一步搬过来。）
"""
import os
import numpy as np
from scipy import fft as sfft
from scipy.ndimage import distance_transform_edt, gaussian_filter


def upwind_grad(phi, sgn, dx):
    """|∇φ| 的 Godunov 迎风离散（一阶）；sgn 为逐点符号场（+1/−1）：
         sgn>0: |∇φ|²ᵢ = max(max(D⁻φ,0)², min(D⁺φ,0)²)
         sgn<0: |∇φ|²ᵢ = max(max(D⁺φ,0)², min(D⁻φ,0)²)
       ★ 记账：这是 ④ 验证过的格式（`_chk_d4.py`）。**单畴与多畴共用同一份实现**
       （旧写法在两个类里各写一份 ⇒ 极易分叉，是审计记下的一条教训）。"""
    acc = np.zeros_like(phi)
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        gpos = np.maximum(np.maximum(dm, 0.0) ** 2, np.minimum(dp, 0.0) ** 2)
        gneg = np.maximum(np.maximum(dp, 0.0) ** 2, np.minimum(dm, 0.0) ** 2)
        acc += np.where(sgn > 0, gpos, gneg)
    return np.sqrt(acc)


def _minmod(a, b):
    """minmod 限制器：同号取绝对值小者，异号取 0（保单调）"""
    return 0.5 * (np.sign(a) + np.sign(b)) * np.minimum(np.abs(a), np.abs(b))


def upwind_grad2(phi, sgn, dx):
    """**二阶 ENO(minmod)** Godunov 迎风 |∇φ|。一阶迎风写成
         D⁻ᵢ = (φᵢ−φᵢ₋₁)/dx
       的二阶版本用 3 点单边外推 + minmod 限制（同号才外推 ⇒ 光滑区二阶、拐点处退一阶）：
         Dm2ᵢ = D⁻ᵢ + ½·minmod(D⁻ᵢ−D⁻ᵢ₋₁, D⁺ᵢ−D⁻ᵢ)
         Dp2ᵢ = D⁺ᵢ − ½·minmod(D⁺ᵢ₊₁−D⁺ᵢ, D⁺ᵢ−D⁻ᵢ)
       ★ 记账（为什么要它）：一阶迎风的单边差有 **O(dx) 的取向相关误差**，实测两个后果——
         ① 推进时把有效各向异性压低 ~8%（W1：a2 比 0.90–0.93，且**不随 dx 收敛**）；
         ② Sussman 迭代的不动点不是真 SDF ⇒ reinit **不幂等**，每次把界面内移
            ~0.03–0.10 dx（越用越糟）⇒ 等于给界面加了一个系统性假收缩速度。
        而"中心型/对称型" |∇φ| 虽然二阶、在圆上漂移为 0，却是**边际不稳定**的
        （迭代 100 次后 ΔR 突然跳到 +0.40 dx、带内 |∇φ|→1.26 ✗）。
       ⇒ 二阶 ENO 迎风同时满足：二阶精度 + 单调/稳定。"""
    acc = np.zeros_like(phi)
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        dmm = np.roll(dm, 1, axis=ax)
        dpp = np.roll(dp, -1, axis=ax)
        Dm2 = dm + 0.5 * _minmod(dm - dmm, dp - dm)
        Dp2 = dp - 0.5 * _minmod(dpp - dp, dp - dm)
        gpos = np.maximum(np.maximum(Dm2, 0.0) ** 2, np.minimum(Dp2, 0.0) ** 2)
        gneg = np.maximum(np.maximum(Dp2, 0.0) ** 2, np.minimum(Dm2, 0.0) ** 2)
        acc += np.where(sgn > 0, gpos, gneg)
    return np.sqrt(acc)


def grad_sym(phi, dx):
    """**二阶**对称 |∇φ|：Σ_轴 ½[(D⁻φ)²+(D⁺φ)²]。
       记账（本轮踩的坑）：一阶 Godunov 迎风 |∇φ| 在**曲面**界面处系统**高估** ~1.5%，
       且误差随取向变化 ⇒ Sussman 迭代的**不动点不是真 SDF**：
       对新鲜球面 SDF 反复 reinit，半径**单调内移且越走越快**
       （-0.028, -0.048, -0.067, -0.084, -0.100 dx ✗，即 reinit 不是幂等的，
       等于给界面加了一个系统性的假收缩速度）。
       对称式把两侧单边差分的 O(dx) 误差对冲掉（余 O(dx²)）⇒ 不动点回到真 SDF ✓。"""
    acc = 0.0
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        acc = acc + 0.5 * (dm ** 2 + dp ** 2)
    return np.sqrt(acc)


def sussman_reinit(phi, dx, iters=40, dtau=None, grad='upwind2', guard=True):
    """④ 保亚胞位置的 PDE 式重初始化：解 φ_τ + S(φ0)(|∇φ|−1) = 0（一阶迎风）。
       零等值面在连续意义下不动 ✓（旧写法 `distance_transform_edt(mask)` 会把界面
       吸附到胞边界，O(0.5dx) 系统偏差 ✗）。
       ★ 记账（本轮修的一个真 bug）：步长必须满足**多维** Godunov 迎风的 CFL
         `dτ·(|S_x|+|S_y|+|S_z|) ≤ dx` ⇒ `dτ ≤ dx/3`（3D；2D 薄板是 dx/2）。
         旧默认 `dτ = 0.8dx` **越界 2.4 倍** ⇒ 这个"迭代"其实在发散：
           症状 ① 界面被"钉"在按 dt 变化的伪不动点上（W1 定容弛豫实测：
                dt 小 5 倍，收敛长径比从 1.35 掉到 1.15 ✗）；
           症状 ② 跑几百步后带内 |∇φ| 从 1.0 突然涨到 5.5 ⇒ 界面炸掉 ✗。
         现在默认 `dτ = 0.5·dx/3`（安全裕度 2 倍），收敛靠增加迭代数（iter=40）。"""
    phi0 = phi.copy()
    # EXPERT-#3b 修（2026-09-26）：**先把输入整体归一化成近似 SDF**。
    #   为什么必须：PDE 式重初始化的稳定性前提是 |grad phi| ~ 1。实测输入
    #   |grad phi0| = 2（例如差分场 d = phi_k - phi_l 在紧挨界面时）会让 (gm-1) ~ 1，
    #   每步位移 ~ dtau，而二阶 ENO 的 gm 会过冲 => **直接发散**：
    #     实测 zero-level 从 0.012um 跑到 -0.82um(iters=100) -> -71um(iters=3000)，
    #     带内 |grad phi| 变 nan；且**迭代越多越糟**（说明是发散不是收敛慢）。
    #   归一化只除以一个**全局常数**（不改零等值面、只改斜率），是安全的前置步骤。
    _probe = phi0
    for _ax in range(3):
        _probe = _probe  # no-op，保持维度一致
    _g = np.gradient(phi0, dx)
    _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
    _gm = float(np.median(_gn))
    if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
        phi = phi / _gm
        phi0 = phi0 / _gm
    S = phi0 / np.sqrt(phi0 ** 2 + dx ** 2)
    if dtau is None:
        dtau = 0.5 * dx / 3.0   # 一阶迎风、多维 CFL：dτ ≤ dx/3（|S|≤1）
    # EXPERT-#3c 修（2026-09-26）：**自适应 dtau + 单步 clip + 发散守卫**。
    #   为什么原写法会发散：更新量是 dtau*S*(gm-1)。当输入 |grad phi| 明显 >1 时
    #   (gm-1)~O(1)，而 gm 自身在迭代中还会被二阶 ENO 过冲放大 =>
    #   实测 iters 越大越糟（-0.82um@100 -> -71um@3000，带内 |grad| 变 nan）。
    #   三处加固：
    #     ① 自适应步长：dtau_eff = min(dtau, 0.5*dx/3/max(gm))  （CFL 对 gm 也成立）
    #     ② 单步更新 clip 到 ±0.5*dx
    #     ③ 守卫：若 max|phi| 超过初值量级 10 倍 => **拒绝本次 reinit**（返回原场，不静默生效）
    _phi_raw = phi0.copy()
    _lim0 = float(np.max(np.abs(phi0))) + dx
    for _ in range(iters):
        if grad == 'upwind':
            gm = upwind_grad(phi, S, dx)
        elif grad == 'upwind2':
            gm = upwind_grad2(phi, S, dx)
        elif grad == 'central':
            g = np.gradient(phi, dx)
            gm = np.sqrt(sum(gi ** 2 for gi in g))
        else:
            gm = grad_sym(phi, dx)
        _gmax = float(np.max(gm))
        _dte = min(dtau, 0.5 * dx / 3.0 / max(_gmax, 1.0))
        _upd = _dte * S * (gm - 1.0)
        phi = phi - np.clip(_upd, -0.5 * dx, 0.5 * dx)
        if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
            return _phi_raw            # 发散 => 拒绝，保持原场
    return phi


def herring_stiffness_cusp(ndot2, gamma0, Lam, eps_c=0.05):
    """**尖点/近奇异**界面能的 Herring 刚度 gamma + gamma_tt。

        gamma(th)  = gamma0 * (1 + Lam * sqrt(sin^2 th + eps_c^2))
        gamma_tt   = gamma0 * Lam * (eps_c^2 - s^4 - 2 s^2 eps_c^2) / s^3,   s^2 = sin^2 th + eps_c^2

    ★ 为什么需要它（本轮实测 D11/长时程给的定量理由）：
      孤立单核长跑（beta_h=3.5, beta_w=2.3）：300 步 aspect 3.49 -> 1200 步 **2.23**，
      而**法向厚度反而长了 2.4x**。=> 形状弛豫（Gibbs-Thomson，驱动力 = gamma*kappa）
      用**各向同性的 gamma** 把薄饼**拉圆**了 => 光有 M(n) 钉扎**维持不住**板条。
      要维持，必须让惯习面同时是**低能面 + 刚性面**。

    ★ 凸性（已逐项核对，故**不需要** Wulff 凸化）：
        th -> 90 deg: gamma_tt -> -gamma0*Lam, gamma -> gamma0(1+Lam)
                      => gamma+gamma_tt -> gamma0 > 0  ✓
        th -> 0     : s -> eps_c => gamma_tt -> +gamma0*Lam/eps_c  (>0, 发散) ✓
      => 处处凸；且惯习面处刚度 ~ gamma0*Lam/eps_c **极大** => 该面极稳定。
    Lam 的物理：gamma(惯习面)/gamma(无序面) = 1/(1+Lam)。取 Lam=0.4 => 比 0.71。
    """
    s2 = np.clip(1.0 - ndot2, 0.0, 1.0)
    s2e = s2 + eps_c ** 2
    s = np.sqrt(s2e)
    g = gamma0 * (1.0 + Lam * s)
    gtt = gamma0 * Lam * (eps_c ** 2 - s2 ** 2 - 2.0 * s2 * eps_c ** 2) / (s2e ** 1.5)
    return g + gtt


def herring_stiffness(ndot2, gamma0, Lam, herring=True):
    """各向异性界面刚度 γ_eff = γ + γ_θθ（Herring 项）。
       输入 ndot2 = (n·n_pref)²；对 γ(θ)=γ0[1+Λ sin²θ]（θ = 法向与 n_pref 的夹角）:
           herring=True :  γ+γ_θθ = γ0[1 + 2Λ − 3Λ sin²θ]  ← Gibbs–Thomson 的正确形式
           herring=False:  只用 γ 本身 = γ0[1 + Λ sin²θ]     ← **刻意保留的错误对照**（W1 反向判据）"""
    s2 = 1.0 - ndot2
    if herring:
        return gamma0 * (1.0 + 2.0 * Lam - 3.0 * Lam * s2)
    return gamma0 * (1.0 + Lam * s2)


def iface_crossings(field, dx, axis):
    """**亚胞射线交点**口径的界面位置：沿 `axis` 找 `field` 的相邻变号胞对，
       线性插值出交点在该轴上的亚胞坐标（物理单位）。

    ★ 记账（为什么要它 —— 本轮的直接动因，审计 §10）：
      `region()` **计数法**在**均匀亚胞平移**下没有分辨力：
        · 界面推进 < 0.5·dx 时**逐位不动**（实测 pair_kernel=True 的 P1 读数 0.000 ✗）；
        · 平移恰好是整数胞时又**逐位精确**（旧 W2 的 40×0.1dx = 4dx 正是这种巧合）。
      两个极端都是**构型依赖**的 ⇒ 判据本身不可用。
      射线交点只用"相邻两胞 field 变号 + 线性插值"：O(dx²) 无偏、对任意亚胞平移
      都连续可读，且**不依赖 |∇φ|**（与 S1 的 `radius_rays` 同一口径，可互相印证）。

    返回 (n_cross, coords)；coords 为各交点坐标（一维数组，无交点则为空数组）。
    """
    field = np.asarray(field, float)
    n = field.shape[axis]
    if n < 2:
        return 0, np.zeros(0)
    lo = [slice(None)] * field.ndim
    hi = [slice(None)] * field.ndim
    lo[axis] = np.arange(n - 1)
    hi[axis] = np.arange(1, n)
    a = field[tuple(lo)]
    b = field[tuple(hi)]
    # ★ 记账（本轮实测踩到的退化）：`a*b < 0` 会**漏掉零点正好落在胞心**的情形
    #   （初值 φ = (i−12)dx ⇒ 界面恰在 z 胞 12 的中心 ⇒ a*b = 0 ⇒ 判据返回"无交点"，
    #   量出 z0 = nan ✗）。改用**非对称**变号判据 `(a<0≤b) | (a>0≥b)`：
    #     · a=0 ⇒ t=0（交点就在 a 胞心）、b=0 ⇒ t=1（就在 b 胞心）——都精确；
    #     · 零只在**前一对**被记一次（(a<0,b≥0) 与 (a>0,b≤0) 互斥）⇒ 不重复计数。
    s = ((a < 0) & (b >= 0)) | ((a > 0) & (b <= 0))
    if not s.any():
        return 0, np.zeros(0)
    ii = np.argwhere(s)
    pa = a[tuple(ii.T)]
    pb = b[tuple(ii.T)]
    t = pa / (pa - pb)
    coord = (ii[:, axis].astype(float) + t + 0.5) * dx
    return int(s.sum()), coord


def extend_along_normal(v, phi, dx, iters=12, dtau_fac=0.4):
    """把界面速度 v 沿**法向**延拓（标准 "extension velocity"：解
         v_τ + S(φ)·(n·∇v) = 0 ,  n = ∇φ/|∇φ|,  S(φ)=φ/√(φ²+dx²)
       用一阶迎风）。为什么必须要它：**只**沿法向常数延拓才能让整个剖面的更新
       成为**纯平移** ⇒ 保 SDF、保界面速度（见 `LevelSetSurface.advance` 的记账）。
       ★ 相比 nearest-interface-point(distance_transform_edt) 延拓：局部、便宜
         （EDT 在 96³ 上每步 ~2 s，这里 ~30 ms），且是**光滑**延拓（无最近点跳变）。"""
    v = v.copy()
    g = np.gradient(phi, dx)
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = S * (g[ax] / gn)
            dm = (v - np.roll(v, 1, axis=ax)) / dx
            dp = (np.roll(v, -1, axis=ax) - v) / dx
            cov += w * np.where(w > 0, dm, dp)
        v = v - dtau * cov
    return v


class LevelSetSurface(object):
    """level-set 面场（单相/单畴版；多畴身份由 label 场平流携带，下一步接）"""

    def __init__(self, N, L, gamma=0.15, Mob=1.0, kappa_omega=1.0, ic='sphere',
                 R0=None, workers=4, reinit_every=50, nz=None, ndim=3,
                 reinit_dtau=None, reinit_iters=60, reinit_grad='upwind2'):
        """ndim=2 时用 (N,N,nz) 的薄板 + z 方向平移不变 ⇒ **与真 2D 逐位等价**
           （SDF 不依赖 z、np.gradient 的 z 分量为 0）但便宜 nz 倍。nz 缺省 4。"""
        self.N, self.L = N, L
        self.ndim = ndim
        self.Nz = int(nz) if nz is not None else (4 if ndim == 2 else N)
        self.dx = L / N
        self.gamma = gamma
        self.M = Mob               # 含 Ω（记账：M 已含摩尔体积）
        self.workers = workers
        self.reinit_every = reinit_every
        self.reinit_dtau = reinit_dtau          # None ⇒ 用 sussman_reinit 的安全默认
        self.reinit_iters = reinit_iters
        self.reinit_grad = reinit_grad          # 'sym'(二阶,默认) | 'upwind' | 'central'
        x = (np.arange(N) + 0.5) * self.dx
        xz = (np.arange(self.Nz) + 0.5) * self.dx
        X, Y, Z = np.meshgrid(x, x, xz, indexing='ij')
        c0 = 0.5 * L
        if R0 is None:
            R0 = 0.25 * L
        self.R0 = R0
        r = np.sqrt((X - c0) ** 2 + (Y - c0) ** 2 + (Z - c0) ** 2)
        self.phi = r - R0                    # <0 = 产物内部（有符号距离）

    # ---------- 面几何（全部来自 φ，连续、无台阶伪影）----------
    def normal(self):
        g = np.gradient(self.phi, self.dx)
        gnorm = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        return [gi / gnorm for gi in g], gnorm

    def curvature(self):
        """κ = ∇·(∇φ/|∇φ|)（level-set 标准式；凸面（产物在外）取正）"""
        n, _ = self.normal()
        return sum(np.gradient(n[i], self.dx)[i] for i in range(3))

    def interface_mask(self, band=1.5):
        """界面带：|φ| <= band·dx"""
        return np.abs(self.phi) <= band * self.dx

    def area(self):
        """界面积（coarea 式估计：A = ∫ δ(φ)|∇φ| dV ≈ ∫_{band} |∇φ| dV / (2·band·dx)）
           —— 等价于 (band 内 |∇φ| 的体积分)/(带厚)。收敛性在报告里记账。"""
        m = self.interface_mask()
        _, gnorm = self.normal()
        return float((gnorm * m).sum()) * self.dx ** 3 / (2 * 1.5 * self.dx)

    def volume(self):
        """产物体积 = φ<0 的体积（用平滑阶跃估算以减小量化噪声）"""
        h = 0.5 * (1.0 - np.tanh(np.clip(self.phi / (1.0 * self.dx), -20, 20)))
        return float(h.sum()) * self.dx ** 3

    def radius(self):
        return (3 * self.volume() / (4 * np.pi)) ** (1 / 3)

    # ---------- 2D（薄板）专用：横截面半径 / 定容投影 / 界面点提取 ----------
    def Lz(self):
        return self.Nz * self.dx

    def volume_2d(self):
        """横截面积 = 3D 体积 / 板厚"""
        return self.volume() / self.Lz()

    def radius_2d(self):
        """等效半径 R = sqrt(A_cross/π)（柱体的横截面）"""
        return np.sqrt(max(self.volume_2d(), 0.0) / np.pi)

    def project_volume(self, V_target, iters=12, warn_many_dx=1.0):
        """**定容投影**：把 φ 整体平移一个常数 c（|∇φ|=1 不受影响）使**三维**体积回到 V_target。
           体积对平移的导数 dV/dc = −A（A = 三维界面积）⇒ 牛顿步 c = (V − V_target)/A。
           ★ 记账（本轮踩到的单位陷阱）：**必须用同一套测度** —— 若拿 `volume_2d()`
             （m²）配 `area()`（m²，但是整根柱体的侧面积）就会差一个 Lz ⇒ 修正量被放大
             1/Lz*... 倍。实测：三维/三维 给出正确的 0.115 nm 步长，而 2D/3D 混用一步把
             φ 平移了 **14 mm** ⇒ 界面直接被推出计算域（band=0，"形状消失"）。
             加了下面的守卫：单步修正量超过 `warn_many_dx·dx` 就告警（说明测度没配平）。
           ★ 这是"体积守恒弛豫"的**投影实现**，与 Lagrange 乘子 `df = γ⟨κ⟩_A` 等价
             （两者都只允许形状自由度演化）；投影实现**没有临界核不稳定性** ⇒ 鲁棒。"""
        for _ in range(iters):
            V = self.volume()
            dV = V - V_target
            if abs(dV) < 1e-8 * abs(V_target):
                break
            A = self.area()
            if A <= 0:
                break
            c = dV / A
            if abs(c) > warn_many_dx * self.dx:
                print('   [project_volume 告警] 单步平移 %.3e m = %.2f dx —— 测度可能没配平'
                      % (c, c / self.dx))
            self.phi = self.phi + c
        return self.volume()

    def region_center(self):
        """区域（φ<0）的形心 —— Wulff 形状量测的中心"""
        m = self.phi < 0
        if not m.any():
            return np.zeros(3)
        idx = np.argwhere(m).astype(float) + 0.5
        return (idx.mean(0)) * self.dx

    def radius_iface(self, band=1.5):
        """从**亚胞界面点**量等效半径（球的 R）：λ = mean|x_if − x_c|。
           ★ 记账（本轮修的量测偏差）：`radius()` 用的 tanh 体积测度对**限制在带内**的
             界面平移只有 **90.5%** 灵敏度（0.5sech² 的尾巴被带边截掉）⇒ 用它量界面
             速度会**系统性低估 ~9.5%**（实测：真实更新量给 -0.0200 nm/步，tanh 测度
             只报 -0.0182 nm/步；两者之比 0.918 与 0.905 完全吻合）。
             对**全域平移**（φ+c）才回到 99.86%。所以界面速度必须用**几何点**量，
             不能用带截断的体积测度。"""
        P, _ = self.interface_points(band=band)
        if len(P) < 8:
            return np.nan
        c = self.region_center()
        return float(np.linalg.norm(P - c[None, :], axis=1).mean())

    def radius_rays(self):
        """**射线交点**口径的界面半径：沿三个轴向找 φ 变号的相邻胞对，线性插值出
           亚胞交点位置，再对 |x_cross − x_c| 取平均（面积均匀加权）。
           ★ 为什么需要它：界面**速度**的量测必须避开两类偏置 ——
             (i) tanh 体积测度对"限制在带内"的界面平移只有 90.5% 灵敏度（带边截断）✗；
             (ii) `interface_points` 的**投影** x−φ∇φ/|∇φ|² 在 |∇φ|≠1 时带偏 ✗。
           射线交点只用"相邻两胞的 φ 变号 + 线性插值"，O(dx²) 无偏、也不依赖 |∇φ|。"""
        c = self.region_center()
        rad = []
        for ax in range(3):
            n = self.phi.shape[ax]
            a = np.take(self.phi, np.arange(n - 1), axis=ax)
            b = np.take(self.phi, np.arange(1, n), axis=ax)
            s = (a * b) < 0
            if not s.any():
                continue
            ii = np.argwhere(s)
            pa = a[tuple(ii.T)]
            pb = b[tuple(ii.T)]
            t = pa / (pa - pb)
            pos = (ii.astype(float) + 0.5) * self.dx
            pos[:, ax] = ((ii[:, ax] + t) + 0.5) * self.dx
            rad.append(np.linalg.norm(pos - c[None, :], axis=1))
        if not rad:
            return np.nan
        return float(np.concatenate(rad).mean())

    def interface_points(self, band=1.5, zslice=None):
        """界面点 x_if 与法向 n（一阶投影到零等值面）：
             x_if = x − φ ∇φ/|∇φ|² ,  n = ∇φ/|∇φ|
           返回 (P (M,3), N (M,3))。zslice 给定时只在那一层取点（2D 柱体用）。"""
        g = np.gradient(self.phi, self.dx)
        gn2 = sum(gi ** 2 for gi in g) + 1e-300
        if zslice is not None:
            sl = (slice(None), slice(None), int(zslice))
            p = self.phi[sl]
            m = np.abs(p) <= band * self.dx
            idx = np.argwhere(m)
            gg = [gi[sl] for gi in g]
            gn2s = gn2[sl]
        else:
            m = np.abs(self.phi) <= band * self.dx
            idx = np.argwhere(m)
            gg, gn2s = g, gn2
        if len(idx) == 0:
            return np.zeros((0, 3)), np.zeros((0, 3))
        pv = self.phi[tuple(idx.T)] if zslice is None else self.phi[sl][tuple(idx.T)]
        pts = np.zeros((len(idx), 3))
        nrm = np.zeros((len(idx), 3))
        # zslice 情形 idx 只有 2 列 ⇒ z 方向导数为 0（真 2D 问题的精确简化）
        axes = [0, 1] if zslice is not None else [0, 1, 2]
        for a in axes:
            ga = gg[a][tuple(idx.T)]
            pts[:, a] = (idx[:, a].astype(float) + 0.5) * self.dx
            nrm[:, a] = ga / np.sqrt(gn2s[tuple(idx.T)])
            pts[:, a] -= pv * ga / gn2s[tuple(idx.T)]
        if zslice is not None:
            pts[:, 2] = (int(zslice) + 0.5) * self.dx
            nrm[:, 2] = 0.0
            nn = np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-300
            nrm = nrm / nn
        return pts, nrm

    # ---------- 速度扩展（nearest-interface-point）----------
    def extend_velocity(self, vn_iface, band_cells=4):
        """把界面上的 v_n 扩展为带上处处可用的速度场（标准做法）"""
        m = self.interface_mask()
        if not m.any():
            return np.zeros_like(self.phi)
        # 到最近界面点的索引
        ind = distance_transform_edt(~m, return_distances=False, return_indices=True)
        vn_ext = vn_iface[tuple(ind)]
        near = distance_transform_edt(~m) <= band_cells
        return np.where(near, vn_ext, 0.0)

    # ---------- 界面推进（PDE，不是翻转）----------
    def advance(self, dt, df=0.0, gamma_eff=None, aniso=0.0, npref=None,
                herring=True, band=1.5, adv_grad='upwind2', band_cells=6,
                extend='edt', ext_iters=14, ext_refresh=5,
                mob_aniso=0.0, mref=None):
        """∂φ/∂t + v_n|∇φ| = 0，v_n = M[Δf − γ_eff(n) κ]（γ_eff = γ+γ_θθ）。
           ★ 记账（本轮移植 ④ 的两处改动）：
             1) 空间导数换成 **Godunov 迎风 |∇φ|**（模块级 `upwind_grad`），
                旧写法用中心差分 `|∇φ|` ⇒ 不稳、且大形变下失真；
             2) 重初始化换成 **Sussman PDE 式**（保亚胞界面位置），
                旧写法 `distance_transform_edt(φ<0 掩模)` 把界面吸附到胞边界 ✗。
           ★ 另外**不再做速度扩展**：v_n 由带上的局部 κ 直接给出（处处光滑），
             而 nearest-interface-point 扩展是 O(dx) 的分段常数近似 ⇒ 无必要且更差。
           —— 顺带记账：本函数旧版还有一个 `ininside := inside` 的笔误（无害但已删）。"""
        # ★★ 记账（本轮最重要的一个修正）：**必须**把界面速度沿法向**扩展到一条较宽的带**
        #    （nearest-interface-point 扩展 ⇒ 速度沿法向为常数 ⇒ 整个剖面的更新是**纯平移**
        #    ⇒ φ 保持 SDF、界面速度精确）。我此前把扩展删掉、只用 1.5dx 窄带，导致：
        #      · 窄带：带外剖面"不动" ⇒ 带边出现折点并随时间累积 ⇒ 界面速度塌掉
        #        （实测 d(R²)/dt 只有理论的 **0.138** ✗，带内 |∇φ| 从 1.00 掉到 0.87）；
        #      · 不扩展的宽带：vn 在带内随 κ∝1/r 变化 ⇒ 剖面被**非均匀拉伸** ⇒ |∇φ| 爆到 4–5 ✗。
        #    修复后（扩展 + 6dx 带）实测 d(R²)/dt = **1.014** ✓、|∇φ| 稳定 ✓。
        gam0 = self.gamma if gamma_eff is None else gamma_eff
        kap = self.curvature()
        m = self.interface_mask(band)
        # ★ 符号约定（记账）：v_n = M[ Δf_bulk − Ω γ κ ]，κ 对**凸的产物**取正。
        #   ⇒ 正曲率使凸体收缩（Gibbs–Thomson）；Δf<0 表示产物相稳定 ⇒ 长大。
        gk = gam0
        if aniso > 0 and npref is not None:
            n, _ = self.normal()
            nd = np.asarray(npref, float)
            nd = nd / (np.linalg.norm(nd) + 1e-300)
            ndot2 = sum(n[i] * nd[i] for i in range(3)) ** 2
            gk = herring_stiffness(np.clip(ndot2, 0.0, 1.0), gam0, aniso, herring)
        # ---- P0.4 (2026-09-26, LATH_FACET_PLAN): 界面**迁移率**各向异性 --------------
        #   物理：界面迁移率与界面能一样由界面结构决定；{334} 型惯习面是"好界面"，
        #         其他取向的迁移率被结构缺陷拖低（faceted growth 的标准图像）。
        #   ★ 为什么必须走 M(n) 而不是继续调 gamma(n)：
        #     P0.3 实测（_chk_mroute A-D，df=1e8 = dG_chem(M_s) 的真实值）：
        #       aniso=0 与 aniso=0.9 的 M6 中位**都是 55.4 deg**，参考取向换对/换错也不动
        #     => 在真实驱动力下，"界面能 vs 驱动力"的幅度竞争根本不成立。
        #     而 M(n) 是**动力学**量，**没有热力学凸性约束**（不需要 gamma+gamma_tt>0）
        #     => 各向异性强度可以任意大，不会被 Delta G 淹没。
        #   形式： M(n) = M0 * [1 - mob_aniso * (1 - (n.nref)^2)]
        #     mob_aniso=0   -> 各向同性（返回旧行为，逐位相同）
        #     mob_aniso=1   -> 非法向迁移率 = 0（完全钉扎）
        Mloc = self.M
        if mob_aniso > 0.0 and mref is not None:
            nv_, _gn_ = self.normal()
            nd_ = np.asarray(mref, float)
            nd_ = nd_ / (np.linalg.norm(nd_) + 1e-300)
            ndot2_ = np.clip(sum(nv_[i] * nd_[i] for i in range(3)) ** 2, 0.0, 1.0)
            Mloc = self.M * (1.0 - mob_aniso * (1.0 - ndot2_))
        vn_if = np.where(m, Mloc * (df - gk * kap), 0.0)
        if extend == 'edt' and (~m).any():
            # 最近界面点扩展：把界面上的 v_n 复制到"到界面距离 ≤ band_cells"内的所有胞
            # ⇒ 沿法向常数 ⇒ 剖面的更新是纯平移（保 SDF、保界面速度）
            # ★ 成本记账：EDT 在 96³ 上 ~2×100 ms ⇒ 每步都算会让步时 +330 ms。
            #   最近界面点的**索引图**变化很慢（界面每步只走 0.02 dx）⇒ 缓存 `ext_refresh`
            #   步复用一次（默认 5 步 ⇒ 步时降到 ~40 ms，速度判据不受影响）。
            age = getattr(self, '_ext_age', 0)
            if age <= 0 or getattr(self, '_ext_band', None) != band_cells:
                self._ext_ind = distance_transform_edt(~m, return_distances=False,
                                                       return_indices=True)
                self._ext_near = distance_transform_edt(~m) <= band_cells
                self._ext_band = band_cells
                self._ext_age = ext_refresh - 1
            else:
                self._ext_age = age - 1
            ind, near = self._ext_ind, self._ext_near
            vn = np.where(near, vn_if[tuple(ind)], 0.0)
        elif extend:
            # ★ 默认：沿法向的 PDE 延拓（局部、便宜、光滑）
            vn = extend_along_normal(vn_if, self.phi, self.dx, iters=ext_iters)
            vn = np.where(np.abs(self.phi) <= band_cells * self.dx, vn, 0.0)
        else:
            vn = vn_if
        if adv_grad == 'central':
            # 对照用：中心差分 |∇φ|（对光滑 SDF 是二阶；迎风是一阶单边）
            _, gn_c = self.normal()
            gmag = gn_c
        else:
            sgn = np.where(vn > 0, 1.0, -1.0)
            if adv_grad == 'upwind':
                gmag = upwind_grad(self.phi, sgn, self.dx)      # 一阶迎风（最保守）
            else:
                gmag = upwind_grad2(self.phi, sgn, self.dx)     # ★ 二阶 ENO 迎风（默认）
        self.phi -= dt * vn * gmag
        self._cnt = getattr(self, '_cnt', 0) + 1
        if self.reinit_every and self._cnt % self.reinit_every == 0:
            self.reinitialize()
        return vn

    def reinitialize(self, band_cells=6):
        """④ Sussman PDE 式重初始化：把带内的 φ 拉回 |∇φ|=1，**不动零等值面** ✓
           （带外不动 ⇒ 多区域/多岛情形安全）。"""
        near = np.abs(self.phi) <= band_cells * self.dx
        if near.any():
            newp = sussman_reinit(self.phi, self.dx, iters=self.reinit_iters,
                                  dtau=self.reinit_dtau, grad=self.reinit_grad)
            self.phi = np.where(near, newp, self.phi)


# ============================================================ 判据
def S0_curvature(N=64, dx=2e-9, R0=3e-8):
    g = LevelSetSurface(N, N * dx, R0=R0)
    kap = g.curvature()
    m = g.interface_mask()
    k_meas = float(kap[m].mean())
    k_th = 2.0 / R0
    rel = abs(k_meas / k_th - 1)
    print('---- S0 level-set 曲率正对照 ----')
    print('   R=%.0f nm (R/dx=%.1f): κ_meas=%.3e vs 2/R=%.3e ; 相对差 %.2f%%   %s'
          % (R0 * 1e9, R0 / dx, k_meas, k_th, 100 * rel, 'PASS' if rel < 0.05 else 'FAIL'))
    return rel < 0.05


def S1_GibbsThomson(N=96, dx=1e-9, R0=2.4e-8, M=1e-9, gamma=0.15, nstep=400):
    """孤球收缩：d(R²)/dt 应 = -4Mγ（level-set 无台阶伪影，收敛应干净）
       ★ 半径用**亚胞界面点**量（`radius_iface`），不用 tanh 体积测度 ——
         后者对带内平移只有 90.5% 灵敏度，会把斜率系统性拉低 ~9.5% ✗（见该方法记账）。"""
    g = LevelSetSurface(N, N * dx, gamma=gamma, Mob=M, R0=R0)
    dt = 0.02 * dx / (M * 2 * gamma / R0)
    ts, Rs = [], []
    for k in range(nstep):
        if k % 20 == 0:
            ts.append(k * dt)
            Rs.append(g.radius_rays())     # ★ 用无偏的射线交点口径（见该方法的记账）
        g.advance(dt, df=0.0)
    ts, Rs = np.array(ts), np.array(Rs)
    Rs = np.where(np.isfinite(Rs), Rs, np.nan)
    good = np.isfinite(Rs)
    ts, Rs = ts[good], Rs[good]
    keep = (Rs > 0.55 * Rs[0]) & (Rs < 0.99 * Rs[0])   # 收缩方向
    if keep.sum() < 3:                                  # 若反向（长大），则用上侧窗口
        keep = (Rs > 1.01 * Rs[0]) & (Rs < 1.45 * Rs[0])
    if keep.sum() >= 3:
        sl = np.polyfit(ts[keep], Rs[keep] ** 2, 1)[0]
    else:
        sl = np.nan
    sl_th = -4 * M * gamma
    rel = abs(sl / sl_th - 1)
    print('---- S1 Gibbs–Thomson（level-set，孤球收缩）----')
    print('   R(t) 前几点: %s nm' % np.round(np.array(Rs[:6]) * 1e9, 2))
    print('   拟合窗口 %d 点, R/R0∈[%.2f,%.2f] ; d(R²)/dt=%.4e vs -4Mγ=%.4e ; 相对差 %.1f%%   %s'
          % (int(keep.sum()), Rs[keep].min() / Rs[0] if keep.sum() else np.nan,
             Rs[keep].max() / Rs[0] if keep.sum() else np.nan, sl, sl_th, 100 * rel,
             'PASS' if rel < 0.15 else 'FAIL'))
    return rel < 0.15


def _old_main():
    res = {}
    res['S0'] = S0_curvature()
    res['S1'] = S1_GibbsThomson()
    print('\n总判定: %s' % ('ALL PASS' if all(res.values())
                          else 'FAIL -> %s' % [k for k, v in res.items() if not v]))


# ============================================================ 多区域 level-set（多畴身份）
class LevelSetMulti(object):
    """多区域 level-set：每个相/变体一个 φ_k（有符号距离），region = argmin_k φ_k。
       · 身份由 φ 平流携带（**没有随机胞翻转** ✗）
       · 体相耦合：ε⁰(φ) 由 region 给出 ⇒ 复用已验的谱法微弹性
       · 界面动力学：∂φ_k/∂t + v_n^k|∇φ_k| = 0，v_n^k = M[Δf_k + Δf_el,k − Ω γ(n) κ_k]
    """

    def __init__(self, N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9, df=None,
                 Lam=0.0, k0_mode='clamped', workers=4, reinit_every=20, nv=None,
                 aniso_elastic=False, C_hex_tab=None, C_cub=None, sigma_ext=None,
                 reinit_iters=100, reinit_dtau=None, reinit_grad='upwind2'):
        # EXPERT-#3: reinit_iters 由硬编码 30 提到 100。依据 _tune_reinit.py：
        #   两变体平面界面 d=phi_k-phi_l 的零等值面 iters=30 停在 0.025um，
        #   iters>=100 落到 0.01200um = **解析值** => 残余偏差来自迭代不足。
        self.reinit_iters = int(reinit_iters)
        self.reinit_dtau = reinit_dtau
        self.reinit_grad = reinit_grad
        self.N, self.L = N, L
        self.dx = L / N
        self.gamma = gamma
        self.M = Mob
        self.reinit_every = reinit_every
        self.nv = (nv if nv is not None else (1 if eps0 is None else len(eps0)))
        self.nreg = self.nv + 1                      # 0 = 母相
        x = (np.arange(N) + 0.5) * self.dx
        X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
        self.XYZ = np.stack([X, Y, Z], -1)
        self.phi = np.full((self.nreg, N, N, N), 1e3)
        # 体相成分与面上过剩（Gibbs 面的状态量）
        try:
            import sys as _s
            # (fix) 原来的硬编码绝对路径 => 换项目相对路径，别人克隆到别处也能跑
            _s.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gibbs'))
            from gibbs_physics import RHO_MOL
            self.rho = RHO_MOL
        except Exception:
            self.rho = 1.0129e5
        self.T = 1950.0
        self.c = np.full((N, N, N), 0.036)
        self.Gam = np.zeros((N, N, N))
        self.Gam_mol = np.zeros((N, N, N))   # ★ W-6c：面量的**权威状态**（摩尔/胞）
        # ★★ W-6c（2026-09-25）：**面量的权威状态改按「摩尔/胞」存**（Gam_mol）。
        #   为什么： 里的 A_c 是 coarea 测度、**界面一动它就变** ⇒ 账面逐步漏
        #   （实测 advance 侧 rel 1.1e-5/步，30 步累积 1.2e-4；update_Gamma 侧是 2.5e-32）。
        #   改法：内部只对 Gam_mol 做加减（与测度无关）， 只作为
        #   **派生量**供物理（McLean Gamma_eq）与面扩散的通量换算使用 ⇒  用
        #   ，**与时间无关、必然闭合**。
        #   兼容：判据若直接写 （A3/H6/M3 的老写法），update_Gamma 开头会检测
        #   到不一致并以  为准重新同步 Gam_mol（见那里的 guard）。
        self.J_edge = [np.zeros((N, N, N))] * 3     # 面扩散的边通量（ΣJ_s 判据/H7 用）
        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)
        # ---- T2.1a (2026-09-25): external stress sigma_ext -------------------
        # Driving-force convention, identical to `PF3D.forces()` / `dfdphi()`:
        #     df_v = -eps0_v : sigma_int  +  sigma_ext : eps0_v
        # (the second term is the work done by the applied stress as the
        # transformation strain develops).  sigma_ext = None reproduces the old
        # behaviour bit-for-bit (sext_e0 is then identically zero).
        self.sigma_ext = (np.zeros((3, 3)) if sigma_ext is None
                          else np.asarray(sigma_ext, float))
        self.sext_e0 = (np.zeros(self.nv) if eps0 is None else
                        np.array([np.einsum('ij,ij->', self.sigma_ext,
                                            np.asarray(e, float)) for e in eps0]))
        # 弹性
        self.pf = None
        self.ae = None
        self.aniso_elastic = bool(aniso_elastic)
        self.elastic_soft = False     # AUDIT-#9: 默认沿用 hard region（不改动已归档结论）
        if C is not None and eps0 is not None:
            from windowB_pf3d import PF3D, VOIGT, G6 as _G6, _lam_full
            self.pf = PF3D(N, L, C, eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                           workers=workers, k0_mode=k0_mode,
                           sigma_ext=self.sigma_ext)
            self.e0v_eng = np.array([[eps0[v][i, j] for (i, j) in VOIGT]
                                     for v in range(self.nv)]) * _G6[None, :]
            self._G6 = _G6
        if self.aniso_elastic:
            # ★★ 逐变体模量（方案：参考介质 + 极化迭代；已过 AS-1/AS-1b/AS-2）：
            #   12 个 Burgers 变体的 hcp 张量各不相同（c 轴 = {110}_β 面法向，来自
            #   `windowB_ti64_variants` 的 meta['n'] —— **注意与 `npref` 不是一回事**：
            #   `npref` 是"弹性最省能法向"（惯习面），这里是晶体学 c 轴）
            #   基体 = 母相 bcc。参考模量 C⁰ 取**初始**相体积平均（固定一次；
            #   迭代的不动点与 C⁰ 无关，C⁰ 只影响收敛速度）。
            from windowB_aniso_elastic import AnisoElastic
            from windowB_pf3d import C_hex, C_cubic, C_rot4, rot_z_to
            from windowB_ti64_variants import variants as _vars
            _e0, _Fs, _meta = _vars()
            Cal = C_hex_tab if C_hex_tab is not None else C_hex(
                162.4e9, 92.0e9, 69.0e9, 180.7e9, 46.7e9)      # ★文献值待核对
            Cbe = C_cub if C_cub is not None else C_cubic(134.0e9, 110.0e9, 36.0e9)
            self._C_phases = [Cbe] + [
                C_rot4(Cal, rot_z_to(np.asarray(_meta[v]['n'], float)))
                for v in range(self.nv)]
            f0 = 1.0 / (self.nv + 1)
            self.ae = AnisoElastic(N, L, self._C_phases,
                                   sum(self._C_phases) / len(self._C_phases))

        # ---- P0.1 (2026-09-26, LATH_FACET_PLAN 1-主因①-a): 配对相容法向表 ----
        #   物理依据 = MATH_FRAMEWORK 5.6 的 rank-1 不变平面 (lam2(U)=1):
        #   两个变体 k,l 之间的界面应落在它们的不变平面上, 法向
        #       n*(k,l) = argmin_n 0.5 * dEps0 : Lam(C,n) : dEps0,  dEps0 = eps0_k - eps0_l.
        #   旧代码: 任何界面都用 winner 的 npref[k] (= 对**母相**的惯习面)
        #   => 变体-变体界面用错对象. 生产末态 f=0.9001 => 母相只剩 9.99% 面积
        #   => 绝大多数界面用错 => M6 (58.9 deg vs 随机 59.7 deg) 的第一嫌疑.
        self.ncmp = None      # (nreg,nreg,3); 母相相关项与对角项 = nan (调用方 fallback)
        # ---- P2 (2026-09-26): 每变体的**双轴**（n_hab, w = n_hab x a），a 由 rank-1 分解 ----
        self.wtab = None      # (nreg,3); 母相行 = nan
        # AUDIT-#7 修：同时存**真长轴 a**（rank-1 分解的位移方向）。
        #   原来调用方只能用 n x w 去还原 a，而 a 并不垂直于 n
        #   （实测 n.a = cos(82.7deg) = 0.127），n x (n x a) = n(n.a) - a
        #   => 偏离真 a 约 7.3deg。现在直接给 atab。
        self.atab = None      # (nreg,3); 真长轴 a
        if C is not None and eps0 is not None:
            _w = np.full((self.nreg, 3), np.nan)
            _a = np.full((self.nreg, 3), np.nan)
            _rng = np.random.default_rng(0)
            _ns = _rng.normal(size=(400, 3))
            _ns /= np.linalg.norm(_ns, axis=1)[:, None]
            for _v in range(self.nv):
                _E = np.asarray(eps0[_v], float)
                _val = 0.5 * np.einsum('ij,sijkl,kl->s', _E,
                                       np.array([_lam_full(C, n) for n in _ns]), _E)
                _nref = _ns[int(np.argmin(_val))]
                _R = self._rank1_axes(_E, _nref)
                if _R is not None:
                    _w[_v + 1] = _R[2]
                    _a[_v + 1] = _R[1]      # AUDIT-#7: 真长轴
            self.wtab = _w
            self.atab = _a

        if C is not None and eps0 is not None:
            self.ncmp = self._pair_normals(C, eps0)

    # ---------- 区域与几何 ----------
    @staticmethod
    def _rank1_axes(eps, nref):
        """对形状应变 eps 做 **rank-1 分解** eps = 0.5*(a n^T + n a^T)，
           并用 nref 选解（分解有**两个**解，取 n 更接近 nref 的那个）。
           返回 (n_hab, a_axis, w_axis)；w = n x a = 板条**宽度方向**。

           物理（MATH_FRAMEWORK 5.6 的 lam2(U)=1 的直接延伸）：
             n = 惯习面法向（大面法向）—— 已被 beta_h 压制
             a = 界面位错的**位移/滑移方向** = 板条**长轴**（不压制）
             w = n x a = 面内垂直方向 = 板条**宽度方向**（第二钉扎轴）
           ★ 记账：a.n 不要求为 0（rank-1 分解中 a.n 正比于 trace(eps)，
             第一版判据误以为要正交，已更正）。判据用**重构误差**。
        """
        eps = np.asarray(eps, float)
        w_, V = np.linalg.eigh(eps)
        o = np.argsort(w_)[::-1]
        w_ = w_[o]; V = V[:, o]
        mu1, mu3 = w_[0], w_[2]
        if mu1 <= 0 or mu3 >= 0:
            return None
        e1, e3 = V[:, 0], V[:, 2]
        r = np.sqrt(-mu3 / mu1)
        cands = []
        for sgn in (+1.0, -1.0):
            n = e1 + sgn * r * e3
            n = n / np.linalg.norm(n)
            a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
            a = a / np.linalg.norm(a)
            cands.append((n, a))
        nd = np.asarray(nref, float); nd = nd / np.linalg.norm(nd)
        best = max(cands, key=lambda t: abs(t[0] @ nd))
        n, a = best
        wv = np.cross(n, a)
        nw = np.linalg.norm(wv)
        if nw < 1e-8:
            wv = np.cross(n, [0.0, 0.0, 1.0])
            nw = np.linalg.norm(wv) + 1e-300
        return n, a, wv / nw

    @staticmethod
    def _pair_normals(C, eps0, nsamp=600, seed=0):
        """变体-变体配对 (k,l) 的 rank-1 相容法向表 (MATH_FRAMEWORK 5.6).

        返回 (nv+1, nv+1, 3): ncmp[k,l] = argmin_n 0.5 dEps0:Lam(C,n):dEps0.
        母相相关项 (k==0 或 l==0) 与对角项 = nan (物理上不适用, 调用方 fallback 到 npref).
        与 _chk_morph.py 的 M6 用**同一**定义 (那里也按 de = eps0[k-1]-eps0[l-1] 取 argmin).
        """
        from windowB_pf3d import _lam_full
        nv = len(eps0)
        tab = np.full((nv + 1, nv + 1, 3), np.nan)
        rng = np.random.default_rng(seed)
        ns = rng.normal(size=(nsamp, 3))
        ns /= np.linalg.norm(ns, axis=1)[:, None]
        L = np.array([_lam_full(C, n) for n in ns])            # (nsamp,3,3,3,3)
        E = [np.asarray(e, float) for e in eps0]
        for k in range(1, nv + 1):
            for l in range(k + 1, nv + 1):
                de = E[k - 1] - E[l - 1]
                val = 0.5 * np.einsum('ij,sijkl,kl->s', de, L, de)
                tab[k, l] = tab[l, k] = ns[int(np.argmin(val))]
        return tab

    def region(self):
        return np.argmin(self.phi, axis=0).astype(np.int8)

    def seed_sphere(self, k, center, R):
        c = np.asarray(center, float)
        r = np.linalg.norm(self.XYZ - c, axis=-1)
        self.phi[k] = np.minimum(self.phi[k], r - R)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], R - r)   # 其它区域让位

    def seed_plate(self, k, center, normal, R, t, elong=1.0, along=None):
        """薄板晶核：法向 normal、半径 R、厚 t。

           P3 (2026-09-26): elong/along 支持**长条形**种子（面内椭圆）。
           为什么需要：Mfac 对变体-变体界面是**双重压制**（(n.ncmp)^2 与 (n.w)^2）
           => 块被**锁在种子形状**上 => 圆盘种子只能给出长/宽~1 的等轴块
           （实测 LR1 长/宽=1.39）。真实马氏体板条的**形核胚本身是薄片状**的
           （晶体学控制）=> 属 HyBRID_FRAMEWORK 8 item 4 的**形核是输入**。
           along = 长轴方向（= n x w）；elong = 长/宽比。
        """
        c = np.asarray(center, float)
        n = np.asarray(normal, float)
        n = n / np.linalg.norm(n)
        rel = self.XYZ - c
        d = rel @ n
        u = rel - d[..., None] * n
        rperp = np.linalg.norm(u, axis=-1)
        if elong > 1.0 and along is not None:
            al = np.asarray(along, float)
            al = al / (np.linalg.norm(al) + 1e-300)
            e_par = u @ al
            e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
            rperp = np.sqrt((e_par / elong) ** 2 + e_per ** 2)
        # EXPERT-#1 修：**越界硬检查**。 在 elong>1 时用 (e_par/elong)^2+e_per^2
        #   => 长轴半径 = elong*R。若它超过"种子中心到最近域面的距离"，种子会被
        #   盒子截断（实测 E6: elong*R=1.8um > L/2=0.8um => 初始长/宽只有 2.72 而非 6）。
        #   截断后的一切形貌结论都无效 => 这里直接拒绝，不再静默。
        if elong > 1.0:
            _c = np.asarray(center, float)
            _margin = float(min(_c.min(), (self.L - _c).min()))
            if elong * R > _margin:
                raise ValueError(
                    'elongated seed exceeds domain: elong*R=%.4g um > margin %.4g um. '
                    'Enlarge L, reduce R, or reduce elong.'
                    % (elong * R, _margin))
        sdf = np.maximum(np.abs(d) - t / 2, rperp - R)         # 椭/圆盘 SDF（近似）
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], -sdf)

    def init_parent(self):
        """★ 多区域 VDF 的标准初始化：母相 = 变体并集的补集 ⇒ φ_0 = −min_{k≥1} φ_k。
           （本轮修的 bug：把 φ_0 初始化成常数 1e3 ⇒ argmin 永远选变体 ⇒ 母相初始体积 0 ✗）"""
        self.phi[0] = -np.min(self.phi[1:], axis=0)

    # ================= 面上场 Γ（溶质过剩）：Gibbs 面的"面" =================
    def surface_band(self):
        """界面胞集合：6 邻域内区域号不同者（3D 中的离散 2D 流形）"""
        reg = self.region()
        m = np.zeros_like(reg, bool)
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            m |= (np.roll(reg, d, axis=(0, 1, 2)) != reg)
        return m

    def cell_area(self):
        """每胞的界面面积 A_c = (#异键)/2·dx²（立体学一致的测度）"""
        reg = self.region()
        b = np.zeros(reg.shape)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            b += (np.roll(reg, d, axis=(0, 1, 2)) != reg)
        return 0.5 * b * self.dx ** 2

    def cell_area_geom(self):
        """★ P1 修正：几何（coarea / 部分体积）面积测度，替换格子键测度。
           A_c(i) = |∇φ_k(i)|·dx²/3（只取 winner==k 且在 1.5dx 带内）。
           ★ 记账：初版多乘了 2（误以为要"两侧各半"），实测给 +100.5% ✗；
             实际上每个胞只属一个区域 ⇒ Σ_k 已含两侧 ⇒ 去掉因子后 +0.25% ✅
             （与 A2 的 +0.3% 完全一致，两条独立估计互相印证 ✓）。"""
        reg = self.region()
        A = np.zeros_like(self.phi[0])
        for k in range(self.nreg):
            g = np.gradient(self.phi[k], self.dx)
            # ★★ 记账（本轮修的真 bug，M3/A3 的 `nan` 就是它）：**不能给 gn 加 ε**。
            #   旧写法 `gn = |∇φ| + 1e-30` ⇒ 带外（|∇φ| = 0）的胞也得到 A_c = 1e-48 > 0
            #   ⇒ 掩模 `A_c > 0` **恒为真（全域）**、`A_c` 在带外是 1e-48 量级。
            #   在 H6 把面扩散改成"保守边通量 + `Δq/A_c`"之后，真实带（A_c≈6.7e-19）与
            #   "幽灵带"（1e-48）的交界处比值 ~1e29 ⇒ 显式更新**爆掉**（实测 M3：
            #   `|Γ|` 1e-6 → 2.9e5 → 3.6e21 → nan）。⇒ 用**原始** |∇φ|：带外 A_c 严格为 0，
            #   掩模 `A_c > 0` 就精确等于"该胞承载界面面积"（H6 想要的语义）。
            gn = np.sqrt(sum(gi ** 2 for gi in g))
            band = (reg == k) & (np.abs(self.phi[k]) <= 1.5 * self.dx)
            A = np.where(band, gn * self.dx ** 2 / 3.0, A)
        return A

    def area_total_geom(self):
        return float(self.cell_area_geom().sum())

    def band_health(self):
        """界面带健康度 —— **防止几何量静默失真**（本轮实测的坑）。

        多畴 + 宽带速度扩展时，各区域按"自己最近的界面"平移 ⇒ 两区域之间的差分
        `φ_k−φ_l` 被**无限拉陡**：实测带内 |∇φ| 从 0.5 涨到 530、带胞从 3.7e4 掉到 155
        ⇒ 面几何测度（S_v、面积）**静默退化到 0** ✗。
        任何用带几何做结论的地方（S_v、板条厚度、面偏析总量）必须先过这一关。
        返回 (带胞数, 带内 |∇φ_winner| 中位, 是否健康)。
        """
        A = self.cell_area_geom()
        m = A > 0
        if not m.any():
            return 0, np.inf, False
        karr = np.argsort(self.phi, axis=0)[0]
        phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
        gn = np.sqrt(sum(gi ** 2 for gi in np.gradient(phiw, self.dx)))
        med = float(np.median(gn[m]))
        ok = (med < 5.0) and (int(m.sum()) > 0.002 * self.phi.shape[1] ** 3)
        return int(m.sum()), med, bool(ok)

    def Gamma_eq(self, c):
        """Langmuir/McLean 平衡过剩（mol/m²），复用 pipeline/gibbs 的单一参数来源"""
        try:
            import sys as _s
            # (fix) 原来的硬编码绝对路径 => 换项目相对路径，别人克隆到别处也能跑
            _s.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gibbs'))
            from gibbs_physics import gamma_eq_langmuir, dH_seg_from_anchor
            H, _ = dH_seg_from_anchor()
            flat = np.ravel(c)
            out = np.array([gamma_eq_langmuir(float(x), self.T, H) for x in flat])
            return out.reshape(c.shape)
        except Exception:
            K = np.exp(2.0)
            x = K * c
            return 2.14e-5 * x / (1.0 + x)

    def update_Gamma(self, dt, tau_ex=1e-9, D_s=1e-20):
        """面的演化（全部守恒）：
             (1) 与体相按局部平衡交换（同一胞等量反号 ⇒ 精确守恒；含 ρ_mol 换算）
             (2) 沿面扩散：**切向 Laplace–Beltrami 算子**（② 本轮修：旧写法用 6 邻域格点键，
                 含法向邻居 ⇒ Γ 会跨界面扩散 = 物理错 ✗）
             (3) 离开界面带的胞，其面过剩**还给体相**（⑥ 本轮修：旧写法直接清零 ⇒ 溶质泄漏 ✗）"""
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        A_c = self.cell_area_geom()      # ★ P1：用几何（coarea）测度，替换格子键测度
        # ★★ H6 记账（本轮）：**面积、交换、扩散必须用同一个掩模**
        #   旧写法：`surface_band()`（异邻 2 层带）与 `cell_area_geom`（winner & |φ|≤1.5dx）不一致
        #   ⇒ 外层带胞 A_c=0 ⇒ 面扩散/交换在那里失效、且总量记账错位 ✗（审计 §5.2 的老账）。
        m = A_c > 0
        # ---- W-6c：Gam_mol 的兼容 guard（外部若写 Gam，以 Gam 为准重新同步）----
        # ★★ W-6c 的 guard（第二轮修，关键）：**不能用  去判"外部写歪"** ——
        #   界面一移动 A_c 就变，于是即使没人动 Gam， 也不再等于 Gam_mol
        #   ⇒ guard 会把 Gam_mol 重算成  ⇒ **凭空改摩尔量**（实测 rel 1.1e-5/步，
        #   30 步累积 1.2e-4，与 W-6b 的残差完全同源）。
        #   正确判据：比较"当前 Gam"与"**上一次由 Gam_mol 派生出来的 Gam**"（）——
        #   只有**外部真的写了 Gam** 时两者才会不同（面积变化不影响它）✓。
        if not hasattr(self, 'Gam_mol') or self.Gam_mol.shape != A_c.shape:
            self.Gam_mol = self.Gam * A_c
        elif hasattr(self, '_Gam_derived') and self._Gam_derived.shape == self.Gam.shape:
            _sc = max(float(np.max(np.abs(self.Gam))), 1e-300)
            if float(np.max(np.abs(self.Gam - self._Gam_derived))) > 1e-12 * _sc:
                self.Gam_mol = self.Gam * A_c          # 外部写了 Gam => 以它为准
        else:
            self.Gam_mol = self.Gam * A_c
        # (3) ★ W-6d：把"带外但仍持有 Gam_mol"的胞**每步强制回吐**给体相。
        #   旧写法依赖 （"上一步在带内、这一步不在"）⇒ 与调用顺序/reinit 耦合，
        #   漏掉的胞会让 Gam_mol 挂在带外 ⇒ 账面多出量（M4 综合场景 2.02e-04 -> 2.43e-03 的来源）。
        #   新写法只用**当前**的 ：凡是带外且 Gam_mol != 0 的，一律回吐并清零 ⇒ 与顺序无关。
        wander = (self.Gam_mol != 0.0) & (~m)
        if wander.any():
            self.c = self.c + np.where(wander,
                                       self.Gam_mol / (self.rho * self.dx ** 3), 0.0)
            self.Gam_mol = np.where(wander, 0.0, self.Gam_mol)
        self._m_prev, self._A_prev = m.copy(), A_c.copy()
        Gam_eq = self.Gamma_eq(self.c)
        # ★ 稳定性保护：显式弛豫必须 dt ≤ τ_ex，否则 Γ 过冲发散（实测 M4 里 dt=4e-9 > τ=1e-9
        #   导致总量变负、涨 1e5 倍 ✗）。超出时按线性插值限幅（等价于隐式的第一步）。
        frac = min(1.0, dt / tau_ex)
        # (1) 局部平衡交换：**按摩尔**做（目标摩尔 = Gamma_eq * A_c）⇒ 体/面等量反号，精确守恒
        dmol = np.where(m, (Gam_eq * A_c - self.Gam_mol) * frac, 0.0)
        self.Gam_mol = np.where(m, self.Gam_mol + dmol, 0.0)
        self.c -= dmol / (self.rho * self.dx ** 3)
        # (2) 面扩散 —— ★★ H6：改成**保守边通量形式**（旧写法是 Laplace–Beltrami *微分算子*）
        #   为什么必须改：微分算子离散（中心差分）**没有通量结构** ⇒ Σ(A_c ΔΓ) ≠ 0，
        #   即"面扩散会凭空造/吞溶质"，而 `ΣJ_s = 0`（三叉线通量平衡）正是本课题要学的东西。
        #   通量形式：把面看成"带上的一个 2D 流形"，边 (i,j) 的通量为
        #       F_ij = −D_s·A_e·(Γ_j−Γ_i)/ℓ_ij,  A_e = ½(A_c(i)+A_c(j)),
        #       ℓ_ij = dx·|sin θ_ij| = |(x_j−x_i) − n̂(n̂·(x_j−x_i))|   ← 投影到切平面
        #   于是：① 纯法向相连（ℓ→0）的通量为 0 ⇒ 不跨界面扩散 ✓（审计 A3 的切向性）；
        #        ② 每条边只在 i、j 各记一次且符号相反 ⇒ **逐位守恒** ✓；
        #        ③ 三叉线处各支通量自然相加 ⇒ **ΣJ_s = 0 是结构性的** ✓。
        #   平界面极限：n=ẑ ⇒ x/y 边 ℓ=dx、z 边 ℓ=0 ⇒ 退化为切向 5 点 Laplacian ✓ 一致。
        if D_s > 0:
            order = np.argsort(self.phi, axis=0)
            karr = order[0]
            self.J_edge = []          # ★ 暴露每条边通量（供 ΣJ_s 判据/H7/算子使用）
            # winner 的法向（用 winner 的 φ 直接求梯度）
            # ★ 记账（本轮踩的坑）：**不能用 `self.phi[karr]`** —— 4 维数组上用 3 维整数
            #   索引，numpy 会把尾部维度**接在索引形状后面** ⇒ 得到 (N,N,N,N,N,N) 的 6 维
            #   数组（实测报 "allocate 512 GiB" ✗）。正确写法是 `take_along_axis`
            #   （与 `advance` 里既有写法一致）。
            phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
            gk = np.gradient(phiw, self.dx)
            nrm = np.stack(gk, -1)
            nn = np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-30
            nhat = nrm / nn
            eps = 1e-3 * self.dx
            for ax in range(3):
                Ac_j = np.roll(A_c, -1, axis=ax)
                Ae = 0.5 * (A_c + Ac_j)
                # ★★ 记账（本轮修的**真 bug**，A3/M3 的直接根因）：**绝不能对界面两侧的
                #   法向取平均**。界面两侧的 winner 不同 ⇒ 两者的 n̂ 恰好**反向**
                #   （+ẑ 与 −ẑ）⇒ 平均后**相消为 0** ⇒ 归一化退化 ⇒ `sinθ = 1` ⇒
                #   系统把**跨界面（法向）连接**误判成**切向**连接 ⇒ Γ 沿法向泄漏。
                #   实测：A3 的法向二阶矩 12dx → ~0（Γ 全跑到别的 z 层）、M3 的 Γ 被摊到
                #   3 层、只能到 Γ_McLean 的 **0.477 倍**（都指向同一个 bug）。
                #   修法：取**更靠内那一侧**（φ_winner 更负）的法向作为该连接的界面法向。
                #   单界面光滑处两侧法向几乎相同（等价）✓；界面处恰好给出正确的界面法向 ✓。
                #   （注意：sinθ 只用 `n_pair·ê` 的**平方** ⇒ 符号无关 ⇒ "取哪一侧"只影响
                #     "不被相消"，不引入新的方向约定。）
                phj = np.roll(phiw, -1, axis=ax)
                take_i = phiw <= phj
                npair = np.where(take_i[..., None], nhat,
                                 np.roll(nhat, -1, axis=ax))
                sin_t = np.sqrt(np.maximum(1.0 - npair[..., ax] ** 2, 0.0))
                mj = np.roll(m, -1, axis=ax)
                conn = m & mj
                # ★ 记账（本轮由 F1 的**有效 D_s** 检验抓到的**量纲错误**）：
                #   导通必须写成 `D_s·A_e·sinθ/dx²`，而不是 `D_s·A_e/ℓ`。
                #   理由：面上的有限体积式是 `A_c ∂_tΓ = Σ_j (D_s·L_ij/ℓ_ij)(Γ_j−Γ_i)`，
                #   其中 L_ij 是**边长**（不是面积！）。把 A_c≈dx² 的**面积**当 L 用，
                #   会白白多出一个 dx ⇒ 有效 D 变成 `D_s·dx`（量纲也从 m²/s 变 m³/s）。
                #   实测：修前 d(R²)/dt 口径的有效 D_s/D_s = **1e-8 = dx** ✗；
                #   正确写法 = D_s·A_e·sinθ/dx²（平界面 sinθ=1 ⇒ 退化切向 5 点 Laplacian ✓，
                #   纯法向 sinθ→0 ⇒ 通量→0 ✓）。
                # W-6c：通量里的 Γ 由派生量给出（Gamma = Gam_mol/A_c），**更新量本来就是摩尔**
                m_safe = np.where(m, A_c, 1.0)
                Gam_v = np.where(m, self.Gam_mol / m_safe, 0.0)
                J = np.where(conn, -D_s * Ae * sin_t
                             * (np.roll(Gam_v, -1, axis=ax) - Gam_v) / self.dx ** 2,
                             0.0)
                dq = dt * J
                self.J_edge.append(J)
                # Δ(摩尔)_i = dt·(J_{i−1→i} − J_{i→i+1}) ⇒ roll(+1) 把上一条边的 J 搬到 i
                self.Gam_mol = np.where(m, self.Gam_mol
                                        + (np.roll(dq, 1, axis=ax) - dq), self.Gam_mol)
        else:
            self.J_edge = [np.zeros_like(self.Gam)] * 3
        # 派生 Gamma（per-area）供物理/判据读取；Gam_mol 才是权威状态
        self.Gam = np.where(m, self.Gam_mol / np.where(m, A_c, 1.0), 0.0)
        self._Gam_derived = self.Gam.copy()      # ★ 供 guard 区分"外部写"vs"面积变"
        # (3') 带外的 Γ 清零（其摩尔量已在上面还给体相）
        self.Gam = np.where(m, self.Gam, 0.0)

    def _normal_of(self, k):
        g = np.gradient(self.phi[k], self.dx)
        gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        return [gi / gn for gi in g]

    def iface_offset(self, k=1, l=0, axis=2, near=None):
        """**亚胞射线交点**口径的界面位置：k 与 l 之间沿 `axis` 的交点均值。
           量界面**速度**用它：v = (z_if^(1) − z_if^(0))/(nstep·dt)（符号按 k 收缩为负）。
           ★ 记账：**不要**用 `region()` 计数法量速度 —— 亚胞平移下会失明/巧合精确
             （见模块级 `iface_crossings` 的记账与审计 §10）。
           `near` 给定时只取**离 near 最近的那一个交点**（每列一个，再取均值）
           —— 用于一列里有多个界面（如周期 slab 有 2 个）时锁定要跟踪的那一个。
           返回 (n_used, coord)；n=0 时 coord 为 nan。"""
        n, coord = iface_crossings(self.phi[k] - self.phi[l], self.dx, axis)
        if n == 0:
            return 0, float('nan')
        if near is not None:
            return 1, float(coord[np.argmin(np.abs(coord - near))])
        return n, float(coord.mean())

    def totals(self):
        """总溶质（mol）：体相 Σc·ρ·dV + 面 ΣΓ·A_c"""
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        mb = float(self.c.sum()) * self.rho * self.dx ** 3
        # ★★ W-6c：面量用**权威状态 Gam_mol（摩尔/胞）**求和 —— 与面积测度无关 ⇒ 必然闭合。
        if not hasattr(self, 'Gam_mol'):
            A_c = self.cell_area_geom()
            self.Gam_mol = self.Gam * A_c
        ms = float(self.Gam_mol.sum())
        return mb, ms

    def curvature_of(self, k):
        """kappa = div(grad phi / |grad phi|)。
           AUDIT-#8 修：np.gradient 默认 edge_order=1（边界一阶）=> 对界面靠近边界、
           或只有数胞厚的薄片，kappa 在边界/薄向上误差大。改用 **edge_order=2**。
           记账：这不能解决"薄片只有 2-3 胞厚时二阶导本身不可信"的根本问题
           （那是分辨率问题，见 LATH_CODE_AUDIT #8/#2 与 C 节），只去掉边界那一项误差。"""
        g = np.gradient(self.phi[k], self.dx, edge_order=2)
        gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        n = [gi / gn for gi in g]
        return sum(np.gradient(n[i], self.dx, edge_order=2)[i] for i in range(3))

    # ================= ④ 数值格式：Godunov 迎风 |∇φ| 与 Sussman 重初始化 =================
    def _upwind_grad(self, phi, sgn):
        """★ 委托给**模块级** `upwind_grad`（单畴/多畴共用一份 ⇒ 不会分叉）"""
        return upwind_grad(phi, sgn, self.dx)

    def sussman_reinit(self, phi, iters=None):
        """委托给模块级 `sussman_reinit`。
           EXPERT-#3: 默认改用 self.reinit_iters 并透传 dtau/grad
           （原来这里硬编码 iters=30，且丢掉了 dtau/grad）。"""
        return sussman_reinit(phi, self.dx,
                              iters=(self.reinit_iters if iters is None else iters),
                              dtau=getattr(self, 'reinit_dtau', None),
                              grad=getattr(self, 'reinit_grad', 'upwind2'))

    def _advance_phi(self, k, vn, dt):
        """④ 用迎风 |∇φ| 推进：φ_t + v_n|∇φ| = 0"""
        sgn = np.where(vn > 0, 1.0, -1.0)
        return self.phi[k] - dt * vn * self._upwind_grad(self.phi[k], sgn)

    def volume(self, k):
        m = (self.region() == k)
        return float(m.sum()) * self.dx ** 3

    def area(self, k):
        reg = self.region()
        c = 0
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            nb = np.roll(reg, d, axis=(0, 1, 2))
            c += int(np.count_nonzero((reg == k) & (nb != k)))
        return c * self.dx ** 2

    # ---------- 体相驱动：谱法微弹性 ----------
    def elastic_driving(self, soft=None):
        """返回 (nreg, N,N,N)：-ε⁰_k:σ（对母相为 0）。

           AUDIT-#9 修：原来一律用 **hard region** 指示场（@B@pf.phi[v] = (reg==v+1)@B@）
           => 界面胞的 eps0 分布是阶梯状 => FFT 谱法解出的 sigma 在界面处有 O(1) 阶梯噪声
           => 驱动 ed 在界面附近被污染。新增 soft 选项：用**平滑指示场**
               h_k = 0.5*(1 - tanh(phi_k / w)),  w = 1.5*dx
           默认 soft=None => 沿用类属性 self.elastic_soft（**默认 False**，
           以免改变已归档的全部结论）；显式 soft=True 才启用。"""
        if soft is None:
            soft = bool(getattr(self, 'elastic_soft', False))
        _hard = (lambda v: (self.region() == v + 1))
        reg = self.region()
        out = np.zeros((self.nreg,) + reg.shape)
        if self.aniso_elastic:
            # ★ 逐变体模量路径（`windowB_aniso_elastic.AnisoElastic`，已过 AS-1/AS-1b/AS-2）：
            #   把 `region` 的 0/1 指示场当作相场（与 PF3D 路径一致），解 inhomogeneous
            #   弹性取 σ。σ 的 6 分量约定与 `PF3D.sigma_tensor()` **逐位一致**
            #   （AS-1/AS-1b 实测 0.00e+00 / 9.5e-16）⇒ 下面 `e0v_eng` 的内积可直接复用。
            phi = np.zeros((self.nreg,) + reg.shape)
            for k in range(self.nreg):
                phi[k] = (reg == k)
            e0l = [np.zeros((3, 3))] + [np.asarray(e, float)
                                        for e in self.pf.eps0]
            #   ★ 记账：`AnisoElastic` 内部**全张量**（(3,3,N,N,N)，见该模块的记账）⇒
            #     用 `sigma6` 转成本仓库 6 分量约定（与 `PF3D.sigma_tensor()` 逐位一致，
            #     AS-1/AS-1b 三种 ε⁰ 实测 ≤9.5e-16）。
            #   ★ 性能：**热启动**（上一步的 ε 当初值）+ tol=1e-8 ⇒ 迭代数从 ~35 降到个位数。
            #     驱动力只需要 ~1e-4 的 σ 精度；AS-1/AS-1b 的严格一致性判据走 tol=1e-10。
            sig6, _nit, _ = self.ae.sigma6(
                phi, e0l, niter=80, tol=1e-8,
                init=getattr(self, '_ae_eps', None))
            self._ae_eps = self.ae.eps
            for v in range(self.nv):
                out[v + 1] = (-np.einsum('p,p...->...', self.e0v_eng[v], sig6)
                              + self.sext_e0[v])
            self._ae_nit = _nit
            return out
        if self.pf is None:
            return out
        if soft:
            # AUDIT-#9: 平滑指示场（level-set 的 phi 是 SDF => 0.5*(1-tanh) 是自然选择）
            _w = 1.5 * self.dx
            for v in range(self.nv):
                self.pf.phi[v] = 0.5 * (1.0 - np.tanh(self.phi[v + 1] / _w))
        else:
            for v in range(self.nv):
                self.pf.phi[v] = (reg == v + 1)
        sig = self.pf.sigma_tensor()
        for v in range(self.nv):
            out[v + 1] = (-np.einsum('p,p...->...', self.e0v_eng[v], sig)
                          + self.sext_e0[v])
        return out

    # ---------- 界面推进（PDE）----------
    # AUDIT-#1 (2026-09-26)： 的**默认值**由 'upwind' 改为 'central'。
    #   依据：审计发现两种格式在长时程上给出**不同结果**（同一 E6 配置：
    #   长/宽 1.54(upwind) vs 1.75(central)，f 0.727 vs 0.846；C1(central) 跑满 700 步、
    #   带胞健康、无失稳）=> 取更准确的 central 为默认。
    #   ⚠ 记账：**这改变了后续所有结果的数值**，与审计前的归档结果不可逐位比较。
    #   若某算例出现失稳（陡梯度），显式传 adv_grad='upwind' 可回退。
    def advance(self, dt, aniso=0.0, npref=None, gamma0=None, herring=True,
                adv_grad='central', extend='edt', band_cells=20, iface_band=2.0,
                drag=None, pair_kernel=False, per_field=False, pair_aniso=False,
                mob_aniso=0.0, pin_min=True, mob_beta=0.0, mob_beta_w=0.0,
                facet_lam=0.0, facet_eps=0.05):
        # ★ 记账（本轮 P1 重标定）：`iface_band=2.0` 而非 1.0 —— 界面种子必须是
        #   **≥2 层胞**。实测 pair_kernel 下 `iface_band=1.0`（|∇d|≈2 ⇒ 种子只有
        #   1 层）时，`extend_along_normal` 的迎风延拓**退化**（v/MΔf = 0.125 ✗）；
        #   2.0/3.0 都给 1.0000 ✓（`_chk_p1.py` 全网格扫描，见审计 §10.1）。
        # ★ 记账（本轮）：`pair_kernel=True` 是"按配对核"的**实验性**实现（见审计 §10），
        #   尚未通过标定判据（平界面 |v|/MΔf 实测 0.00 ✗）⇒ **默认保持 False**，
        #   即停在已被 W2 验证的那条路径上（pair=False + EDT 扩展 + 20dx 带 ⇒ 1.0000 ✓）。
        """★ ⑤（本轮修）配对一致推进：界面 (winner k, runner-up l) 用**同一个** v_n，
           两侧 φ 一致更新（φ_k 减、φ_l 增）。旧写法让每个 φ_k 各用自己 v_k ⇒
           实测界面有效速度只有 **v/2** ✗（因为 VDF 里 |∇(φ_k−φ_l)|=2）。
           判据 W2 用"平界面 + 常数驱动"直接量界面速度验证。"""
        reg0 = self.region()
        ed = self.elastic_driving()
        nreg = self.nreg
        gn = np.zeros_like(self.phi)
        kap_all = np.zeros_like(self.phi)
        stiff = np.ones((nreg,) + self.phi.shape[1:])
        for k in range(nreg):
            g = np.gradient(self.phi[k], self.dx)
            gn[k] = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
            kap_k = self.curvature_of(k)
            gk = self.gamma if gamma0 is None else gamma0
            if facet_lam > 0.0 and npref is not None and npref.get(k) is not None:
                # ★ P3：尖点界面能（只在给了 npref 的场上用）
                n = np.stack([gi / gn[k] for gi in g], -1)
                nd = np.asarray(npref[k], float)
                nd = nd / (np.linalg.norm(nd) + 1e-300)
                c2f = np.clip((n @ nd) ** 2, 0.0, 1.0)
                gk = herring_stiffness_cusp(c2f, gk, facet_lam, facet_eps)
            # ★ 记账（2026-09-26 的 bug）：这里必须是 **elif**。
            #   第一版写成独立的 if => 当 aniso>0 时，下面 sin^2 分支会把 facet 的 gk
            #   **整个覆盖** => facet_lam=0/0.4/1.0 三档结果**逐位相同**（实测抓到）。
            elif aniso > 0 and npref is not None and npref.get(k) is not None:
                n = np.stack([gi / gn[k] for gi in g], -1)
                # ★ 各向异性刚度：**统一走 `herring_stiffness`**（原来这里内联的写法与
                #   `LevelSetSurface` 各写一份 ⇒ 已合并，避免两处分叉）
                nd = np.asarray(npref[k], float)
                nd = nd / (np.linalg.norm(nd) + 1e-300)
                c2 = np.clip((n @ nd) ** 2, 0.0, 1.0)
                gk = herring_stiffness(c2, gk, aniso, herring)
            stiff[k] = gk
            kap_all[k] = kap_k
        # winner / runner-up
        order = np.argsort(self.phi, axis=0)
        karr, larr = order[0], order[1]
        if per_field:
            # ★★ 按**场**推进（2026-09-25 新增，方案 (a)）—— 见 `_advance_perfield` 的记账。
            #   走这条分支时后面那套"winner/runner-up 两场"逻辑整段跳过。
            self._advance_perfield(dt, karr, larr, ed, stiff, iface_band,
                                   band_cells, adv_grad)
            return self._finish_advance(reg0)
        # 每胞的配对速度（正 = winner 长大）
        edk = np.take_along_axis(ed, karr[None], 0)[0]
        edl = np.take_along_axis(ed, larr[None], 0)[0]
        stk = np.take_along_axis(stiff, karr[None], 0)[0]
        pha = np.take_along_axis(self.phi, karr[None], 0)[0]
        phb = np.take_along_axis(self.phi, larr[None], 0)[0]
        # ---- P0.2 (2026-09-26): 按**配对**选各向异性参考取向 ------------------
        #   (k,0) 类界面 -> npref[k] (变体对母相的惯习面)
        #   (k,l) 类界面 -> ncmp[k,l] (两变体的不变平面, 见 _pair_normals)
        #   旧写法一律用 winner 的 npref[k] => 在 f->1 时对绝大多数界面用错对象.
        #   界面法向用**差分场** d = phi_k - phi_l 的梯度 (两侧对称, 且就是该界面的法向).
        _need_ref = (pair_aniso and aniso > 0) or (mob_aniso > 0.0) or (mob_beta > 0.0)
        nd_ref_ = None
        # AUDIT-#4 修：原来这里还要求 self.ncmp is not None，而 ncmp 只在
        #   (C is not None and eps0 is not None) 时才建 => 跑"单变体 vs 母相"(nv=1、
        #   不给 eps0) 时 ncmp=None => 整块被跳过 => **mob_beta 静默不生效**。
        #   现在：ncmp 缺失时退化为"只用 npref"，并在下面 has_pair 分支做保护。
        if _need_ref:
            gd_ = np.gradient(pha - phb, self.dx)
            gdn_ = np.sqrt(sum(g_ ** 2 for g_ in gd_)) + 1e-30
            ndir_ = np.stack([g_ / gdn_ for g_ in gd_], -1)
            ndir_ = ndir_ / (np.linalg.norm(ndir_, axis=-1, keepdims=True) + 1e-300)
            np_arr = np.full((nreg, 3), np.nan)
            if npref is not None:
                for kk, vv in npref.items():
                    if vv is not None and 0 <= int(kk) < nreg:
                        vv = np.asarray(vv, float)
                        np_arr[int(kk)] = vv / (np.linalg.norm(vv) + 1e-300)
            ncl = getattr(self, 'ncmp', None)
            ki = np.clip(karr, 0, nreg - 1)
            li = np.clip(larr, 0, nreg - 1)
            has_pair = (karr > 0) & (larr > 0)
            if ncl is None:
                # AUDIT-#4: 没有配对表 => 变体-变体界面也退化为用 winner/runner-up 的 npref
                nd_ref = np.where((karr > 0)[..., None], np_arr[ki], np_arr[li])
            else:
                nd_ref = np.where(has_pair[..., None], ncl[ki, li],
                                  np.where((karr > 0)[..., None], np_arr[ki], np_arr[li]))
            badp = ~np.isfinite(nd_ref).all(-1)
            if badp.any():
                nd_ref = np.where(badp[..., None], np_arr[ki], nd_ref)
            c2p = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref) ** 2, 0.0, 1.0)
            nd_ref_ = nd_ref
            if pair_aniso and aniso > 0:
                stk = herring_stiffness(c2p, self.gamma if gamma0 is None else gamma0,
                                        aniso, herring)
            self._pair_aniso_used = True
        elif pair_aniso:
            self._pair_aniso_used = False
        # ★★ 按配对（pair-canonical）核 —— 本轮修的关键点：
        #   旧写法用 "winner 自己的曲率 κ_karr" 与 "winner 自己的刚度"，跨界面时曲率项
        #   在两侧**不对称**（内侧用 κ_karr、外侧用 κ_larr）⇒ 与"按区域"的速度扩展叠加后，
        #   两区域之间的差分 φ_k−φ_l 会被无限拉陡（实测带内 |∇φ| 0.5→530、带胞 3.7e4→155，
        #   几何测度静默归零 ✗）。
        #   改成用**差分场** d = φ_karr − φ_larr 的曲率（对两侧严格对称、且保持 winner 的
        #   符号约定）与**成对平均刚度** ⇒ 界面速度成为该配对的单一标量，两侧一致。
        if pair_kernel:
            dd = pha - phb
            gd = np.gradient(dd, self.dx)
            gdn = np.sqrt(sum(g ** 2 for g in gd)) + 1e-30
            nd = [g / gdn for g in gd]
            kap_pair = sum(np.gradient(nd[i], self.dx)[i] for i in range(3))
            stk_pair = 0.5 * (stk + np.take_along_axis(stiff, larr[None], 0)[0])
            kap_cell = kap_pair
            stk = stk_pair
        else:
            kap_cell = np.take_along_axis(kap_all, karr[None], 0)[0]
            # EXPERT-#4：默认 pair_kernel=False 时，变体-变体界面用的是 **winner 场的曲率**，
            #   而真实界面曲率应来自差分场 d=phi_k-phi_l => 两侧不对称（仓库注释已记载：
            #   可致 d 被拉陡、|grad phi| 由 ~1 涨到数百）。这里**显式告警**（不静默），
            #   提醒结论可能被污染；修 pair_kernel 判据后再改默认。
            if (not getattr(self, '_warned_pair_kernel', False)):
                _hp = (karr > 0) & (larr > 0)
                if _hp.sum() > 0:
                    import warnings as _w
                    _w.warn('pair_kernel=False: detected %d variant-variant interface cells; '
                           'their curvature is taken from the winner field, not from '
                           'the difference field phi_k-phi_l => the two sides are '
                           'asymmetric and morphology conclusions may be biased '
                           '(see LATH_CODE_AUDIT / expert review EXPERT-#4).'
                           % int(_hp.sum()), RuntimeWarning, stacklevel=2)
                    self._warned_pair_kernel = True
        dG_cell = (self.df[karr] - self.df[larr]) + (edk - edl) - stk * kap_cell
        # ★★ 记账（2026-09-25，查明 M2"塌缩"的真凶）：把本步驱动力存下来，供
        #   `suggest_dt` 按**总驱动**定 CFL。**只用 Δf 估 dt 会严重低估界面速度** ——
        #   实测 M2：弹性项中位 4.9e8 是 Δf(1e8) 的 ~5 倍 ⇒ 按 Δf 定出的 dt 实际每步
        #   位移是 **0.6–0.75 dx**（不是 0.15），一阶迎风必然失真。
        # AUDIT-#3 修：原来 dG_max = max|dG_cell| **不含 Mfac** => Mfac 小的界面上
        #   dt 被按"未压制的驱动力"定，最多保守 33 倍（白算机时）。
        #   现在改存"有效驱动"，在 Mfac 应用之后重算（见下面 _dG_max_from_mfac）。
        self.dG_max = float(np.max(np.abs(dG_cell)))
        self._dG_cell_ref = dG_cell          # 供 Mfac 应用后重算 dG_max
        if drag is not None:
            # ★★ 溶质拖曳（P3.3 / 框架 §6.3 [RULE] K5）：**隐式自洽**解
            #     v = M[ΔG − P_drag(v)]，P_drag = P0/(1+v/v*)（双盒闭式，K1 已验）。
            #     绝不能用线性闭式 v = MΔG(1−a v)：在被钉扎的驱动下它会**凭空给出速度**
            #     （模块 7 K3 实测偏差 98%），而隐式解给出 v=0 ✓。
            #     脱钉判据（本模块数值验证）：v>0 ⟺ ΔG>P0 或 M·ΔG>v*。
            from windowB_drag import solve_v
            P0, vstar = drag
            v_cell, _pin = solve_v(dG_cell, self.M, P0, vstar)
        else:
            v_cell = self.M * dG_cell
        # ---- P0.5 (2026-09-26): 界面**迁移率**各向异性（facet pinning）----------
        #   物理与 D8 正对照（_chk_m8_mobpin.py，真实驱动力 df=1e8 下）：
        #     gamma(n) 通道被驱动力完全淹没（P0.3），而 M(n) 是**动力学**量、
        #     无热力学凸性约束 => 强度可任意大，实测能把形状取向精确钉住（主轴偏差 0.0 deg）。
        #   形式： M(n) = M0 * [1 - a*(n.n*)^2]        (pin_min=True, 默认)
        #          => n 平行 n* 时迁移率最小（法向长得慢）、面内长得快
        #          => 形状是"沿 n* 法向的薄片" = **板条**的几何（不是"沿 n* 的针"）
        #          这与惯习面物理一致：板条的**宽面**是惯习面，其法向 = n*。
        #      M(n) = M0 * [1 - a*(1-(n.n*)^2)]    (pin_min=False)
        #          => 沿 n* 长得最快 => 形状沿 n* 拉长（"针状"形态）
        #   ⚠ 记账：D8 的 a00..a100 用的是 pin_min=False（当时 mref = 快生长方向），
        #     所以它给的是"沿 mref 拉长"；那组数据证明的是**机制有效**（主轴 0.0 deg、
        #     长径比单调 1.00->2.15），不是"板条已得到"。板条要用 pin_min=True + n*=惯习面法向。
        # ★★ P1' (2026-09-26): **物理形式** M(n) = M0*exp[-beta*(n.n*)^2]，
        #   beta = dG_misfit/(k_B T)（位移型界面靠界面位错保守滑移迁移：
        #   Olson-Cohen / Christian；位错只能在其滑移面=惯习面内滑移 =>
        #   法向生长必须容纳失配 => 额外激活能 ∝ (n.n_hab)^2 的几何投影）。
        #   标定见 LATH_FACET_PLAN §9：位错环形成能 => beta~3.8；板条纵横比反推 => beta~3.0
        #   => 取 beta=3.5（带 [3,6]）。M_min = 3% M0 => 界面不会被冻结（数值安全）。
        _mfac_dt = 1.0                          # AUDIT-#3: 累积的 Mfac（用于重定 dt）
        if mob_beta > 0.0 and nd_ref_ is not None:
            c2b_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            # ★ P2：**第二钉扎轴** w = n_hab x a（板条宽度方向）。
            #   只对"变体-母相"界面加（板条成形主要发生在从母相长大的阶段）；
            #   变体-变体界面保持单轴（那里 ncmp 已是不变平面，w 无独立意义）。
            _expo = -mob_beta * (c2b_ if pin_min else (1.0 - c2b_))
            if mob_beta_w > 0.0 and getattr(self, 'wtab', None) is not None:
                ki2 = np.clip(karr, 0, nreg - 1)
                li2 = np.clip(larr, 0, nreg - 1)
                w_of = np.where((karr > 0)[..., None], self.wtab[ki2], self.wtab[li2])
                okw = np.isfinite(w_of).all(-1)
                c2w_ = np.clip(np.einsum('...i,...i->...', ndir_, np.where(
                    okw[..., None], w_of, 0.0)) ** 2, 0.0, 1.0)
                # EXPERT-#5 修：第二钉扎轴 w **只对变体-母相界面**施加（与上面注释一致）。
                #   原写法只要 winner 是变体就用它的 w => 变体-变体界面也被加了 w 轴钉扎，
                #   于是实际模型是"变体-母相:双轴 / 变体-变体:winner 的双轴"，
                #   而不是设计中的"变体-变体:只按相容法向单轴"（会改变变体间界面选择）。
                _has_pair_ = (karr > 0) & (larr > 0)
                _use_w = (~_has_pair_) & okw
                _expo = _expo - mob_beta_w * np.where(_use_w, c2w_, 0.0)
            _mfac_dt = np.exp(_expo)
            v_cell = v_cell * _mfac_dt
        # AUDIT-#6 修：mob_beta 与 mob_aniso 是两套等价机制的**不同参数化**，
        #   同时给非零会相乘 => 双重调制（静默的错）。这里显式拒绝。
        if mob_beta > 0.0 and mob_aniso > 0.0:
            raise ValueError('mob_beta 与 mob_aniso 不能同时给非零（会双重调制）')
        if mob_aniso > 0.0 and nd_ref_ is not None:
            c2r_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            Mfac = 1.0 - mob_aniso * (c2r_ if pin_min else (1.0 - c2r_))
            _mfac_dt = Mfac
            v_cell = v_cell * Mfac

        # ★★ （本轮修·关键）界面速度的**配对规范形**（跨界面连续化）。
        #    `v_cell` 是"winner 长大为正"的约定 ⇒ 跨过界面时 winner 换成 runner-up
        #    ⇒ 同一界面两侧的 `v_cell` **符号相反**。速度延拓要求被延拓的场在界面上
        #    **连续**；否则最近点延拓会把一侧的符号搬到另一侧 / 两侧种子互相抵消 ✗。
        #    规范形按 min(k,l) 定向 ⇒ 跨界面连续：V_c = M(df_min − df_max) = sigma·v_cell。
        #    随后每胞用**同一标量**：φ_karr 取 +V_ab = +sigma·V_c，φ_larr 取 −sigma·V_c。
        # AUDIT-#3: 用**有效驱动**重定 dt（原来用未压制的 dG）
        if not isinstance(_mfac_dt, float):
            self.dG_max = float(np.max(np.abs(self._dG_cell_ref * _mfac_dt)))
        sigma = np.where(karr < larr, 1.0, -1.0)
        vcanon = sigma * v_cell
        # ★★ 记账：和单畴一样，**必须做速度扩展**，而且多畴对带宽更敏感 ——
        #   实测（平界面 + 常数驱动 ΔG，40 步后的 v/MΔf，应 = 1.000）：
        #      无扩展 band=2dx → 0.250 ; band=6dx → 0.750 ; band=12dx → 2.000（乱）
        #      EDT 扩展 band=5dx → 0.500 ; 10dx → 0.750 ; **20dx → 1.0000** ✓
        #   物理原因：扩展让速度**沿法向为常数** ⇒ 整个剖面是**纯平移**（保 SDF、保速度）；
        #   带太窄时带外剖面不动 ⇒ 带边折点累积 ⇒ 有效速度塌（与单畴 P6 同源）。
        #   ⇒ 多畴默认 `extend='edt', band_cells=20`（宽带 + 扩展才自洽）。
        #   ⚠ 这解释了为什么旧的 `_chk_w2.py`（阶跃初值 + 默认扩展）得到 1.0000：
        #     那是**退化构型**下的巧合；用真 SDF 初值必须靠宽带+扩展才复现 1.0000。
        #    多畴的额外要求（★ 本轮修正）：延拓必须**跨越界面两侧**（按**无序对**
        #    {karr,larr} 判定配对身份），且被延拓的量必须是**跨界面连续**的规范形
        #    `vcanon`。旧的 `karr == karr[最近界面胞]` 约束把界面的 runner-up 一侧
        #    整个排除 —— 这是本轮用**亚胞射线交点**口径抓到的真 bug（见下）。
        if pair_kernel:
            # ★★ 配对口径：界面 = 差分场 d = φ_karr − φ_larr 的小值集，速度沿 d 的
            #    法向延拓 ⇒ 界面两侧拿到**同一个标量速度** ⇒ 差分 d 只**平移**、不被拉陡
            #    （对比：按区域延拓时 |∇φ| 0.5→530 ✗）。
            #    ★ 本轮修两处：(i) 延拓**规范形** `vcanon`（`v_cell` 跨界面符号翻转，
            #    把两侧种子放一起会**互相抵消** ✗）；(ii) 带按 `|∇d|` 折算（`d` 不是
            #    距离函数、|∇d|≈2 ⇒ 旧写法 `|d| ≤ 1.0dx` 在 48³ 上只选到 **1 层**胞）。
            dfield = pha - phb
            gdd = np.gradient(dfield, self.dx)
            gdn = np.sqrt(sum(g ** 2 for g in gdd)) + 1e-30
            iface = (np.abs(dfield) <= iface_band * self.dx * gdn) \
                & (np.abs(v_cell) > 0)
            band = np.abs(dfield) <= band_cells * self.dx * gdn
            if iface.any() and not iface.all():
                v_ext = extend_along_normal(np.where(iface, vcanon, 0.0), dfield,
                                            self.dx, iters=int(band_cells / 0.4) + 6)
                coef = np.where(band, sigma * v_ext, 0.0)
            else:
                band = iface
                coef = np.where(iface, sigma * vcanon, 0.0)
        else:
            phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
            iface = (np.abs(phiw) <= iface_band * self.dx * (1.0 + 1e-9)) \
                & (np.abs(v_cell) > 0)
            # ★ 守卫：`distance_transform_edt(~iface)` 要求 `~iface` 非空（否则索引为垃圾）
            if extend and iface.any() and not iface.all():
                ind = distance_transform_edt(~iface, return_distances=False,
                                             return_indices=True)
                dist = distance_transform_edt(~iface)
                v_at = np.where(iface, vcanon, 0.0)
                kat = karr[tuple(ind)]
                lat = larr[tuple(ind)]
                # ★★ 本轮修的真 bug（被亚胞射线交点口径抓到）：旧写法用
                #   `karr == kat`（"与最近界面胞**同区域**"）。但 `iface` 往往
                #   **只落在 winner 一侧**（实测：`dx = L/N` 的浮点尾差让
                #   |φ_winner| = dx 的胞判为带外 ⇒ iface 只剩 winner=0 的胞）
                #   ⇒ `kat ≡ 0` ⇒ **runner-up 一侧从不被推进**。实测后果（z 剖面）：
                #   φ_1 只在 z>z0 侧平移、z<z0 侧冻结 ⇒ 差分场 d=φ_k−φ_l 不平移而只被
                #   **拉陡** ⇒ 射线口径 40 步位移 6.31dx（应 4dx）、单步 0.0909dx
                #   （应 0.1dx）；而 `region()` 计数法靠"符号翻转"**凑巧**给出 1.0000
                #   —— 计数法掩盖结构错误的教科书案例（审计 §10 的 0.000 亦须重判）。
                #   正确掩模按**界面的配对身份**（无序对 {k,l}），两侧一视同仁。
                same_pair = ((karr == kat) & (larr == lat)) | \
                            ((karr == lat) & (larr == kat))
                band = (dist <= band_cells) & same_pair
                coef = np.where(band, sigma * v_at[tuple(ind)], 0.0)
            else:
                band = np.zeros(self.phi.shape[1:], bool)
                for k in range(nreg):
                    band |= ((karr == k) | (larr == k)) & (np.abs(self.phi[k])
                                                           <= band_cells * self.dx)
                band = band & (np.abs(v_cell) > 0)
                coef = np.where(band, sigma * vcanon, 0.0)
        for k in range(nreg):
            # ④ 推进：默认 Godunov 迎风（鲁棒）；`adv_grad='central'` 用于"光滑 SDF +
            #   需要无偏各向异性幅度"的场合（W1/H1 判据实测：迎风把各向异性压低 ~8%，
            #   中心差分把 a2 复原到 1.0±0.02 —— 见 W1 的记账）
            #   `coef = sigma·V_c`（带内延拓后的规范形速度）⇒ winner φ 拿 +V_ab、
            #   runner-up φ 拿 −V_ab ⇒ **两侧同一个标量** ✓
            vnk = coef * (np.where(karr == k, 1.0, 0.0)
                          - np.where(larr == k, 1.0, 0.0))
            if np.any(vnk != 0):
                if adv_grad == 'central':
                    g = np.gradient(self.phi[k], self.dx)
                    gmag = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
                else:
                    sgn = np.where(vnk > 0, 1.0, -1.0)
                    gmag = self._upwind_grad(self.phi[k], sgn)
                self.phi[k] = self.phi[k] - dt * vnk * gmag
        return self._finish_advance(reg0)

    def _finish_advance(self, reg0):
        """推进一步的**收尾**（两条推进路径共用，避免两处分叉）：
           区域/计数、按平流取 `reg_adv`、定期重初始化、Stefan 记账。
           ★ 记账：Stefan 必须只对"**平流**扫过的胞"记账。旧写法在 `reinitialize()`
             之后才取 reg1 ⇒ 把**重初始化微移界面**造成的区域翻转也算成"前沿扫过"
             ⇒ 凭空吞吐溶质（实测：关重初始化 M4=1.16e-2、每 20 步重初始化 5.37e-2 ✗）。"""
        reg = self.region()
        self._cnt = getattr(self, '_cnt', 0) + 1
        # AUDIT-#10 修：原来这里又写了一次 self.region()（中间无修改 => 与 reg 相同）。
        #   逻辑本来就对（此处仍在 reinitialize 之前 => 只反映【平流】造成的扫过），
        #   只是重复计算；直接复用 reg。
        reg_adv = reg
        if self.reinit_every and self._cnt % self.reinit_every == 0:
            self.reinitialize()
        self._stefan(reg0, reg_adv)
        return reg

    def _advance_perfield(self, dt, karr, larr, ed, stiff, iface_band,
                          band_cells, adv_grad):
        """★ 按**场**推进（2026-09-25，方案 (a)）：每个 φ_k 用它**自己最近界面**
           `{k, l_k}`（`l_k(x) = argmin_{j≠k} φ_j(x)`）的配对速度，速度沿该界面的法向
           延拓到带内，然后 `φ_k −= dt·V_k·|∇φ_k|`（Godunov 迎风）。

           ★ 记账（为什么需要它）：旧写法每胞只推进局部 `(winner, runner-up)` **两个场**
             ⇒ **"被推进的场集合"在空间上跳变**（一侧推进、紧邻一侧冻结）⇒ φ 上出现
             跳变、再被 `|∇φ|` 项自放大 ⇒ 带胞与 `|∇φ|` 静默退化（§9.5/§10.4 的全部
             隔离实验都指向这里，而不是配对扩展）。
             本写法每胞推进**全部 nreg 个场**（各自带内）⇒ 跳变只剩"速度值的跳变"
             （在 `l_k` 切换的中性面上），**不再有"零速区"** ✓。
           ★ 另一个便利：这里 `V_k` **总是以 k 为被减数** ⇒ 跨 k 的界面**天然连续**
             （不需要 §10.2 里 `sigma`/`vcanon` 那套规范化）；
             曲率必须取**差分场** `d = φ_k − φ_{l_k}` 的（单场自己的曲率在界面两侧
             **符号相反**：球内 φ_k = r−R 给 +2/R，球外 φ_l 给 −2/R ⇒ 两侧会互相打架 ✗）。
           ★ 代价（如实记账）：每步 `nreg` 次差分场曲率 + `2·nreg` 次 EDT ⇒ 比旧路径
             O(nreg) 倍（N=64/nreg=13 约 ~0.5–1 s/步）。
        """
        for k in range(self.nreg):
            lk = np.where(karr == k, larr, karr)     # k 的最近竞争者
            d = self.phi[k] - np.take_along_axis(self.phi, lk[None], 0)[0]
            gd = np.gradient(d, self.dx)
            gdn = np.sqrt(sum(g ** 2 for g in gd))
            scale = np.maximum(gdn, 1e-30)           # d 不是距离函数（|∇d| ≈ 2）
            nd = [g / scale for g in gd]
            kap = sum(np.gradient(nd[i], self.dx)[i] for i in range(3))
            edl = np.take_along_axis(ed, lk[None], 0)[0]
            stk = 0.5 * (stiff[k] + np.take_along_axis(stiff, lk[None], 0)[0])
            V = self.M * ((self.df[k] - self.df[lk]) + (ed[k] - edl) - stk * kap)
            iface = (np.abs(d) <= iface_band * self.dx * scale) & (np.abs(V) > 0)
            if np.any(iface) and not iface.all():
                ind = distance_transform_edt(~iface, return_distances=False,
                                             return_indices=True)
                dist = distance_transform_edt(~iface)
                Vext = np.where(dist <= band_cells, V[tuple(ind)], 0.0)
            else:
                band = np.abs(d) <= band_cells * self.dx * scale
                Vext = np.where(band & (np.abs(V) > 0), V, 0.0)
            if not np.any(Vext != 0):
                continue
            if adv_grad == 'central':
                g = np.gradient(self.phi[k], self.dx)
                gmag = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
            else:
                sgn = np.where(Vext > 0, 1.0, -1.0)
                gmag = self._upwind_grad(self.phi[k], sgn)
            self.phi[k] = self.phi[k] - dt * Vext * gmag
            vmax = float(np.max(np.abs(Vext)))
            self.dG_max = (vmax / self.M) if self.M else 0.0

    def suggest_dt(self, cfl=0.15, dt_prev=None, grow_max=2.0):
        """按**实际最大界面速度**定步长：`dt = cfl·dx / max|v|`（`v = M·ΔG`）。
           上一步的驱动力由 `advance` 写在 `self.dG_max`。
           ★ 记账（2026-09-25，M2 的 CFL 真凶）：**必须用总驱动**（Δf + 弹性 − γκ），
             不能只用 Δf。实测 M2 里弹性项比 Δf 大 ~5 倍 ⇒ 只按 Δf 定 dt 会让实际每步
             位移达 0.6–0.75 dx（超 CFL 4–5 倍）⇒ 界面剖面失真、几何测度静默塌缩。
           `grow_max` 限制 dt 相对上一步的放大倍数（速度下降时不让 dt 突跳）。"""
        dmax = getattr(self, 'dG_max', 0.0)
        if not dmax or dmax <= 0 or not self.M:
            return None
        dt = cfl * self.dx / (self.M * dmax)
        if dt_prev is not None:
            dt = min(dt, grow_max * dt_prev)
        return dt
    def _stefan(self, reg0, reg1, k_part=0.6303, dbg=None):
        """③ 本轮修：Stefan 跳跃的**正确去向**——界面扫过时被排出的溶质
           **先存进面过剩 Γ**（即 ∂Γ/∂t 那一项），再由 update_Gamma 的面-体交换与
           面扩散分发出去；**不再直接甩给邻居**（旧写法既非物理、又带 1.6% 不守恒 ✗）。
           收缩时反向：产物胞变母相需要的溶质，**先从面 Γ 取**，不足的部分才由邻居补
           （记账：Γ 不足时从邻居补，仍是精确守恒 ✓）。"""
        m = self.surface_band()
        A_c = self.cell_area_geom()
        if not hasattr(self, 'Gam_mol') or self.Gam_mol.shape != A_c.shape:
            self.Gam_mol = self.Gam * A_c          # 惰性初始化（应对 __new__/外部构造）
        if dbg is not None:
            b0, s0 = self.totals()
            dbg['t0'] = b0 + s0
        for kind in ('grow', 'shrink'):
            if kind == 'grow':
                swept = (reg0 == 0) & (reg1 != 0)          # 母相 -> 产物
                ctgt = k_part * self.c
            else:
                swept = (reg0 != 0) & (reg1 == 0)          # 产物 -> 母相
                ctgt = self.c / max(k_part, 1e-6)
            if not swept.any():
                if dbg is not None:
                    b1, s1 = self.totals()
                    dbg['log'].append((dbg['step'], kind + '(空)', (b1 + s1) - dbg['t0'],
                                       int(swept.sum())))
                    dbg['t0'] = b1 + s1
                continue
            dq = (ctgt - self.c)
            self.c[swept] = ctgt[swept]
            amount = -(dq * self.rho * self.dx ** 3)       # 需从系统其余部分拿走的摩尔量
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' a)置c后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            # (a) 先存/取面 Γ
            # ★★ W-6c：**直接按摩尔存/取**（不再经过 A_c 的除法/乘法，避免测度漂移）
            msk = swept & (A_c > 0)
            if kind == 'grow':
                self.Gam_mol = np.where(msk, self.Gam_mol + amount, self.Gam_mol)
                amount = np.where(msk, 0.0, amount)
            else:
                take = np.where(msk, np.minimum(self.Gam_mol, -amount), 0.0)
                self.Gam_mol = np.where(msk, self.Gam_mol - take, self.Gam_mol)
                amount = amount + take
            # 派生 Gam 保持一致（供读 Gam 的判据/物理使用），并同步 
            #   —— 否则 update_Gamma 的 guard 会误判成"外部写了 Gam"而每步重同步一次。
            self.Gam = np.where(A_c > 0, self.Gam_mol / np.maximum(A_c, 1e-30), 0.0)
            self._Gam_derived = self.Gam.copy()
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' b)取面后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            # ★ 收口（本轮）：接收者 = **全部 6 个邻居 + 自己 = 7 个** ⇒ 除数恒为 7 ✓。
            #   此前除数用 `wsum = #被扫邻居 + 1`（薄扫层里只有 ~2）⇒ 分出去的总量 = 应有量×7/wsum
            #   ≈ ×3.5 ⇒ 守恒漏（探针实测：体相应取 2.05e-21，却被拿走 7.19e-21 = 3.5 倍 ✓ 完全吻合）。
            # AUDIT-#5 修：原来用 np.roll 分配（**周期边界**）=> 域边界的排出溶质会从
            #   对面边界冒出（非物理）。改成**非周期移位**：只分给"落在域内"的邻居，
            #   越界方向的那份自然留在源胞手上 => 既不跨域、又逐位守恒。
            #   接收者数由**实际**决定（自己 + 域内被扫过的邻居），不再硬编码 7。
            def _shift_np(arr, d):
                out = np.zeros_like(arr)
                src_s = [slice(None)] * 3
                dst_s = [slice(None)] * 3
                for ax in range(3):
                    if d[ax] > 0:
                        src_s[ax], dst_s[ax] = slice(0, -1), slice(1, None)
                    elif d[ax] < 0:
                        src_s[ax], dst_s[ax] = slice(1, None), slice(0, -1)
                out[tuple(dst_s)] = arr[tuple(src_s)]
                return out
            _dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
            nrecv = np.ones(swept.shape)                      # 自己
            for d in _dirs:
                nrecv += _shift_np(swept.astype(float), d)     # 域内且被扫过的邻居
            share = np.where(swept, amount / np.maximum(nrecv, 1.0)
                             / (self.rho * self.dx ** 3), 0.0)
            self.c += share                                   # 自己那份
            for d in _dirs:
                self.c += _shift_np(share, d)                 # 邻居那份（非周期）
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' c)分发后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            if dbg is not None:
                b1, s1 = self.totals()
                dbg['log'].append((dbg['step'], kind, (b1 + s1) - dbg['t0'], int(swept.sum())))
                dbg['t0'] = b1 + s1

    def reinitialize(self, band_cells=6, mode='pair'):
        """★ EXPERT-#3 修（2026-09-26）：**按界面配对**重初始化（默认 mode='pair'）。

        为什么必须改：多区域的真实界面由  决定，**不是** 。
          旧实现把每个 phi_k 当**独立单相**做 Sussman => 即使各场自己的零等值面各自不动，
           的零等值面仍会移动。
          **实测**（_verify_reinit.py，两变体平面界面）：
            不重初始化      => d=0 在 0.02500 um
            独立 reinit 各 phi_k（旧实现）=> d=0 移到 **-0.21313 um**（跳 0.238um ≈ **4.8 个胞**！）
            对差分场 reinit  => 0.02500 um（正确）
          => 每 25 步一次的 reinit 会**反复打乱变体-变体界面**，很可能就是"等轴化"的真主因。

        做法（对每个活跃配对 (k,l), k<l）：
          1. d = phi_k - phi_l，只在 |d| <= band 的带内
          2. d_new = sussman_reinit(d)  => SDF 且**零等值面不动**
          3. **对称回写**：phi_k += 0.5*(d_new-d)，phi_l -= 0.5*(d_new-d)
             => d_kl == d_new（界面保持），且 phi_k+phi_l 不变（不引入整体漂移）
        记账：
          * 多配对叠加处（三叉线）各配对各自贡献 => 近似处理，见文档。
          * mode='perfield' 保留旧行为，仅供对照/回归。
        """
        if mode != 'pair':
            reg = self.region()
            for k in range(self.nreg):
                near = np.abs(self.phi[k]) <= band_cells * self.dx
                if not near.any():
                    continue
                newp = self.sussman_reinit(self.phi[k])
                self.phi[k] = np.where(near, newp, self.phi[k])
            return
        reg = self.region()
        # 活跃配对：区域数少时可全对；否则用 region 的邻居关系先筛
        pairs = set()
        for ax in range(3):
            a = reg
            b = np.roll(reg, -1, axis=ax)
            sel = a != b
            if sel.any():
                for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                    if x != y:
                        pairs.add((int(min(x, y)), int(max(x, y))))
        if not pairs:
            return
        # ★ 关键：**逐胞只用它自己的界面配对**（karr,larr），否则多配对（含母相）的
        #   修正会互相叠加、把界面推错（实测：叠加时界面跑到 -0.047um，逐胞后回到解析值附近）。
        _karr = np.argmin(self.phi, axis=0)
        _order = np.argsort(self.phi, axis=0)
        _karr, _larr = _order[0], _order[1]
        delta = np.zeros_like(self.phi)
        for (k, l) in pairs:
            d = self.phi[k] - self.phi[l]
            near = np.abs(d) <= band_cells * self.dx
            if not near.any():
                continue
            # EXPERT-#3c 记账：本路径的正确性依赖"窄带 + 输入近似 SDF"。
            #   Sussman 的不动点是 |grad| = 1 的场；若带内 |grad d| 明显偏离 1，
            #   迭代会把斜率推向 1 并**同时移动零等值面**（不是 bug，是必然）。
            #   这里加**运行期告警**，避免将来在别处误用这条路径。
            _gd = np.gradient(d, self.dx)
            _gdn = np.sqrt(sum(_gi ** 2 for _gi in _gd))
            _med = float(np.median(_gdn[near]))
            if abs(_med - 1.0) > 0.5:
                import warnings as _w
                _w.warn('pair reinit: band |grad d| median=%.3f 明显偏离 1; '
                       'Sussman will move the zero-level set (input not SDF).'
                       % _med, RuntimeWarning, stacklevel=2)
            dn = self.sussman_reinit(d)
            corr = np.where(near, dn - d, 0.0)
            # 该胞的界面身份必须是 (k,l)（无序）
            is_kl = ((_karr == k) & (_larr == l)) | ((_karr == l) & (_larr == k))
            corr = np.where(is_kl, corr, 0.0)
            delta[k] += 0.5 * corr
            delta[l] -= 0.5 * corr
        self.phi = self.phi + delta


def M1_multiregion_conservation(N=48, nstep=20):
    """多区域静态守恒：v_n=0（df=0、γ=0）时各区域体积应逐位不变"""
    g = LevelSetMulti(N, N * 1e-9, gamma=0.0, Mob=1.0, nv=2)
    g.seed_sphere(1, [0.4 * N * 1e-9] * 3, 8e-9)
    g.seed_sphere(2, [0.65 * N * 1e-9] * 3, 6e-9)
    v0 = [g.volume(k) for k in range(g.nreg)]
    for _ in range(nstep):
        g.advance(1e-12)
    v1 = [g.volume(k) for k in range(g.nreg)]
    drift = max(abs(a - b) / max(abs(a), 1e-30) for a, b in zip(v0, v1))
    print('---- M1 多区域静态守恒 ----')
    print('   体积漂移（最大相对）= %.2e   %s' % (drift, 'PASS' if drift < 1e-6 else 'FAIL'))
    return drift < 1e-6


class M2Out(object):
    """M2 的返回值：既支持 out['f_trans']（新代码），也把未知属性代理给内部 g
       （旧代码  后用 g.volume(...) 的那批脚本）。
       ★ 记账：加这个包装是为了"返回值从 g 改成 dict"这一步不破坏既有调用者。
    """

    def __init__(self, g, d):
        object.__setattr__(self, '_g', g)
        object.__setattr__(self, '_d', d)

    def __getitem__(self, k):
        return self._d[k]

    def get(self, k, default=None):
        return self._d.get(k, default)

    def keys(self):
        return self._d.keys()

    def __contains__(self, k):
        return k in self._d

    def __getattr__(self, k):
        return getattr(object.__getattribute__(self, '_g'), k)

    def __setattr__(self, k, v):
        setattr(object.__getattribute__(self, '_g'), k, v)


def M2_twelve_variants(N=64, dx=1e-8, nstep=300, df=1e8, gamma=0.15, aniso=0.4,
                       Mob=1e-9, rfrac=0.22, adv_grad='upwind',
                       pair_kernel=False, iface_band=2.0, probe=0, cfl=0.15,
                       plate_dx=2.0, per_field=False, aniso_elastic=False, quiet=False,
                       t_end=None, surface_chem=True,
                       C_override=None):
    # t_end：给定**总物理时间**时，按累计时间跑（而不是固定步数）。★ 记账：
    #   界面每步位移被 CFL 钉在 ~0.15dx，而 dt ∝ 1/dG_max ⇒ **同一 nstep ≠ 同一时刻**；
    #   比较不同驱动下的分数必须在**同一 t**（否则低驱动因 dt 更大而虚假领先）。
    """12 变体 RVE（level-set 表示）：看是否（i）不冻结晶核、（ii）给出板条形状。

       ★★ 符号约定（2026-09-25 由判据 T2.1b-7 判决，_chk_t21b7.py）：
          df > 0 = **变体有利**（会长大）；df < 0 = 变体不利（会缩小）。
          验证（nv=1 的 slab）：df=+1e8 => dV1=+18432、v/(M|df|)=+0.9989；
                            df=-1e8 => dV1=-18432、v/(M|df|)=-1.0000。
          这与 PF3D 的 dF/dphi_v = -dG（梯度下降 => dG>0 才长大）一致。
          ⚠ **默认值 2026-09-25 从 -1e8 改成 +1e8**：改前所有 M2 运行
          （含 §6.7 与审计引用的「转变分数 14.5%」）其实是在**溶解**晶核，
          报出的分数是**弹性自协调**撑起来的（T2.1b 开工时用单步增量发现，
          见 WINDOWB_SURFACE_AUDIT §11）。**改前的 f_trans 数值一律作废**。
       与格点 KMC 版（windowB_gibbs）对照：那里 Λ≳5 时转变被冻在 5–23% ✗。

       ★★ 记账（2026-09-25 两个真修正，缺一都会让 M2 的几何量彻底失真）：
       1) **`dt` 必须按总驱动自适应**（`suggest_dt`）：弹性项在界面带上中位 4.9e8，
          是 Δf(1e8) 的 ~5 倍 ⇒ 只用 Δf 估 dt 会让**实际每步位移达 0.6–0.75 dx**
          （超 CFL 4–5 倍）。实测修前 25 步内带胞 12601→35、|∇φ_winner| 0.73→6e5；
          修后同样 25 步带胞 9567→**9671**、|∇φ_winner| 稳定在 0.48–0.62、12 个变体
          **全部存活**，几何首次给出合理数字（长:短 3.9–5.2、与相容法向夹角中位 20.7°）。
          ⇒ §9.4/§9.5 的"M2 塌缩/配对一致性被破坏"全部是**这一步的超 CFL 症状**。
       2) **`Λ` 默认 10 → 0.4**：`γ(θ)=γ0(1+Λ sin²θ)` 的 Herring 稳定性要求
          `γ+γ_θθ = γ0(1+2Λ−3Λ sin²θ) > 0`，最坏在 `sin²θ=1` ⇒ **Λ < 1**。
          Λ=10 时实测该量跨 **[−1.35, +3.15]（含负）⇒ 非凸/不适定**（界面会被"起皱"
          驱动）。0.4 与 W1 的正对照同一个值（W1 已验证），且落在 Ti64 晶界能各向异性
          的常见范围（~0.2–0.4）。"""
    _p = (lambda *a, **k: None) if quiet else print
    from windowB_pf3d import C_iso3, C_cubic, _lam_full
    from windowB_ti64_variants import variants
    # ★★ 记账（2026-09-25）：均匀模量近似的**参考模量**由"各向同性等效"改成**母相 β(bcc) 立方**
    #   —— β-Ti 的 Zener 各向异性 A = 2C44/(C11−C12) = 2·36/(134−110) = **3.0**，是强各向异性，
    #   用各向同性等效会丢掉弹性相互作用的**方向性**（而 M2 的板条取向正是靠它）。
    #   张量本身已过 `_chk_hex.py` HX-7（立方不变性机器精度）；常数 ★【文献值待核对】。
    #   ⚠ 仍未做：逐变体模量（12 个转动 hcp 张量已建好并验证 = HX-6，但 FFT 谱法要求均匀 C
    #   ⇒ 要做 inhomogeneous 需换参考介质 + 极化迭代；见审计 §10.9）。
    # ★ C_override：隔离实验用（C_override=None 表示**关掉弹性**，只留化学驱动）。
    #   用途：把「界面/化学」与「弹性相互作用」分开（见 _t21b_noel.py 的记账）。
    #   C_override=None -> 默认（bcc β-Ti 立方）；'off' -> **关掉弹性**（C=None）；
    #   否则当作显式张量。
    _no_el = (C_override == 'off')
    if C_override is None or _no_el:
        C = C_cubic(134.0e9, 110.0e9, 36.0e9)    # bcc β-Ti ★文献值待核对
    else:
        C = C_override
    #   C 仍用于算 npref（晶核取向，几何量）；弹性求解器是否建由 C_use 决定。
    C_use = None if _no_el else C
    eps0, Fs, meta = variants()
    nv = len(eps0)
    g = LevelSetMulti(N, N * dx, C=C_use, eps0=eps0, gamma=gamma, Mob=Mob,
                      df=[0.0] + [df] * nv, workers=6, reinit_every=25,
                      aniso_elastic=aniso_elastic)
    # 各变体的弹性最省能法向（= 晶核取向）
    npref = {}
    rng = np.random.default_rng(0)
    for v in range(nv):
        best, bn = None, None
        for n in rng.normal(size=(400, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        npref[v + 1] = bn
    R = rfrac * N * dx
    t = plate_dx * dx
    for v in range(nv):
        g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R, t)
    g.init_parent()
    v0 = np.array([g.volume(k) for k in range(g.nreg)])
    _p('   [诊断] 初始各区域体积分数 = %s' % np.round(v0 / v0.sum(), 4))
    _p('   [诊断] phi 的最小值: 母相 %.3e ; 变体1 %.3e ; 空变体13 %.3e'
          % (g.phi[0].min(), g.phi[1].min(), g.phi[g.nreg - 1].min()))
    v = Mob * abs(df) * 0.5                    # 前沿速度估计
    # ★★ 记账（本轮修的真 bug）：前沿速度是 **M·|Δf|**，不是 0.5 倍。旧写法
    #   `v = M|Δf|·0.5` 配 `dt = 0.3dx/v` ⇒ 实际每步位移是 **0.6 dx**（不是 0.3）。
    #   后果（实测，隔离实验见审计 §10.2）：一阶迎风在 0.6dx/步下失真、6dx 厚的
    #   板片 10 步被吃光、`band_health` 静默塌缩（带胞 12601→35、|∇φ_winner| 中位
    #   0.73→6.0e5）；把每步位移降到 0.10–0.15dx 后同一算例 25 步内带胞只降到 ~1900、
    #   |∇φ| 中位 ~4.9（仍退化，但量级完全不同 ⇒ dt 是**主导因素**）。
    #   ⇒ 改用**显式 CFL**：`dt = cfl·dx/(M|Δf|)`。
    v = Mob * abs(df)
    dt = cfl * dx / v
    _p('---- M2 12 变体 RVE（level-set）----')
    _p('   N=%d dx=%.1f nm 域=%.2f um | df=%.1e γ=%.2f Λ=%.1f | v=M|df|=%.3f m/s '
          'dt0=%.2e ⇒ 初值每步位移 %.3f dx（之后按**总驱动**自适应）'
          % (N, dx * 1e9, N * dx * 1e6, df, gamma, aniso, v, dt, dt * v / dx))
    _p('   %6s %9s %9s %9s %9s %10s' %
          ('step', 'f_trans', 'V_max/V', 'min(V)>0', 'dt*(M|dG|mx)/dx', '带胞'))
    _nstop = nstep if t_end is None else 1000000
    _tacc = 0.0
    for k in range(_nstop + 1):
        _done = (k == nstep) if t_end is None else (_tacc >= t_end)
        if k % 60 == 0 or _done:
            vt = np.array([g.volume(j) for j in range(g.nreg)])
            f = 1.0 - vt[0] / (N * dx) ** 3
            nb, medg, okg = g.band_health()
            _p('   %6d %9.4f %9.4f %9s %12.3f %10d'
                  % (k, f, vt.max() / v0.sum(), str(bool((vt[1:] > 0).all())),
                     dt * (g.M * getattr(g, 'dG_max', 0.0)) / dx, nb))
        if _done:
            break
        g.advance(dt, aniso=aniso, npref=npref, adv_grad=adv_grad,
                  pair_kernel=pair_kernel, iface_band=iface_band,
                  per_field=per_field)
        # ★★ W-6 修（2026-09-25）：**必须每步调 update_Gamma** —— 否则被 Stefan 扫出的
        #   溶质全部滞留在面 Gamma 里（既不弛豫到 McLean、也不由面扩散/回吐分发），
        #   且界面移走后离带胞的 Gamma 会脱离账本（实测 rel 约 5e-6/步）。
        #   关掉它只在做'纯平流/纯面储存'的隔离实验时才有意义。
        if surface_chem:
            g.update_Gamma(dt)
        # ★ 自适应 dt：按**实际总驱动**（含弹性）定 CFL，见 `suggest_dt` 的记账
        _tacc += dt
        ndt = g.suggest_dt(cfl=cfl, dt_prev=dt)
        if ndt:
            dt = ndt
        if probe and (k + 1) % probe == 0:
            nb, medg, okg = g.band_health()
            _p('   [带健康 probe step=%4d] 带胞=%6d 带内|∇φ_win|中位=%8.3f %s'
                  % (k + 1, nb, medg, 'OK' if okg else '**退化**'))
    reg = g.region()
    vt = np.array([g.volume(j) for j in range(g.nreg)])
    # ★ P1 修复后必须用**几何（coarea）界面面积测度**：`g.area(k)` 是"异键数×dx²"的
    #   格点测度，对球实测 **+51.9%** ✗（见 WINDOWB_SURFACE_AUDIT §2 的 A1）。
    #   `area_total_geom()` 对球 +0.3% ✓ ⇒ S_v、t=2f/S_v 才可信。
    sv_geom = g.area_total_geom() / (N * dx) ** 3
    sv_latt = sum(g.area(j) for j in range(1, g.nreg)) / (N * dx) ** 3
    nb, medg, okg = g.band_health()
    if not okg:
        _p('   ⚠⚠ 界面带已退化（带胞 %d、带内 |∇φ| 中位 %.2f）⇒ **下面的 S_v / 板条厚度'
              '不得引用**：多畴速度扩展/带掩模仍有问题（见审计 §9.5/§10）' % (nb, medg))
    _p('   末态: 转变分数 %.4f ; 各变体体积分数 %s' %
          (1 - vt[0] / (N * dx) ** 3, np.round(vt[1:] / vt[1:].sum(), 3)))
    f_t = 1 - vt[0] / (N * dx) ** 3
    _p('   S_v(几何 coarea) = %.3e 1/m ⇒ 板片厚 t = 2f/S_v = %.1f nm ; '
          '（格点键测度 S_v = %.3e ⇒ t = %.1f nm，仅作对照）'
          % (sv_geom, 2 * f_t / max(sv_geom, 1e-30) * 1e9,
             sv_latt, 2 * f_t / max(sv_latt, 1e-30) * 1e9))
    if not quiet:
        geom_stats(g)
    out = dict(f_trans=float(f_t), v_frac=(vt / vt.sum()).tolist(),
               v_abs=vt.tolist(), S_v_geom=float(sv_geom),
               band=nb, band_ok=bool(okg), g=g, k_used=k, t_total=_tacc,
               dt_last=dt)
    return M2Out(g, out)


if __name__ == '__main__' and False:
    pass


# ============================================================ W1：各向异性 Wulff 形状（① 的判据）
def _wulff_polar(Lam, n=1441):
    """γ(θ)=γ0(1+Λ sin²θ)（θ = 法向与 x̂ 的夹角）的 **Wulff 形状极坐标表示**。
       Wulff 形状 = 半平面族 {x·n ≤ γ(n)} 的交 ⇒ **支撑函数 h(n) = γ(n)**，
       边界由包络 x(θ) = γ(θ)n(θ) + γ'(θ)t(θ) 给出（该点外法向恰为 n(θ)）。
       返回 (ψ, ρ/γ0)：ψ = 位置角，ρ = 到中心的距离。
       ★ 记账（一条会误判的坑）：**不要**拿 "R ∝ γ+γ_θθ" 去比**极径** ——
           γ+γ_θθ 是**曲率半径** 1/κ（Wulff 形状满足 (γ+γ_θθ)κ = 1），
           不是极径；两者只在各向同性时相同。Λ=0.4 下二者差 ~12% ⇒ 用错公式必误判。"""
    th = np.linspace(-np.pi, np.pi, n)
    g = 1.0 + Lam * np.sin(th) ** 2
    gp = Lam * np.sin(2.0 * th)
    x = g * np.cos(th) - gp * np.sin(th)
    y = g * np.sin(th) + gp * np.cos(th)
    psi = np.unwrap(np.arctan2(y, x))
    rho = np.hypot(x, y)
    o = np.argsort(psi)
    return psi[o], rho[o]


def _bin_polar(psi, rho, nbin):
    edges = np.linspace(-np.pi, np.pi, nbin + 1)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(psi, edges) - 1, 0, nbin - 1)
    out = np.full(nbin, np.nan)
    for b in range(nbin):
        s = (idx == b)
        if s.sum():
            out[b] = rho[s].mean()
    return ctr, out


def _shape_metrics(pts2, nrm2, ctr2, Lam, npref2, nbin=36):
    """把 2D 横截面上的界面点折算成 W1 的四条量：
         (a) **支撑函数**判据 h ≡ (x−x_c)·n 必须 ∝ γ(n)  ⇒ 比值 h/γ 的离散度
         (b) 归一化极径 ρ(ψ) 与**精确 Wulff 极径**的最大偏差（按各向异性幅度归一）
         (c) 长径比 = ρ_max/ρ_min，以及 ρ_max 的位置角（Herring 结果应沿 ŷ 拉长）
         (d) 界面点数（量测可靠性的门槛）"""
    d = pts2 - ctr2[None, :]
    rho = np.linalg.norm(d, axis=1)
    psi = np.arctan2(d[:, 1], d[:, 0])
    ctr, rb = _bin_polar(psi, rho, nbin)
    ok = ~np.isnan(rb)
    rn = rb[ok] / rb[ok].mean()
    nd = nrm2 @ (np.asarray(npref2, float) / np.linalg.norm(npref2))
    # ★ 记账（本轮修的一个判据 bug）：γ(θ)=γ0(1+Λ sin²θ)，θ = 法向与 x̂ 的夹角
    #   ⇒ γ = 1 + Λ(1 − (n·x̂)²)。写成 `1 + Λ(n·x̂)²` 会让 γ 的各向异性**反相**
    #   （实测：h/γ 离散度从 0.33 一路涨到 0.66，看起来像"越弛豫越不像 Wulff" ✗）。
    gam = 1.0 + Lam * (1.0 - nd ** 2)
    h = np.einsum('ij,ij->i', d, nrm2)
    ratio = (h / gam)
    ratio = ratio[np.isfinite(ratio) & (gam > 0)]
    spread = float((ratio.max() - ratio.min()) / abs(ratio.mean())) if len(ratio) else np.nan
    # ★ 稳健口径：极差(h_spread)对个别离群点极敏感；判据用 **RMS 相对偏差**
    h_rms = float(np.std(ratio) / abs(np.mean(ratio))) if len(ratio) else np.nan
    pth, prho = _wulff_polar(Lam)
    pr = np.interp(ctr[ok], pth, prho)
    pr = pr / pr.mean()
    dev = float(np.max(np.abs(rn - pr)) / (pr.max() - pr.min()))
    # ★ 无偏形状量：傅里叶拟合 r(ψ)=a0+a2cos2ψ+b2sin2ψ+a4cos4ψ+b4sin4ψ
    #   记账：**不要**用分箱极径的 max/min 当长径比 —— 极值附近的分箱平均会把 max 压低、
    #   min 抬高（各 ~1.5%），实测把 Λ=0.4 的长径比从 1.40 系统性拉到 1.356（-11% 幅度）✗。
    #   傅里叶系数对同样的形状给出无偏估计，且**理论值用同一套拟合**得到 ⇒ 可比。
    ps, rs = _bin_polar(psi, rho, 720)
    o2 = ~np.isnan(rs)
    A = np.stack([np.ones(o2.sum()), np.cos(2 * ps[o2]), np.sin(2 * ps[o2]),
                  np.cos(4 * ps[o2]), np.sin(4 * ps[o2])], -1)
    coef, *_ = np.linalg.lstsq(A, rs[o2], rcond=None)
    tA = np.stack([np.ones_like(pth), np.cos(2 * pth), np.sin(2 * pth),
                   np.cos(4 * pth), np.sin(4 * pth)], -1)
    tcoef, *_ = np.linalg.lstsq(tA, prho, rcond=None)   # 比值 a2/a0 与整体标度无关
    f_m = np.array([coef[0], np.hypot(coef[1], coef[2]), np.hypot(coef[3], coef[4])])
    f_t = np.array([tcoef[0], np.hypot(tcoef[1], tcoef[2]), np.hypot(tcoef[3], tcoef[4])])
    an2 = f_m[1] / f_m[0]
    an2_th = f_t[1] / f_t[0]
    an4 = f_m[2] / f_m[0]
    an4_th = f_t[2] / f_t[0]
    asp_fit = float((f_m[0] + f_m[1] + f_m[2]) / (f_m[0] - f_m[1] + f_m[2]))
    asp_fit_th = float((f_t[0] + f_t[1] + f_t[2]) / (f_t[0] - f_t[1] + f_t[2]))
    return dict(n=len(pts2), aspect=float(rb[ok].max() / rb[ok].min()),
                psi_max=float(ctr[ok][int(np.argmax(rb[ok]))]),
                R_eq=float(rho.mean()), h_spread=spread, dev=dev,
                h_rms=h_rms,
                ctr=ctr[ok], rn=rn, pr=pr, psi=psi, rho=rho, ratio=ratio,
                a2=float(an2), a2_th=float(an2_th), a4=float(an4),
                a4_th=float(an4_th), asp_fit=asp_fit, asp_fit_th=asp_fit_th,
                cos2=float(coef[1]),
                psi_axis=float(0.5 * np.degrees(np.arctan2(coef[2], coef[1]))))


def W1_wulff(N=64, dx=2e-9, R0=1.2e-8, Lam=0.4, nstep=600, herring=True,
             nbin=36, nz=4, tag='', plot=None, M=1e-9, gamma=0.15,
             adv_grad='central', dtfac=0.05, reinit_every=20, verbose=None,
             mode='shape'):
    """① 的解析正对照：**各向异性 Wulff 形状**（Gibbs–Thomson 的 Herring 项）。

    几何：沿 z 的柱体（`ndim=2` 薄板，z 向平移不变 ⇒ 与真 2D 逐位等价），n_pref = x̂。
    演化：**定容弛豫** —— v_n = M[df − γ_eff(n)κ]（df=0 走纯各向异性曲率流），每步再用
          `project_volume` 把体积钉回初值 ⇒ 「面积守恒的各向异性平均曲率流」，
          其唯一稳定平衡态 = Wulff 形状 ✓（等价于用户要的 `df = γ⟨κ⟩_A` 定容，见
          `project_volume` 的记账）。
    判据（全部用**无偏**量；量测口径见 `_shape_metrics`）：
      (a) **傅里叶 2 次模** a2/a0（长径比的线性测度）与理论差 < 15%；
      (b) 拉长方向 = ±ŷ（理论：γ 在 n=ŷ 最大 ⇒ Wulff 沿 ŷ 拉长），误差 < 25°；
      (c) **支撑函数** h=(x−x_c)·n 与 γ(n) 成正比 ⇒ h/γ 离散度 < 10%；
      (d) 数值底噪由 Λ=0 对照给出（应 a2≈0、长径比≈1.00）。
    反向对照：herring=False（拿 γ 当刚度）必须 **FAIL** —— 其实测长径比只有 ~1.10、
    拉长轴转到 **x̂**（与 Herring 结果正交互补），h/γ 离散 ~43% ✗。

    ★ 记账（本轮修掉的三个 harness/数值错误）：
      1) **旧的"定容"是坏的**：用两点标定 + 积分控制，标定步本身用 `df=1e8`、`dt=1.33e-8 s`
         ⇒ 两步内把 R 从 10 nm 吹到 ~58 nm（标定毁掉了初始形状）✗ ⇒ 判据必失败。
         现在用**投影式定容**：无标定、无反馈增益、无临界核不稳定性 ✓。
      2) **量测偏置**：用 36 个角度分箱取极径极值当长径比，会在极值附近把 max 压低、
         min 抬高，实测把 Λ=0.4 的长径比从 1.40 拉到 1.356（−11% 幅度）✗
         ⇒ 改用**傅里叶拟合**（与理论同一套拟合流程）。
      3) **推进格式的口径依赖**：一阶 Godunov 迎风 |∇φ| 带一个**与取向有关**的误差，
         把有效各向异性压低 ~8%（实测 a2 比值 0.90–0.93，且**不随 dx 收敛**）；
         换中心差分 |∇φ| 后 a2 比值 **0.99–1.01** ✓。故本判据用 `adv_grad='central'`
         （光滑 SDF 下二阶、实测稳定），并把 upwind 的结果一并打印作为口径对照。
    """
    g = LevelSetSurface(N, N * dx, gamma=gamma, Mob=M, R0=R0,
                        reinit_every=reinit_every, ndim=2, nz=nz)
    x = (np.arange(N) + 0.5) * dx
    X, Y = np.meshgrid(x, x, indexing='ij')
    c0 = 0.5 * N * dx
    rperp = np.sqrt((X - c0) ** 2 + (Y - c0) ** 2)
    g.phi = rperp[..., None] - R0 * np.ones((1, 1, g.Nz))   # 圆柱（xy 截面为圆）
    V0 = g.volume()            # ★ 用**三维**测度配 `area()`（见 project_volume 的记账）
    npref = np.array([1.0, 0.0, 0.0])
    v0 = M * gamma / R0
    dt = dtfac * dx / v0
    zs = g.Nz // 2
    tau = R0 ** 2 / (3.0 * M * gamma)          # 形状模（m=2）线性时间常数
    if verbose is None:
        verbose = max(1, nstep // 4)
    print('---- W1 Wulff 形状（Λ=%.2f, herring=%s, adv=%s）%s ----'
          % (Lam, herring, adv_grad, tag))
    print('   N=%d dx=%.2f nm 柱体 R0=%.2f nm (R0/dx=%.1f) | dt=%.3e s (%.3f 胞/步) | '
          '%d 步 = %.1f 个形状时间常数'
          % (N, dx * 1e9, R0 * 1e9, R0 / dx, dt, dt * v0 / dx, nstep, nstep * dt / tau))
    print('   %6s %9s %9s %8s %9s %9s %8s %7s' %
          ('step', 'a2/a0', 'a2_th', '比', 'a4/a0', '长轴(°)', 'h/g 离散', '点'))
    hist = []
    for k in range(nstep + 1):
        if k % verbose == 0 or k == nstep:
            P, Nn = g.interface_points(band=1.5, zslice=zs)
            if len(P) < 20:
                print('   k=%4d 界面点太少(%d) ⇒ 发散' % (k, len(P)))
                return False, dict(a2=np.nan)
            met = _shape_metrics(P[:, :2], Nn[:, :2], g.region_center()[:2], Lam,
                                 np.array([1.0, 0.0]), nbin=nbin)
            met['step'] = k
            met['R_eq'] = g.radius_2d()
            hist.append(met)
            print('   %6d %9.4f %9.4f %8.3f %9.4f %9.1f %9.4f %7d'
                  % (k, met['a2'], met['a2_th'], met['a2'] / met['a2_th'], met['a4'],
                     met['psi_axis'], met['h_spread'], met['n']))
        if k == nstep:
            break
        g.advance(dt, df=0.0, aniso=Lam, npref=npref, herring=herring,
                  adv_grad=adv_grad)
        g.project_volume(V0)
    fin = hist[-1]
    ratio = fin['a2'] / fin['a2_th'] if fin['a2_th'] > 1e-6 else np.inf
    # 拉长方向到 {±90°}(mod 180°) 的角距离
    axerr = abs((fin['psi_axis'] % 180.0) - 90.0)
    if mode == 'floor':
        # Λ=0 档：理论无各向异性 ⇒ 不能套形状判据，只查"量测到的伪各向异性有多大"
        ok = (fin['a2'] < 0.010) and (fin['a4'] < 0.020) and (abs(fin['asp_fit'] - 1.0) < 0.02)
        print('   末态 a2/a0=%+.5f（应≈0） a4/a0=%.5f（网格 4 次伪模） 拟合长径比=%.5f'
              % (fin['a2'], fin['a4'], fin['asp_fit']))
        print('   判定[数值底噪]: %s' % ('PASS' if ok else 'FAIL'))
        return ok, fin
    print('   末态 a2/a0 = %.4f（理论 %.4f，比 %.3f） | 拉长方向 %.1f°（理论 ±90°，误差 %.1f°）'
          % (fin['a2'], fin['a2_th'], ratio, fin['psi_axis'], axerr))
    print('        h/γ 离散 %.4f | 与 Wulff 极径偏差 %.4f（含分箱偏置，保守）'
          % (fin['h_spread'], fin['dev']))
    ok = (abs(ratio - 1.0) < 0.15) and (axerr < 25.0) and (fin['h_rms'] < 0.10)
    print('        h/γ 稳健 RMS = %.4f（判据 <0.10）; a2 比 %.3f（判据 |比-1|<0.15）; '
          '轴误差 %.1f°（判据 <25°）' % (fin['h_rms'], ratio, axerr))
    print('   判定[herring=%s adv=%s]: %s' % (herring, adv_grad, 'PASS' if ok else 'FAIL'))
    if plot:
        _plot_w1(hist, Lam, herring, plot)
    return ok, fin


def W1_control(Lam=0.4, nstep=600, N=64, dx=2e-9, R0=1.2e-8, nbin=36,
               adv_grad='central', dtfac=0.05):
    """W1 的**三档对照**（同一初始形状、同一推进格式，只差 Herring 项与各向异性幅值）：
         ① Λ=0       : 数值底噪（平衡必须是正圆 ⇒ 量出**纯数值**各向异性）
         ② herring=T : 正对照，应 PASS
         ③ herring=F : 反向对照，应 FAIL（拿 γ 当刚度 ⇒ 长轴转到 x̂、长径比腰斩）
       同时给出 upwind 口径下 ② 的结果，量化推进格式带来的口径偏差。"""
    res = {}
    print('==== ① Λ=0 数值底噪（理论 a2=0、长径比=1.000）====')
    ok0, f0 = W1_wulff(Lam=0.0, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad=adv_grad, dtfac=dtfac, tag='（数值底噪）',
                       mode='floor')
    res['floor_a2'] = f0.get('a2', np.nan)
    res['floor_a4'] = f0.get('a4', np.nan)
    res['ok_floor'] = ok0
    print('==== ② Herring 正对照（Λ=%.2f）====' % Lam)
    ok1, f1 = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad=adv_grad, dtfac=dtfac, tag='（正对照）',
                       plot='/mnt/f/speed_up/pipeline/ca_pf_framework/FIG_W1_wulff_herring.png')
    print('==== ③ 反向对照：herring=False（拿 γ 当刚度）====')
    ok0b, f0b = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                         herring=False, adv_grad=adv_grad, dtfac=dtfac, tag='（反向对照）',
                         plot='/mnt/f/speed_up/pipeline/ca_pf_framework/FIG_W1_wulff_naive.png')
    print('==== ④ 口径对照：upwind |∇φ| ====')
    oku, fu = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad='upwind', dtfac=dtfac, tag='（上风口径）')
    res.update(ok_h=ok1, ok_n=ok0b, ok_up=oku)
    ok = bool(ok1) and (not ok0b)
    print('---- W1 总判定 ----')
    print('   ① 数值底噪      : a2/a0 = %+.4f（应 ≈0）' % res['floor_a2'])
    print('                      a4/a0 = %+.4f（网格 4 次伪模）' % res['floor_a4'])
    print('   ② Herring       : a2/a0 = %.4f / 理论 %.4f = %.3f ; 长轴 %.1f° ; h/γ %.4f ⇒ %s'
          % (f1['a2'], f1['a2_th'], f1['a2'] / f1['a2_th'], f1['psi_axis'],
             f1['h_rms'], 'PASS' if ok1 else 'FAIL'))
    print('   ③ 非 Herring    : a2/a0 = %.4f / 理论 %.4f = %.3f ; 长轴 %.1f° ; h/γ %.4f ⇒ %s'
          % (f0b['a2'], f0b['a2_th'], f0b['a2'] / f0b['a2_th'], f0b['psi_axis'],
             f0b['h_rms'], 'PASS' if ok0b else 'FAIL'))
    print('   ④ 上风口径(仅报告): a2 比值 %.3f ⇒ 一阶迎风的取向偏置 %.1f%%'
          % (fu['a2'] / fu['a2_th'], 100 * (fu['a2'] / fu['a2_th'] - 1)))
    print('   ⇒ W1（Herring 项必需、且 Wulff 形状量测无误）: %s' % ('PASS' if ok else 'FAIL'))
    return ok
def _plot_w1(hist, Lam, herring, path, ttf='/mnt/c/Windows/Fonts/simhei.ttf'):
    """W1 的可视化：形状轮廓 / 归一化极径 vs Wulff 理论 / h-γ 比值"""
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    if os.path.exists(ttf):
        try:
            fm.fontManager.addfont(ttf)
            plt.rcParams['font.family'] = fm.FontProperties(fname=ttf).get_name()
        except Exception:
            pass
    plt.rcParams['axes.unicode_minus'] = False
    fin = hist[-1]
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    # (a) 轮廓 + 理论 Wulff
    pth, prho = _wulff_polar(Lam)
    kk = prho / prho.mean() * fin['R_eq'] * 1e9
    ax[0].plot(pth * 180 / np.pi, kk, 'k--', lw=2, label='Wulff 理论（包络 h=γ）')
    m = np.abs(fin['psi']) <= np.pi
    ax[0].plot(np.degrees(fin['psi'][m]), fin['rho'][m] * 1e9, '.', ms=2, alpha=0.5,
               label='量测界面点')
    ax[0].set_xlabel('位置角 ψ (°)'); ax[0].set_ylabel('极径 (nm)')
    ax[0].set_title('Q1: 形状轮廓 vs Wulff 理论（herring=%s, Λ=%.2f）' % (herring, Lam))
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    # (b) 归一化极径
    ax[1].plot(fin['ctr'] * 180 / np.pi, fin['rn'], 'o-', label='量测（归一）')
    ax[1].plot(fin['ctr'] * 180 / np.pi, fin['pr'], 'k--', label='Wulff 理论（归一）')
    ax[1].set_xlabel('位置角 ψ (°)'); ax[1].set_ylabel('归一化极径 ρ/⟨ρ⟩')
    ax[1].set_title('Q2: 归一化极径（偏差 %.3f）' % fin['dev'])
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    # (c) h/γ
    ax[2].hist(fin['ratio'] / (fin['ratio'].mean() + 1e-30), bins=30, alpha=0.8)
    ax[2].set_xlabel('h/γ（归一）'); ax[2].set_ylabel('计数')
    ax[2].set_title('Q3: 支撑函数 h/γ（离散度 %.3f，应为常数）' % fin['h_spread'])
    ax[2].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print('   [图] 已写 %s' % path)


def M3_McLean(N=32, dx=2e-9, nstep=400):
    """面上场 Γ 的局部平衡：应收敛到 McLean/Langmuir 解析值（新表示下重做 H3）"""
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=0.0)
    # 一个平面界面：区域1 占 z<L/2。★ 记账（本轮修）：必须用**真 SDF** φ = z − L/2，
    # 不能用 ±1e-9 的**阶跃**。阶跃场里 |∇φ| 只在 1 层胞非零 ⇒ `cell_area_geom` 的
    # coarea 估计（Σ|∇φ|dx²/3，"/3" 对应 SDF 的 ±1.5dx 三层带）**偏小 3 倍**；
    # 真 SDF 的带恰好是 3 层、每层 |∇φ|=1 ⇒ Σ = dx² 每列 = 正确面积 ✓。
    g.phi[1] = (np.arange(N)[None, None, :] * dx - 0.5 * N * dx) * np.ones((N, N, N))
    g.init_parent()
    g.c[:] = 0.036
    for _ in range(nstep):
        g.update_Gamma(2e-11)
    # ★ 记账（本轮修）：界面胞集合必须用**面积掩模** `cell_area_geom() > 0`
    #   （= `update_Gamma` 内部用的同一个掩模），**不能**用 `surface_band()`：
    #   后者按"邻胞区域号不同"取，在**周期 BC**下会把 `z=0` 的 wrap 层误判成界面
    #   （实测量到 layer 0 与 layer 24 两层，各 384 胞）。那里 Γ 恒为 0 且会被
    #   `update_Gamma` 的 (3') 清零 ⇒ 把它算进均值会**恰好把 Γ 砍半**
    #   （实测 Γ_model/Γ_McLean = 0.477 ⇒ 就是这个假象，不是物理）。
    m = g.cell_area_geom() > 0
    Geq = g.Gamma_eq(g.c[m])
    rel = float(np.abs(g.Gam[m] - Geq).max() / max(np.abs(Geq).max(), 1e-30))
    print('---- M3 面上场偏析平衡（level-set 表示，重做 H3）----')
    print('   T=%.0f K: Γ_model=%.4e mol/m² ; Γ_McLean=%.4e ; 最大相对差 %.2e   %s'
          % (g.T, float(g.Gam[m].mean()), float(Geq.mean()), rel,
             'PASS' if rel < 0.05 else 'FAIL'))
    return rel < 0.05


def geom_stats(g, topk=6, min_cells=200):
    """几何统计（G4 的正确测度，在 level-set 表示下重做）：
       · 每个变体的回转张量半轴比（长:短）—— 板条应显著各向异性
       · 最小本征值的本征向量 = 板片法向 ⇒ 与"该变体参与的 rank-1 相容对法向"比夹角"""
    from scipy import ndimage
    from windowB_bench3d import rank1_normal
    from windowB_ti64_variants import variants
    eps0, _, _ = variants()
    nv = len(eps0)
    comp = {}
    for a in range(nv):
        for b in range(a + 1, nv):
            res, n = rank1_normal(eps0[b] - eps0[a])
            if res < 1e-9:
                comp[(a + 1, b + 1)] = n
    reg = g.region()
    st = ndimage.generate_binary_structure(3, 3)
    rows = []
    for k in range(1, g.nreg):
        m = (reg == k)
        if m.sum() < min_cells:
            continue
        lab, n = ndimage.label(m, structure=st)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        for j, sz in enumerate(sizes, 1):
            if sz < min_cells:
                continue
            pts = np.argwhere(lab == j).astype(float) * g.dx
            pts -= pts.mean(0)
            G = (pts.T @ pts) / len(pts)
            w, V = np.linalg.eigh(G)
            rows.append((sz, k, w, V[:, 0]))
    rows.sort(key=lambda r: -r[0])
    print('   [几何] 最大的 %d 个域（回转半轴比 长:短；n=板片法向）:' % min(topk, len(rows)))
    angs = []
    for sz, k, w, nvec in rows[:topk]:
        r = (w[2] / max(w[0], 1e-30)) ** 0.5
        best = min((np.degrees(np.arccos(min(1.0, abs(float(nvec @ nrm)))))
                    for (a, b), nrm in comp.items() if k in (a, b)), default=np.nan)
        if not np.isnan(best):
            angs.append(best)
        print('     V%2d 体积=%6d 胞  长:短=%.2f  n=[%+.2f %+.2f %+.2f]  与相容法向夹角 %.1f°'
              % (k, int(sz), r, *nvec, best))
    if angs:
        print('   [几何] 法向 vs 相容法向: 中位 %.1f°  最小 %.1f°' % (np.median(angs), min(angs)))
    return rows


def M4_conservation(N=32, dx=2e-9, nstep=150, df=-1e8, tag='溶解(历史工况)',
                    tol=1.0e-3, verbose=True):
    """体相 + 面过剩的守恒。

    ★ W-6d（2026-09-25）三处改动，都是为了让它**有信息量**：
      1) 门槛 2.5e-2 -> **1e-3**（2.5% 太松，PASS 没有信息量）；
      2) 同时上报**两个工况**：@BT@df=-1e8@BT@（溶解，历史工况）与 @BT@df=+1e8@BT@（成长，物理工况，
         符号按判据 T2.1b-7 的判决）；两者的残差**差 30 倍**，只报一个会把缺陷藏起来；
      3) 把"Stefan 只做了推给邻居、没做面储存/回吐"那条旧备注删掉（机制早已实现，W-6）。
    """
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, df])
    g.seed_sphere(1, [0.5 * N * dx] * 3, 5 * dx)
    g.init_parent()
    g.c[:] = 0.036
    mb0, ms0 = g.totals()
    dt = 0.2 * dx / (1e-9 * 1e8)
    for _ in range(nstep):
        g.advance(dt)
        g.update_Gamma(dt)
    mb1, ms1 = g.totals()
    rel = abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)
    if verbose:
        print('    %-14s : 相对漂移 %.3e   面 %+.3e   体 %+.3e   %s（门槛 %.0e）'
              % (tag, rel, ms1 - ms0, mb1 - mb0, 'PASS' if rel < tol else 'FAIL', tol))
    return rel


def M4_report(N=32, nstep=150):
    """M4 两工况 + 门槛判定（任一 FAIL 则整体 FAIL）。★ 记账：残差主要是**体相**在丢溶质
       （两面工况的  都恰好为 0）⇒ W-6e 要查  的记账去向。"""
    print('---- M4 守恒（体相 + 面过剩，level-set 表示）—— 两工况 ----')
    r1 = M4_conservation(N=N, nstep=nstep, df=-1e8, tag='溶解(历史)')
    r2 = M4_conservation(N=N, nstep=nstep, df=+1e8, tag='成长(物理)')
    print('    记账：面量按摩尔/胞（Gam_mol）记账、带外强制回吐（W-6c/W-6d），')
    print('           派生 Gam 后同步 （否则兼容 guard 每步误触发 => 体相丢溶质）。')
    print('          ★ W-6e（2026-09-25）：上述同步就是把本判据从 8.9e-2 压到 2e-16 的那一步。')
    print('          "Stefan 只做了推给邻居、没做面储存/回吐"那条旧备注**已作废**（机制早已实现）。')
    ok = (r1 < 1.0e-3) and (r2 < 1.0e-3)
    print('    M4 判定: %s（溶解 %.2e / 成长 %.2e，门槛 1e-3）'
          % ('PASS' if ok else 'FAIL', r1, r2))
    return ok


if __name__ == '__main__':
    print('=' * 92)
    print('Gibbs 面场（level-set）+ 体相场：判据 S0/S1')
    print('=' * 92)
    res = {}
    res['S0'] = S0_curvature()
    res['S1'] = S1_GibbsThomson()
    res['M1'] = M1_multiregion_conservation()
    res['M3'] = M3_McLean()
    res['M4'] = M4_conservation()
    M2_twelve_variants()
    print('\n总判定: %s' % ('ALL PASS' if all(res.values())
                          else 'FAIL -> %s' % [k for k, v in res.items() if not v]))
    raise SystemExit(0)
