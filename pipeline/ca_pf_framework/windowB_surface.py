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
import numpy as np
from scipy import fft as sfft
from scipy.ndimage import distance_transform_edt, gaussian_filter


class LevelSetSurface(object):
    """level-set 面场（单相/单畴版；多畴身份由 label 场平流携带，下一步接）"""

    def __init__(self, N, L, gamma=0.15, Mob=1.0, kappa_omega=1.0, ic='sphere',
                 R0=None, workers=4, reinit_every=50):
        self.N, self.L = N, L
        self.dx = L / N
        self.gamma = gamma
        self.M = Mob               # 含 Ω（记账：M 已含摩尔体积）
        self.workers = workers
        self.reinit_every = reinit_every
        x = (np.arange(N) + 0.5) * self.dx
        X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
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
    def advance(self, dt, df=0.0, gamma_eff=None):
        gam = self.gamma if gamma_eff is None else gamma_eff
        kap = self.curvature()
        m = self.interface_mask()
        # ★ 符号约定（记账）：v_n = M[ Δf_bulk − Ω γ κ ]，κ 对**凸的产物**取正。
        #   ⇒ 正曲率使凸体收缩（Gibbs–Thomson）；Δf<0 表示产物相稳定 ⇒ 长大。
        vn = self.M * (df - gam * kap)
        vn_if = np.where(m, vn, 0.0)
        vn_ext = self.extend_velocity(vn_if, band_cells=4)
        _, gnorm = self.normal()
        self.phi -= dt * vn_ext * gnorm        # ∂φ/∂t + v_n|∇φ| = 0
        # ★ 重初始化不能每步做：它会用"φ<0 掩模"重建距离场 ⇒ **抹掉亚胞界面位置** ✗，
        #   使界面运动被量化到整胞（实测 R(t) 在头 100 步完全不动）。
        self._cnt = getattr(self, '_cnt', 0) + 1
        if self.reinit_every and self._cnt % self.reinit_every == 0:
            self.reinitialize()
        return vn_ext

    def reinitialize(self):
        """把 φ 重新初始化成有符号距离（到界面的距离 + 原符号），保持界面位置"""
        inside = self.phi < 0
        dist = distance_transform_edt(ininside := inside, sampling=self.dx)
        self.phi = np.where(inside, -distance_transform_edt(inside, sampling=self.dx),
                            distance_transform_edt(~inside, sampling=self.dx))


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
    """孤球收缩：d(R²)/dt 应 = -4Mγ（level-set 无台阶伪影，收敛应干净）"""
    g = LevelSetSurface(N, N * dx, gamma=gamma, Mob=M, R0=R0)
    dt = 0.02 * dx / (M * 2 * gamma / R0)
    ts, Rs = [], []
    for k in range(nstep):
        if k % 20 == 0:
            ts.append(k * dt)
            Rs.append(g.radius())
        g.advance(dt, df=0.0)
    ts, Rs = np.array(ts), np.array(Rs)
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
                 Lam=0.0, k0_mode='clamped', workers=4, reinit_every=20, nv=None):
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
            _s.path.insert(0, '/mnt/f/speed_up/pipeline/gibbs')
            from gibbs_physics import RHO_MOL
            self.rho = RHO_MOL
        except Exception:
            self.rho = 1.0129e5
        self.T = 1950.0
        self.c = np.full((N, N, N), 0.036)
        self.Gam = np.zeros((N, N, N))
        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)
        # 弹性
        self.pf = None
        if C is not None and eps0 is not None:
            from windowB_pf3d import PF3D, VOIGT, G6 as _G6
            self.pf = PF3D(N, L, C, eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                           workers=workers, k0_mode=k0_mode)
            self.e0v_eng = np.array([[eps0[v][i, j] for (i, j) in VOIGT]
                                     for v in range(self.nv)]) * _G6[None, :]
            self._G6 = _G6

    # ---------- 区域与几何 ----------
    def region(self):
        return np.argmin(self.phi, axis=0).astype(np.int8)

    def seed_sphere(self, k, center, R):
        c = np.asarray(center, float)
        r = np.linalg.norm(self.XYZ - c, axis=-1)
        self.phi[k] = np.minimum(self.phi[k], r - R)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], R - r)   # 其它区域让位

    def seed_plate(self, k, center, normal, R, t):
        """薄板晶核：法向 normal、半径 R、厚 t"""
        c = np.asarray(center, float)
        n = np.asarray(normal, float)
        n = n / np.linalg.norm(n)
        rel = self.XYZ - c
        d = rel @ n
        rperp = np.linalg.norm(rel - d[..., None] * n, axis=-1)
        sdf = np.maximum(np.abs(d) - t / 2, rperp - R)         # 圆盘 SDF（近似）
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

    def Gamma_eq(self, c):
        """Langmuir/McLean 平衡过剩（mol/m²），复用 pipeline/gibbs 的单一参数来源"""
        try:
            import sys as _s
            _s.path.insert(0, '/mnt/f/speed_up/pipeline/gibbs')
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
             (2) 沿面扩散：**通量形式**（只走界面-界面键 ⇒ 逐键对称 ⇒ 严格守恒）"""
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        m = self.surface_band()
        A_c = self.cell_area()
        Gam_eq = self.Gamma_eq(self.c)
        # ★ 稳定性保护：显式弛豫必须 dt ≤ τ_ex，否则 Γ 过冲发散（实测 M4 里 dt=4e-9 > τ=1e-9
        #   导致总量变负、涨 1e5 倍 ✗）。超出时按线性插值限幅（等价于隐式的第一步）。
        frac = min(1.0, dt / tau_ex)
        dG = np.where(m, (Gam_eq - self.Gam) * frac, 0.0)
        self.Gam = np.where(m, self.Gam + dG, 0.0)
        self.c -= dG * A_c / (self.rho * self.dx ** 3)
        flux = np.zeros_like(self.Gam)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nbm = np.roll(m, d, axis=(0, 1, 2))
            both = m & nbm
            flux += np.where(both, np.roll(self.Gam, d, axis=(0, 1, 2)) - self.Gam, 0.0)
        self.Gam = np.where(m, self.Gam + dt * D_s * flux / self.dx ** 2, 0.0)

    def totals(self):
        """总溶质（mol）：体相 Σc·ρ·dV + 面 ΣΓ·A_c"""
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        mb = float(self.c.sum()) * self.rho * self.dx ** 3
        ms = float((self.Gam * self.cell_area()).sum())
        return mb, ms

    def curvature_of(self, k):
        g = np.gradient(self.phi[k], self.dx)
        gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        n = [gi / gn for gi in g]
        return sum(np.gradient(n[i], self.dx)[i] for i in range(3))

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
    def elastic_driving(self):
        """返回 (nreg, N,N,N)：-ε⁰_k:σ（对母相为 0）"""
        reg = self.region()
        out = np.zeros((self.nreg,) + reg.shape)
        if self.pf is None:
            return out
        for v in range(self.nv):
            self.pf.phi[v] = (reg == v + 1)
        sig = self.pf.sigma_tensor()
        for v in range(self.nv):
            out[v + 1] = -np.einsum('p,p...->...', self.e0v_eng[v], sig)
        return out

    # ---------- 界面推进（PDE）----------
    def advance(self, dt, aniso=0.0, npref=None, gamma0=None):
        """aniso>0 时用近奇异各向异性 γ_k(n) = γ0[1+Λ(1−(n·n_pref)²)]（n=∇φ_k/|∇φ_k|）"""
        ed = self.elastic_driving()
        reg = self.region()
        for k in range(self.nreg):
            g = np.gradient(self.phi[k], self.dx)
            gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
            kap = self.curvature_of(k)
            gk = self.gamma if gamma0 is None else gamma0
            if aniso > 0 and npref is not None and npref.get(k) is not None:
                n = np.stack([gi / gn for gi in g], -1)
                c2 = np.clip((n @ np.asarray(npref[k], float)) ** 2, 0, 1)
                gk = gk * (1.0 + aniso * (1.0 - c2))
            vn = self.M * (self.df[k] + ed[k] - gk * kap)
            # 只在界面带内推进（|φ_k| <= 2 dx）
            band = np.abs(self.phi[k]) <= 2.0 * self.dx
            self.phi[k] -= dt * np.where(band, vn, 0.0) * gn
        self._cnt = getattr(self, '_cnt', 0) + 1
        if self.reinit_every and self._cnt % self.reinit_every == 0:
            self.reinitialize()
        return reg

    def reinitialize(self, band_cells=6):
        """把每个 φ_k 在带内重初始化成有符号距离；带外保持不变（多区域安全做法）"""
        reg = self.region()
        for k in range(self.nreg):
            m = (reg == k)
            near = np.abs(self.phi[k]) <= band_cells * self.dx
            if not m.any():
                continue
            d_in = distance_transform_edt(m, sampling=self.dx)
            d_out = distance_transform_edt(~m, sampling=self.dx)
            self.phi[k] = np.where(near, np.where(m, -d_in, d_out), self.phi[k])


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


def M2_twelve_variants(N=64, dx=1e-8, nstep=300, df=-1e8, gamma=0.15, aniso=10.0,
                       Mob=1e-9, rfrac=0.22):
    """12 变体 RVE（level-set 表示）：看是否（i）不冻结晶核、（ii）给出板条形状。
       与格点 KMC 版（windowB_gibbs）对照：那里 Λ≳5 时转变被冻在 5–23% ✗。"""
    from windowB_pf3d import C_iso3, _lam_full
    from windowB_ti64_variants import variants
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    nv = len(eps0)
    g = LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                      df=[0.0] + [df] * nv, workers=6, reinit_every=25)
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
    t = 2.0 * dx
    for v in range(nv):
        g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R, t)
    g.init_parent()
    v0 = np.array([g.volume(k) for k in range(g.nreg)])
    print('   [诊断] 初始各区域体积分数 = %s' % np.round(v0 / v0.sum(), 4))
    print('   [诊断] phi 的最小值: 母相 %.3e ; 变体1 %.3e ; 空变体13 %.3e'
          % (g.phi[0].min(), g.phi[1].min(), g.phi[g.nreg - 1].min()))
    v = Mob * abs(df) * 0.5                    # 前沿速度估计
    dt = 0.3 * dx / v
    print('---- M2 12 变体 RVE（level-set）----')
    print('   N=%d dx=%.1f nm 域=%.2f um | df=%.1e γ=%.2f Λ=%.1f | v≈%.3f m/s dt=%.2e'
          % (N, dx * 1e9, N * dx * 1e6, df, gamma, aniso, v, dt))
    print('   %6s %9s %9s %9s' % ('step', 'f_trans', 'V_max/V', 'min(V)>0'))
    for k in range(nstep + 1):
        if k % 60 == 0 or k == nstep:
            vt = np.array([g.volume(j) for j in range(g.nreg)])
            f = 1.0 - vt[0] / (N * dx) ** 3
            print('   %6d %9.4f %9.4f %9s' % (k, f, vt.max() / v0.sum(),
                                              str(bool((vt[1:] > 0).all()))))
        if k == nstep:
            break
        g.advance(dt, aniso=aniso, npref=npref)
    reg = g.region()
    vt = np.array([g.volume(j) for j in range(g.nreg)])
    sv = sum(g.area(j) for j in range(1, g.nreg)) / (N * dx) ** 3
    print('   末态: 转变分数 %.4f ; 各变体体积分数 %s' %
          (1 - vt[0] / (N * dx) ** 3, np.round(vt[1:] / vt[1:].sum(), 3)))
    print('   S_v = %.3e 1/m ⇒ 板片厚 t = 2f/S_v = %.1f nm'
          % (sv, 2 * (1 - vt[0] / (N * dx) ** 3) / max(sv, 1e-30) * 1e9))
    return g


if __name__ == '__main__' and False:
    pass


def M3_McLean(N=32, dx=2e-9, nstep=400):
    """面上场 Γ 的局部平衡：应收敛到 McLean/Langmuir 解析值（新表示下重做 H3）"""
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=0.0)
    # 一个平面界面：区域1 占 z<L/2
    g.phi[1] = np.where(np.arange(N)[None, None, :] * dx < 0.5 * N * dx,
                        -1e-9, 1e-9) * np.ones((N, N, N))
    g.init_parent()
    g.c[:] = 0.036
    for _ in range(nstep):
        g.update_Gamma(2e-11)
    m = g.surface_band()
    Geq = g.Gamma_eq(g.c[m])
    rel = float(np.abs(g.Gam[m] - Geq).max() / max(np.abs(Geq).max(), 1e-30))
    print('---- M3 面上场偏析平衡（level-set 表示，重做 H3）----')
    print('   T=%.0f K: Γ_model=%.4e mol/m² ; Γ_McLean=%.4e ; 最大相对差 %.2e   %s'
          % (g.T, float(g.Gam[m].mean()), float(Geq.mean()), rel,
             'PASS' if rel < 0.05 else 'FAIL'))
    return rel < 0.05


def M4_conservation(N=32, dx=2e-9, nstep=150):
    """体相 + 面过剩的守恒（新表示下重做 H4）"""
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, -1e8])
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
    print('---- M4 守恒（体相 + 面过剩，level-set 表示）----')
    print('   初始 %.6e mol ; 末态 %.6e mol ; 相对漂移 %.2e   %s'
          % (mb0 + ms0, mb1 + ms1, rel, 'PASS' if rel < 1e-2 else 'FAIL'))
    return rel < 1e-2


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
