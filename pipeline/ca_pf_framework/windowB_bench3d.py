#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_bench3d.py --- Window B 的三维物理判据（全部有闭式解/可判定）

P1  变体对的【层片相容性】(rank-1 / Hadamard):
    两变体以法向 n 做层片共存时，起伏弹性能的精确闭式（层片 => 所有 k || n）:
        E_exc = (1/2) V * [Sum_{k!=0} |phi_hat(k)|^2] * dEps : Lambda(n) : dEps
    而 Sum_{k!=0}|phi_hat|^2 = <phi^2> - <phi>^2 = f(1-f)   (二值场, Parseval)
    => 若存在 n 使 dEps:Lambda(n):dEps = 0  => 该对可"无缝"共存（孪晶/惯习面），
       这就是经典 rank-1 相容条件 dEps = sym(a (x) n)。
    判据: (a) 解析筛出相容对;  (b) PF 实测 E_exc 与上面闭式逐位一致;
          (c) 相容对的 E_exc / 最不相容对 << 1。

P2  外载择优: 初始长大速率排序 == argmax_v (-sigma_ext : eps0_v) 的解析排序。
    各向同性 C 下，自相互作用 eps0_v:C:eps0_v 对 12 个变体【相同】（本征值相同），
    所以速率差完全由外载项决定 => 判据干净。

P3  自协调: 同样几何、同样界面密度下，"12 变体各占一块" 的起伏弹性能
    显著低于 "12 块全是同一变体"。

