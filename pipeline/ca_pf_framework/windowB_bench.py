#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''windowB_bench.py --- Window B 四条物理判据（2D；含【界面迁移率数值标定】）
标定链：① (γ,w) → W=13.18γ/w, κ=1.365γw；② 用 1D 平面界面测 v/Δf ⇒ 得 L 的换算常数
关键物理：屏障 W≈2.5e8 ≫ 化学驱动 ⇒ 无核不转变（= 真实马氏体必须形核于缺陷）
'''
import numpy as np
from windowB_pf import C_iso, e_density, MartensitePF

# ============================================================================
# ⚠ 2026-09-24 状态：本文件的 B1/B2 判据【设计不成立】，已被 windowB_bench3d.py 取代。
#   原因（实测）：
#     · B1 用"结构因子峰值方向"当板条法向 —— 单变体在周期盒里形成方块/条纹，
#       峰值方向被网格各向异性与盒尺寸锁死，测出的不是物理惯习面。
#     · B2 的"非孪晶对"不是良定义对照：eX 与"孪晶对" eB 的 de 振幅、均匀项都不同，
#       层片总能被均匀项主导（实测两者逐位相同 9.6026e-06）。
#   正确做法（已在 3D 版实现）：用 rank-1/Hadamard 相容条件筛真相容对，并用
#   【同几何、同法向、同体积分数】对照；层片起伏能有闭式 E = (1/2)V*S*de:Lam(n):de。
#   B3/B4 物理仍成立，但 B4 在修 sigma 归一化（少 N^dim 倍）前后不可比。
# ============================================================================

GAM, WW = 0.15, 8e-9
KAP, WBAR = 1.365 * GAM * WW, 13.18 * GAM / WW
V_TARGET = 100.0       # 目标界面速度 [m/s]（位移型界面很快；远小于热循环时间 ⇒ 建造期内瞬完）


def calib_L(df=1e7, L_trial=1e-8, nst=4000, dt=1e-9, Nx=128):
    """1D 平面界面：用【变体体积分数增长】测界面速度（符号明确）
       v = (ΔF)·L_box/t ；C1 = v/(L_trial·Δf)（物理上 ≈ 界面半宽量级）"""
    dx = 2e-9
    Lbox = Nx * dx
    C = C_iso(100e9, 0.3, 2)
    eps0 = np.zeros((1, 2, 2))
    a = np.sqrt(KAP / (2 * WBAR))
    x = (np.arange(Nx) + 0.5) * dx
    pf = MartensitePF(Nx, Lbox, C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM, dG=df)
    pf.W = WBAR; pf.Lmob = L_trial
    pf.phi[0] = 0.5 * (1 - np.tanh((x - 0.25 * Lbox) / (2 * a)))
    f0 = pf.phi[0].mean()
    for _ in range(nst):
        pf.step(dt, cap_sum=False)
    v = (pf.phi[0].mean() - f0) * Lbox / (nst * dt)
    return v / (L_trial * df), v


def mk(pf_args, eps0, seeds, N, no_seed=False, lam=None, rng_seed=0):
    C = pf_args['C']
    pf = MartensitePF(N, pf_args['L'], C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM,
                      dG=pf_args['dG'], sigma_ext=pf_args.get('sigma_ext'))
    pf.W = WBAR
    pf.Lmob = pf_args['Lmob']
    rng = np.random.default_rng(rng_seed)
    pf.phi[:] = 0.0
    nv = len(pf.eps0)
    if lam is not None:
        xx = np.arange(N)
        m = ((xx // lam) % 2 == 0).astype(float)[None, :] * np.ones((N, 1))
        pf.phi[0] = m
        if nv > 1:
            pf.phi[1 % nv] += (1 - m)
        return pf
    if no_seed:
        return pf
    for v in range(nv):
        for _ in range(seeds):
            i = int(rng.integers(N // 2)); j = int(rng.integers(N // 2))
            pf.phi[v, i:i + N // 8, j:j + N // 8] = 1.0
    return pf


def main():
    C = C_iso(100e9, 0.3, 2)
    C1, v_raw = calib_L()
    MINT = V_TARGET / 1e7                 # 使 v = M_int·Δf = 100 m/s（Δf=1e7 处）
    Lmob = MINT / C1
    print('=' * 96)
    print('Window B PF 物理判据（2D）')
    print('标定: γ=%.2f J/m², w=%.0f nm ⇒ W=%.2e J/m³, κ=%.2e J/m' % (GAM, WW*1e9, WBAR, KAP))
    print('      1D 标定(体积分数法): C1 = %.3e, v(L=1e-8) = %.3e m/s ⇒ v_target=%.0f m/s ⇒ L = %.3e' % (
        C1, v_raw, V_TARGET, Lmob))
    print('=' * 96)
    e0 = np.array([[0.06, 0.04], [0.04, -0.03]])
    rr = np.array([[np.cos(2*np.pi/3), -np.sin(2*np.pi/3)], [np.sin(2*np.pi/3), np.cos(2*np.pi/3)]])
    triad = np.array([e0, rr @ e0 @ rr.T, rr.T @ e0 @ rr])
    N, L = 128, 2e-7
    base = dict(C=C, L=L, Lmob=Lmob)
    ns = 4000
    dt = 2e-12

    # B1 单变体：有核 ⇒ 长大；取向取解析最省能法向
    ths = np.linspace(0, np.pi, 1441)
    Es = np.array([e_density(C, e0, np.array([np.cos(t), np.sin(t)])) for t in ths])
    tgt = np.degrees(ths[int(np.argmin(Es))]) % 180.0
    pf = mk(dict(base, dG=1e7), e0[None], 1, N, rng_seed=1)
    for s in range(ns):
        pf.step(dt)
    ph = pf.phi[0]
    pk = np.abs(np.fft.fftn(ph - ph.mean()))**2; pk.flat[0] = 0
    kg = np.stack(np.meshgrid(*pf.k, indexing='ij'), -1)
    kk = kg[np.unravel_index(int(np.argmax(pk)), pk.shape)]
    ang = np.degrees(np.arctan2(kk[1], kk[0])) % 180.0
    dev = min(abs(ang-tgt), 180-abs(ang-tgt))
    print('\n[B1] 单变体(有核): 体积分数 %.3f；解析最省能法向 %.1f° vs PF %.1f° ⇒ 差 %.1f°  %s' % (
        ph.mean(), tgt, ang, dev, 'PASS' if (ph.mean() > 0.15 and dev <= 12) else 'FAIL'))

    # B2 替代判据：与惯习面"相容"的孪晶对 vs 不相容对 ⇒ 弹性能应显著更低
    eB = np.array([[0.06, -0.04], [-0.04, -0.03]])        # 孪晶对（剪切反号）
    eX = np.array([[0.06, 0.00], [0.00, -0.03]])          # 非孪晶对
    def lamE(eps, lam=8):
        pf2 = mk(dict(base, dG=0), np.array([e0, eps]), 0, N, lam=lam)
        return pf2.E_el()
    E_twin, E_other = lamE(eB), lamE(eX)
    print('\n[B2] 层片相容性：孪晶对 E_el = %.4e J vs 非孪晶对 %.4e J ⇒ 比 %.3f  %s' % (
        E_twin, E_other, E_twin / E_other, 'PASS' if E_twin < 0.9 * E_other else 'FAIL'))

    # B3 自协调
    mdev = lambda A: A - 0.5*np.trace(A)*np.eye(2)
    pf3 = MartensitePF(N, L, C, triad, kappa=KAP, w=WW, gamma=GAM, M_int=0)
    n3 = N//3; pf3.phi[:] = 0
    pf3.phi[0][:, :n3] = 1; pf3.phi[1][:, n3:2*n3] = 1; pf3.phi[2][:, 2*n3:] = 1
    pf1 = MartensitePF(N, L, C, e0[None], kappa=KAP, w=WW, gamma=GAM, M_int=0); pf1.phi[0] = 1
    ddev = np.linalg.norm(mdev(triad.mean(0))); ratio = pf3.E_el()/pf1.E_el()
    print('\n[B3] 自协调：三变体均分 ‖dev(⟨ε⁰⟩)‖ = %.2e（≈0）；E_el 比 = %.3f  %s' % (
        ddev, ratio, 'PASS' if (ddev < 1e-12 and ratio < 0.8) else 'FAIL'))

    # B4 外载择优
    s_ext = np.array([[3e8, 0.0], [0.0, 0.0]])
    sc = np.array([-np.einsum('ij,ij->', s_ext, e) for e in triad]); win = int(np.argmax(sc))
    pf4 = mk(dict(base, dG=3e6, sigma_ext=s_ext), triad, 2, N, rng_seed=3)
    for s in range(ns):
        pf4.step(dt)
    fr = pf4.phi.reshape(3, -1).mean(1)
    print('\n[B4] 外载择优：解析 %s ⇒ 预测 %d；PF %s ⇒ 占优 %d  %s' % (
        np.round(sc/np.abs(sc).max(), 3), win+1, np.round(fr, 3), int(np.argmax(fr))+1,
        'PASS' if int(np.argmax(fr)) == win else 'FAIL'))


if __name__ == '__main__':
    main()
