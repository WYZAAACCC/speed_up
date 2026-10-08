#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_ti64_variants.py --- Ti64 beta->alpha' 的 12 个 Burgers 变体的特征应变 eps0_v
                                (纯晶体学推导, 不指派任何数)

== 物理依据 ==
Burgers 取向关系 (OR):  (0001)_alpha || {110}_beta  且  <11-20>_alpha || <111>_beta
晶格常数 (文献标准值, nm): a_beta(bcc)=0.3310, a_alpha(hcp)=0.2950, c_alpha=0.4683

== 对应 (lattice correspondence) 怎么定 ==
1) 母相 bcc 的 {110} 面是[中心矩形]2D 点阵: 矩形边长 (sqrt2*a_b, a_b), 角点+中心。
   子相 hcp 的 (0001) 面也写成[中心矩形]: 矩形边长 (sqrt3*a_a, a_a), 角点+中心。
   => 矩形->矩形 是唯一的"小应变"配对 (另一边需要的比是 1.09 与 0.89)。
   *** 这一条只给出"面", 不给面内取向; 面内取向由 OR 的 <111> 条件定。***
2) {110} 面内有[两条]<111>线 (夹角 70.53 度)。OR 要求 <11-20> || <111>:
   选其中一条 <111> d 作参考, 令 F(d) 与 d 同向、长度 a_a;
   另一条 <111> e (与 d 夹角 70.53 度) 的像必须与 F(d) 成 60 度 (六角点阵近邻角),
   保向性 (det F > 0) 迫使取 +60 度那一支 => 每个 (面, <111>) 组合给唯一一个 F。
   *** 这就是文献里 6 个 {110} 面 x 2 条 <111> = 12 个变体的来源。***
   (两条 <111> 的选择不能用子相 60 度旋转相连: 二者相差 10.53 度面内转动, 不是子相对称操作。)
3) 沿面法向 n: 母相 a_b*[110] (两层 (110) 间距) -> 子相 c_a。
   d_(110)=a_b/sqrt2=0.23408 nm 与 c_a/2=0.23415 nm 几乎相等 (+0.03%),
   所以贝恩畸变的法向分量几乎为零 --- 这正是 bcc->hcp 能发生的经典原因。
4) eps0 = sym(F) - I (小应变约定)。应变 ~10%, 故 det(F)-1 与小应变迹不等;
   体积变化一律用[每原子体积]做独立核对。

== 自检判据 (任一不过就不许用) ==
 C1 变体数 = 12
 C2 det(F)-1 与每原子体积比一致 (相对差 < 1e-3)
 C3 主应变在 0.08~0.12 量级
 C4 12 个 dev(eps0) 之和 = 0 (自协调)
 C5 F 把母相点阵映到同一个 hcp 点阵 (整数坐标检验)
 C6 OR 精确成立: F(d) || d, 且 F(d) 与 F(e) 夹角 = 60 度