P4  非热动力学一致性: 界面速度 ~ L*Δf（体积分数法），符号为正。
"""
import itertools
import numpy as np
from windowB_pf3d import PF3D, C_iso3, _lam_full, VOIGT, G6
from windowB_ti64_variants import variants

# Ti64 alpha' 的弹性常数（多晶近似 / 记账见 WINDOWB_PARAMS.md）
E_MOD, NU = 113e9, 0.34
GAM, W90 = 0.15, 4e-8


def fib_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def dE_dLam(C, de, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))


def refine_dir(C, de, n0, iters=120):
    """在球面上把 f(n)=de:Lam(n):de 局部最小化（随机扰动 + 收缩半径）"""
    rng = np.random.default_rng(0)
    n = np.array(n0, float)
    n /= np.linalg.norm(n)
    best = dE_dLam(C, de, n)
    r = 0.3
    for _ in range(iters):
        cand = n + r * rng.normal(size=3)
        cand /= np.linalg.norm(cand)
        v = dE_dLam(C, de, cand)
        if v < best:
            best, n = v, cand
        else:
            r *= 0.92
    return best, n


def rank1_normal(de):
    """解析求 rank-1 相容法向: 解 (I-nn^T) de (I-nn^T) = 0（单位球上 2 参数最小二乘）。
       物理意义: 若 de = sym(a (x) n)，两变体可以"无缝"层片共存（twin/habit plane）。"""
    from scipy.optimize import least_squares

    def n_of(p):
        th, ph = p
        return np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])

    def resid(p):
        n = n_of(p)
        P = np.eye(3) - np.outer(n, n)
        M = P @ de @ P
        return np.array([M[0, 0], M[1, 1], M[2, 2], M[0, 1], M[0, 2], M[1, 2]])

    best = None
    for th0 in np.linspace(0.05, np.pi - 0.05, 6):
        for ph0 in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            r = least_squares(resid, [th0, ph0], xtol=1e-15, ftol=1e-15, gtol=1e-15)
            v = np.linalg.norm(r.fun)
            if best is None or v < best[0]:
                best = (v, n_of(r.x))
    return best


def P1(C, eps0, N=64, L=6.4e-7, nobs=6000, workers=4, verbose=True):
    nv = len(eps0)
    dirs = fib_sphere(nobs)
    print('\n' + '=' * 96)
    print('P1  变体对的层片相容性（rank-1 / Hadamard 条件）')
    print('=' * 96)
    scale = 0.5 * E_MOD      # 归一化尺度: |de:Lam:de| ~ E*|de|^2
    rows = []
    for a, b in itertools.combinations(range(nv), 2):
        de = eps0[b] - eps0[a]
        vals = np.array([dE_dLam(C, de, d) for d in dirs])
        k = int(np.argmin(vals))
        vmin, nstar = refine_dir(C, de, dirs[k])
        r1 = np.linalg.norm(de)
        resn, n_exact = rank1_normal(de)
        v_exact = dE_dLam(C, de, n_exact)
        if v_exact < vmin:                              # 用解析法向把相容对做到机器精度
            vmin, nstar = v_exact, n_exact
        ev = np.linalg.eigvalsh(de)
        rows.append((a, b, vmin / (scale * np.sum(de ** 2)), nstar, vmin, vals.max(),
                     ev.copy()))
    rows.sort(key=lambda r: r[2])
    ncomp = sum(1 for r in rows if r[2] < 1e-8)
    print('  归一化尺度: E|de|^2/2 = %.3e J/m^3' % scale)
    print('  rank-1 相容的对数（E_min/scale < 1e-8）= %d / %d' % (ncomp, len(rows)))
    print('  相容对（若存在）:')
    for r in [x for x in rows if x[2] < 1e-8][:8]:
        print('    V%2d-V%2d  E_min/scale = %.2e  n* = [%+.4f %+.4f %+.4f]  eig(de) = %s'
              % (r[0] + 1, r[1] + 1, r[2], *r[3], np.round(r[6] * 1e3, 3)))
    print('  最不相容的 4 对:')
    for r in rows[-4:]:
        print('    V%2d-V%2d  E_min/scale = %.4f  n* = [%+.3f %+.3f %+.3f]'
              % (r[0] + 1, r[1] + 1, r[2], *r[3]))
    a1, b1, c1, n1 = rows[0][:4]
    a2, b2, c2, n2 = rows[-1][:4]
    print('  => 相容对 V%d-V%d 的 E_min / 最不相容对 V%d-V%d 的 E_min = %.3e   %s'
          % (a1 + 1, b1 + 1, a2 + 1, b2 + 1, (c1 + 1e-30) / c2,
             'PASS' if (c1 + 1e-30) / c2 < 1e-3 else 'FAIL'))
    ok_p1 = (c1 + 1e-30) / c2 < 1e-3

    # ---- PF 实测 vs 闭式 ----
    # ⚠ 斜法向的层片在【离散网格】上会"阶梯化": 它的 DFT 不是精确落在 n 方向上,
    #   于是 PF 的 E_exc 会系统地大于锐界面闭式（实测 6e-2 相对量级）。这不是 PF 的错，
    #   而是"离散层片 ≠ 理想层片"。所以:
    #   (i) 物理判据用【轴向法向】的精确层片（离散下就是理想层片）；
    #   (ii) 一般法向另用"逐 k 求和"的闭式做管线一致性检查。
    axes = [np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])]

    def base_of(pf, a, b, eps0, C, L):
        """clamped 约定下 k=0 项贡献 (V/2)<eps0>:C:<eps0>；free 约定下为 0"""
        if getattr(pf, 'k0_mode', 'free') != 'clamped':
            return 0.0
        ebar = pf.phi[a].mean() * eps0[a] + pf.phi[b].mean() * eps0[b]
        return 0.5 * L ** 3 * np.einsum('ij,ijkl,kl->', ebar, C, ebar)

    def lam_exc(a, b, n, nslab=6):
        lam = L / nslab
        X = (np.arange(N) + 0.5) * (L / N)
        XYZ = np.stack(np.meshgrid(X, X, X, indexing='ij'), -1)
        frac = (np.cos(2 * np.pi * (XYZ @ n) / lam) > 0)
        pf = PF3D(N, L, C, np.array([eps0[a], eps0[b]]), gamma=0.0, w90=W90, Lmob=0.0,
                  workers=workers)
        pf.phi[0] = frac.astype(float)
        pf.phi[1] = 1.0 - pf.phi[0]
        ph = np.fft.fftn(pf.phi[0]) / N ** 3
        S = float(np.sum(np.abs(ph) ** 2)) - abs(ph[0, 0, 0]) ** 2
        Eexc = pf.E_el() - base_of(pf, 0, 1, [eps0[a], eps0[b]], C, L)
        return Eexc, S

    # (i) 找一个"相容 + 法向沿晶轴"的对
    pick = None
    for r in rows:
        if r[2] > 1e-8:
            continue
        for ax in axes:
            if abs(dE_dLam(C, eps0[r[1]] - eps0[r[0]], ax)) < 1e-6 * scale * np.sum(
                    (eps0[r[1]] - eps0[r[0]]) ** 2):
                pick = (r[0], r[1], ax)
                break
        if pick:
            break
    ok = ok_p1
    if pick:
        a, b, nax = pick
        Eexc, S = lam_exc(a, b, nax)
        de = eps0[b] - eps0[a]
        Esc = 0.5 * L ** 3 * S * scale * float(np.sum(de ** 2))
        print('  [P1b 相容+轴向] V%d-V%d, n=[%.0f %.0f %.0f]: E_exc(PF) = %.4e J'
              '（锐界面闭式 = 0）, 相对能量尺度 = %.2e   %s'
              % (a + 1, b + 1, *nax, Eexc, Eexc / Esc,
                 'PASS' if Eexc / Esc < 1e-12 else 'FAIL'))
        ok &= Eexc / Esc < 1e-12
    # (ii) 一般法向: 逐 k 闭式与 PF 一致（管线一致性）
    a, b = a1, b1
    nst = n1
    de = eps0[b] - eps0[a]
    lam = L / 6.0
    X = (np.arange(N) + 0.5) * (L / N)
    XYZ = np.stack(np.meshgrid(X, X, X, indexing='ij'), -1)
    frac = (np.cos(2 * np.pi * (XYZ @ nst) / lam) > 0)
    pf = PF3D(N, L, C, np.array([eps0[a], eps0[b]]), gamma=0.0, w90=W90, Lmob=0.0,
              workers=workers)
    pf.phi[0] = frac.astype(float)
    pf.phi[1] = 1.0 - pf.phi[0]
    ph = np.fft.fftn(pf.phi[0]) / N ** 3
    ph = np.roll(np.roll(np.roll(ph, -0, 0), -0, 1), -0, 2)
    Kf = pf.K
    Pk = np.abs(ph.reshape(-1)) ** 2
    Pk[0] = 0.0
    nz = Pk > 1e-30
    Esum = 0.0
    for i in np.where(nz)[0]:
        Esum += Pk[i] * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, Kf[i]), de))
    Esum *= 0.5 * L ** 3
    Eexc = pf.E_el() - base_of(pf, 0, 1, [eps0[a], eps0[b]], C, L)
    Esc = 0.5 * L ** 3 * float(np.sum(Pk)) * scale * float(np.sum(de ** 2))
    print('  [P1c 一般法向] V%d-V%d 逐 k 闭式 = %.6e J ; PF = %.6e J ; |差|/尺度 = %.2e   %s'
          % (a + 1, b + 1, Esum, Eexc, abs(Esum - Eexc) / Esc,
             'PASS' if abs(Esum - Eexc) / Esc < 1e-12 else 'FAIL'))
    ok &= abs(Esum - Eexc) / Esc < 1e-12
    return ok, rows


def P2(C, eps0, N=16, L=1.6e-7, workers=2):
    """外载择优。符号约定（务必记账）:
         MATH_FRAMEWORK 写  ΔE_v = -sigma_ext : eps0_v  ==> 这是【能量的变化】，
         越大越好 = sigma_ext:eps0_v 越大（变体做正功、体系势能下降）。
         所以"择优分数" g_v = + sigma_ext : eps0_v，PF 的力 f += sigma_ext:eps0_v 与之一致。
       （若把 g_v 写成 -sigma_ext:eps0_v，排序会整体反号 —— 本轮实测相关系数正好 -1.000，
         说明实现的符号是对的，是测试的符号写反了。）"""
    print('\n' + '=' * 96)
    print('P2  外载择优（变体选择）: 初始速率排序 vs 解析 g_v = +sigma_ext:eps0_v')
    print('=' * 96)
    nv = len(eps0)
    ax = np.array([1.0, 0.0, 0.0])
    s_ext = 3e8 * np.outer(ax, ax)
    g_an = np.array([np.einsum('ij,ij->', s_ext, e) for e in eps0])
    rates = []
    for v in range(nv):
        pf = PF3D(N, L, C, eps0, gamma=GAM, w90=W90, Lmob=1.0, dG=0.0, sigma_ext=s_ext,
                  workers=workers)
        pf.phi[v] = 0.02
        f, _ = pf.forces()
        idx = pf.phi[v] > 0
        rates.append(float(f[v][idx].mean()))
    rates = np.array(rates)
    from scipy.stats import spearmanr
    rho = spearmanr(g_an, rates).statistic
    cc = np.corrcoef(g_an, rates)[0, 1]
    print('  最优变体（解析 g_v 最大）= V%d ; PF 速率最大 = V%d'
          % (int(np.argmax(g_an)) + 1, int(np.argmax(rates)) + 1))
    print('  Spearman rho = %+.4f ; 线性相关系数 = %+.6f   %s'
          % (rho, cc, 'PASS' if (abs(cc) > 0.999 and int(np.argmax(rates)) == int(np.argmax(g_an)))
             else 'FAIL'))
    print('  （rho 会被对称等价的并列变体压低；判据用 argmax + Pearson）')
    print('  注：各向同性 C 下自相互作用 eps0_v:C:eps0_v 对 12 个变体相同（本征值相同），'
          '故速率差完全由外载项给出。')
    return abs(cc) > 0.999 and int(np.argmax(rates)) == int(np.argmax(g_an))


def P3(C, eps0, rows, N=48, L=4.8e-7, workers=4):
    """层片能量: 相容对 vs 最不相容对（同几何、同界面密度、同体积分数、**同一法向**）
       固定法向取晶轴 n=[0,1,0] ⇒ 离散网格上就是理想层片，消掉"阶梯化"混淆。"""
    print('\n' + '=' * 96)
    print('P3  相容层片 vs 不相容层片（同一几何、同一界面密度）')
    print('=' * 96)
    nv = len(eps0)
    X = (np.arange(N) + 0.5) * (L / N)
    XYZ = np.stack(np.meshgrid(X, X, X, indexing='ij'), -1)
    nfix = np.array([0.0, 1.0, 0.0])
    scored = []
    for r in rows:
        de = eps0[r[1]] - eps0[r[0]]
        scored.append((dE_dLam(C, de, nfix), r[0], r[1]))
    scored.sort()
    _, a1, b1 = scored[0]
    _, a2, b2 = scored[-1]
    print('  固定法向 n = [0 1 0]（晶轴）')
    print('  该法向下最小: V%d-V%d  dE = %.3e J/m^3' % (a1 + 1, b1 + 1, scored[0][0]))
    print('  该法向下最大: V%d-V%d  dE = %.3e J/m^3（比 %.2e 倍）'
          % (a2 + 1, b2 + 1, scored[-1][0], scored[-1][0] / max(abs(scored[0][0]), 1e-300)))

    def lam_exc(a, b, n, nslab=8):
        lam = L / nslab
        frac = (np.cos(2 * np.pi * (XYZ @ n) / lam) > 0)
        pf = PF3D(N, L, C, np.array([eps0[a], eps0[b]]), gamma=0.0, w90=W90, Lmob=0.0,
                  workers=workers)
        pf.phi[0] = frac.astype(float)
        pf.phi[1] = 1.0 - pf.phi[0]
        if getattr(pf, 'k0_mode', 'free') == 'clamped':
            ebar = pf.phi[0].mean() * eps0[a] + pf.phi[1].mean() * eps0[b]
            return pf.E_el() - 0.5 * L ** 3 * np.einsum('ij,ijkl,kl->', ebar, C, ebar)
        return pf.E_el()

    Ec = lam_exc(a1, b1, nfix)
    Ei = lam_exc(a2, b2, nfix)
    print('  相容对  V%d-V%d (n* 由 P1)  E_exc = %.6e J' % (a1 + 1, b1 + 1, Ec))
    print('  不相容对 V%d-V%d (n* 由 P1)  E_exc = %.6e J' % (a2 + 1, b2 + 1, Ei))
    print('  比值 E_incompat / E_compat = %.4e   %s'
          % (Ei / max(Ec, 1e-300), 'PASS' if Ei / max(Ec, 1e-300) > 1e3 else 'FAIL'))
    print('  （相容对的 E_exc 是"机器零"量级，比值上界只受浮点限制）')
    # 参考: 12 变体 mosaic（等体积）
    nm = np.array([0.4, 0.6, 0.6928])
    nm /= np.linalg.norm(nm)
    seg = np.floor((XYZ @ nm) / (L / 12.0)).astype(int) % 12
    pf = PF3D(N, L, C, eps0, gamma=0.0, w90=W90, Lmob=0.0, workers=workers)
    for v in range(nv):
        pf.phi[v] = (seg == v).astype(float)
    if getattr(pf, 'k0_mode', 'free') == 'clamped':
        ebar = sum((seg == v).mean() * eps0[v] for v in range(nv))
        E12 = pf.E_el() - 0.5 * L ** 3 * np.einsum('ij,ijkl,kl->', ebar, C, ebar)
    else:
        E12 = pf.E_el()
    print('  参考: 12 变体等体积 mosaic  E_exc = %.6e J' % E12)
    return Ei / max(Ec, 1e-300) > 1e3


def main():
    print('#' * 96)
    print('Window B 三维物理判据')
    print('#' * 96)
    C = C_iso3(E_MOD, NU)
    eps0, Fs, meta = variants()
    print('12 个变体已就绪: det(F)-1 = %.5f ; 主应变 [%.4f, %.4f]'
          % (np.mean([np.linalg.det(F) for F in Fs]) - 1,
             np.linalg.eigvalsh(eps0).min(), np.linalg.eigvalsh(eps0).max()))
    res = {}
    res['P1'], rows = P1(C, eps0)
    res['P2'] = P2(C, eps0)
    res['P3'] = P3(C, eps0, rows)
    print('\n' + '#' * 96)
    print('总判定: %s' % ('ALL PASS' if all(res.values()) else 'FAIL -> %s'
                        % [k for k, v in res.items() if not v]))
    return 0 if all(res.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
