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


if __name__ == '__main__':
    print('=' * 92)
    print('Gibbs 面场（level-set）+ 体相场：判据 S0/S1')
    print('=' * 92)
    res = {}
    res['S0'] = S0_curvature()
    res['S1'] = S1_GibbsThomson()
    print('\n总判定: %s' % ('ALL PASS' if all(res.values())
                          else 'FAIL -> %s' % [k for k, v in res.items() if not v]))