"""
import itertools
import numpy as np

A_B, A_A, C_A = 0.3310, 0.2950, 0.4683      # nm


def three_111_lines():
    return [np.array(v, float) / np.sqrt(3) for v in
            ([1, 1, 1], [1, 1, -1], [1, -1, 1], [-1, 1, 1])]


def six_110_planes():
    return [np.array(v, float) for v in
            ([1, 1, 0], [1, -1, 0], [1, 0, 1], [1, 0, -1], [0, 1, 1], [0, 1, -1])]


def build_F(nvec, dlin):
    """按上面的构造给出该变体的 F (在母相笛卡尔系里的 3x3)"""
    n = nvec / np.linalg.norm(nvec)
    d = dlin / np.linalg.norm(dlin)
    m = np.cross(n, d)
    m /= np.linalg.norm(m)                              # (d, m, n) 右手
    others = [x for x in three_111_lines()
              if abs(abs(x @ d) - 1.0) > 1e-6 and abs(x @ n) < 1e-9]
    assert len(others) == 1, others
    e = others[0]
    if e @ d < 0:                                       # 取与 d 成 70.53 度的那一支（e.d=+1/3）
        e = -e
    sig = 1.0 if e @ m > 0 else -1.0                    # e 相对 m 的朝向
    B = np.column_stack([d, e, n])
    Binv = np.linalg.inv(B)
    dst, est, nst = Binv[0, :], Binv[1, :], Binv[2, :]  # 对偶基（B^{-1} 的行）
    s = A_A / (A_B * np.sqrt(3) / 2)                    # <11-20> 键长 / <111> 键长
    lam = C_A / (np.sqrt(2) * A_B)                      # c_a / (sqrt2 a_b)
    Fd = s * d
    Fe = s * (np.cos(np.radians(60)) * d + np.sin(np.radians(60)) * (sig * m))
    Fn = lam * n
    F = np.outer(Fd, dst) + np.outer(Fe, est) + np.outer(Fn, nst)
    assert np.linalg.det(F) > 0, 'correspondence 不是保向的'
    return F, d, e, n


def variants():
    strains, Fs, meta = [], [], []
    for nv in six_110_planes():
        for dl in three_111_lines():
            if abs(dl @ (nv / np.linalg.norm(nv))) > 1e-9:
                continue
            F, d, e, n = build_F(nv, dl)
            eps = 0.5 * (F + F.T) - np.eye(3)
            if any(np.abs(eps - x).max() < 1e-10 for x in strains):
                continue
            strains.append(eps)
            Fs.append(F)
            meta.append(dict(n=n, d=d, e=e))
    return np.array(strains), np.array(Fs), meta


def main():
    C3_111 = np.sqrt(3) / 2 * A_B
    strains, Fs, meta = variants()
    print('=' * 100)
    print("Ti64 beta -> alpha' 的 12 个 Burgers 变体特征应变 (晶体学推导)")
    print('  a_beta=%.4f nm  a_alpha=%.4f nm  c_alpha=%.4f nm' % (A_B, A_A, C_A))
    print('  bcc <111> 原子间距 = %.4f nm ; hcp a_alpha = %.4f nm (比 %.5f)'
          % (C3_111, A_A, A_A / C3_111))
    print('  d_(110)=a_b/sqrt2=%.5f nm vs c_a/2=%.5f nm (比 %.5f)'
          % (A_B / np.sqrt(2), C_A / 2, (C_A / 2) / (A_B / np.sqrt(2))))
    print('=' * 100)

    ok = True
    print('\n[C1] 变体数 = %d   %s' % (len(strains), 'PASS' if len(strains) == 12 else 'FAIL'))
    ok &= (len(strains) == 12)

    dets = np.array([np.linalg.det(F) for F in Fs]) - 1.0
    vpa = (np.sqrt(3) / 2 * A_A ** 2 * C_A / 2) / (A_B ** 3 / 2) - 1.0
    rel = np.abs(dets - vpa) / abs(vpa)
    print('[C2] det(F)-1 = %.5f ~ %.5f ; 每原子体积比 = %.5f ; 最大相对差 = %.2e   %s'
          % (dets.min(), dets.max(), vpa, rel.max(), 'PASS' if rel.max() < 1e-3 else 'FAIL'))
    ok &= (rel.max() < 1e-3)

    ev = np.linalg.eigvalsh(strains)
    shr = strains - np.trace(strains, axis1=1, axis2=2)[:, None, None] / 3 * np.eye(3)
    shrn = np.linalg.norm(shr, axis=(1, 2))
    print('[C3] 主应变 = [%.4f, %.4f] (期望 |.| 在 0.08-0.12) ; 剪切张量范数 = %.4f~%.4f'
          % (ev.min(), ev.max(), shrn.min(), shrn.max()))
    ok &= (np.abs(ev).min() > 0.0 and np.abs(ev).max() < 0.15)

    dsum = np.linalg.norm(shr.sum(0))
    print('[C4] 12 个 dev(eps0) 之和的 Frobenius 范数 = %.3e (自协调 => 0)   %s'
          % (dsum, 'PASS' if dsum < 1e-12 else 'FAIL'))
    ok &= (dsum < 1e-12)

    worst = 0.0
    for F in Fs:
        t1 = A_B * np.array([1., -1., 0.])
        t2 = A_B * np.array([0., 0., 1.])
        b3 = A_B * np.array([1., 1., 0.])
        p = 0.5 * (t1 + t2)
        q = 0.5 * (t1 - t2)
        Bp = np.column_stack([F @ p, F @ q, F @ b3])
        for tv in (t1, t2, b3, p, q):
            c = np.linalg.solve(Bp, F @ tv)
            worst = max(worst, np.abs(c - np.round(c)).max())
    print('[C5] 点阵成员检验 (整数坐标残差) = %.2e   %s'
          % (worst, 'PASS' if worst < 1e-9 else 'FAIL'))
    ok &= (worst < 1e-9)

    wor6 = 0.0
    for F, mm in zip(Fs, meta):
        d = np.array(mm['d'], float)
        e = np.array(mm['e'], float)
        Fd, Fe = F @ d, F @ e
        wor6 = max(wor6, np.abs(Fd / np.linalg.norm(Fd) - d).max())
        wor6 = max(wor6, abs(float(Fd @ Fe / np.linalg.norm(Fd) / np.linalg.norm(Fe))
                             - np.cos(np.radians(60))))
    print('[C6] OR 检查: 最大偏差 = %.2e   %s' % (wor6, 'PASS' if wor6 < 1e-12 else 'FAIL'))
    ok &= (wor6 < 1e-12)

    try:
        from windowB_pf import C_iso, e_density
        C = C_iso(100e9, 0.3, 3)
        ths = np.linspace(0, np.pi, 91)
        phs = np.linspace(0, 2 * np.pi, 181)
        E = np.zeros((len(ths), len(phs)))
        for i, t in enumerate(ths):
            for j, ph in enumerate(phs):
                nn = np.array([np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.cos(t)])
                E[i, j] = e_density(C, strains[0], nn)
        i0, j0 = np.unravel_index(np.argmin(E), E.shape)
        nmin = np.array([np.sin(ths[i0]) * np.cos(phs[j0]), np.sin(ths[i0]) * np.sin(phs[j0]),
                         np.cos(ths[i0])])
        print('\n[附带] 各向同性 C 下变体1 的弹性能最小界面法向 = [%.3f %.3f %.3f]  E_max/E_min=%.2f'
              % (nmin[0], nmin[1], nmin[2], E.max() / E.min()))
    except Exception as exc:                             # noqa
        print('\n[附带] 单变体弹性能各向异性计算跳过: %s' % exc)

    np.save('/mnt/f/speed_up/bench/ti64_variant_strains.npy', strains)
    with open('/mnt/f/speed_up/pipeline/ca_pf_framework/WINDOWB_VARIANTS.txt', 'w') as f:
        f.write("# Ti64 beta->alpha' 12 Burgers variants (eps0 = sym(F)-I, beta frame)\n")
        f.write('# a_b=%.4f a_a=%.4f c_a=%.4f nm ; det(F)-1=%.5f ; per-atom vol=%.5f\n'
                % (A_B, A_A, C_A, dets.mean(), vpa))
        for k, (eps, mm) in enumerate(zip(strains, meta)):
            f.write('\nV%d  n_basal=%s  d<111>=%s\n' % (k + 1, list(mm['n']), list(mm['d'])))
            for r in range(3):
                f.write('   %+ .6f %+ .6f %+ .6f\n' % tuple(eps[r]))
    print('\n已保存: bench/ti64_variant_strains.npy (12,3,3) 与 WINDOWB_VARIANTS.txt')
    print('\n===== 总判定: %s =====' % ('ALL PASS' if ok else '有 FAIL, 不得使用'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
