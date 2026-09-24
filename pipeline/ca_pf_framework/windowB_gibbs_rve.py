#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_gibbs_rve.py --- Gibbs 面版板条 RVE + 金相学几何测量

用法: python windowB_gibbs_rve.py N=96 dx=1.0e-8 nstep=300 df=5.0e7 k0=clamped tag=_c

几何测量（都用金相学标准量）:
  * 变体体积分数 f_v
  * 界面积 A = dx^2 * (# 异标签近邻键)   （离散面积测度；立方网格对斜面 <=15% 偏差）
  * **平均截距长度** L3 = 4 f_v / (A_v/V)（Smith-Guttman: 平均截距 = 4V_v/S_v；对板条
    这种片状组织, 沿三个轴分别做弦长统计给出片厚）
  * 界面法向直方图（每个异键的方向统计）—— 与晶体学预测的 rank-1 相容法向对照
  * 变体对统计（哪些变体对占据界面）—— 应与相容对一致
"""
import os
import sys
import time
import numpy as np

from windowB_gibbs import GibbsLath, pairs6
from windowB_pf3d import C_iso3
from windowB_ti64_variants import variants

OUT = '/mnt/f/speed_up/bench/windowB_gibbs'


def mean_intercept_per_axis(lab, v):
    """沿 x/y/z 三个方向对变体 v 做弦长统计（周期边界），返回三个方向的平均弦长"""
    N = lab.shape[0]
    out = []
    for ax in range(3):
        m = np.moveaxis(lab == v + 1, ax, 0)
        # 弦长: 每一条线上连续 True 的长度
        lens = []
        for i in range(m.shape[1]):
            pass
        flat = m.reshape(m.shape[0], -1)
        # 用差分找 run 边界（周期）
        for c in range(flat.shape[1]):
            col = flat[:, c]
            if not col.any():
                continue
            d = np.diff(np.concatenate([[col[-1]], col.astype(int), [col[0]]]))
            starts = np.where(d == 1)[0]
            ends = np.where(d == -1)[0]
            for s0, e0 in zip(starts, ends):
                lens.append((e0 - s0) % len(col) or len(col))
        out.append(float(np.mean(lens)) if lens else np.nan)
    return out


def iface_normals(lab):
    """界面法向直方图：按 26 个方向统计异键（权重 dx^2）"""
    N = lab.shape[0]
    dirs = {}
    for dx_ in (-1, 0, 1):
        for dy_ in (-1, 0, 1):
            for dz_ in (-1, 0, 1):
                if (dx_, dy_, dz_) == (0, 0, 0):
                    continue
                c = int(np.count_nonzero(np.roll(lab, (dx_, dy_, dz_), axis=(0, 1, 2)) != lab))
                dirs[(dx_, dy_, dz_)] = c / 2.0
    return dirs


def do_geometry(lab, dx, eps0, C, tag, fh):
    nv = len(eps0)
    N = lab.shape[0]
    V = (N * dx) ** 3
    tot = lab.size
    fh.write('  --- 几何测量 (N=%d, dx=%.2f nm, 域=%.3f um) ---\n'
             % (N, dx * 1e9, N * dx * 1e6))
    frac = np.array([np.count_nonzero(lab == v + 1) for v in range(nv)]) / tot
    fh.write('  变体体积分数: %s\n' % np.round(frac, 4))
    fh.write('    max/min = %.3f（1.0 = 完全均分 = 自协调）\n'
             % (frac.max() / max(frac.min(), 1e-12)))
    f_parent = np.count_nonzero(lab == 0) / tot
    fh.write('  母相分数 = %.4f\n' % f_parent)
    A = 0.0
    for d in pairs6():
        A += int(np.count_nonzero(np.roll(lab, d, axis=(0, 1, 2)) != lab)) / 2.0
    A *= dx ** 2
    fh.write('  界面积 A = %.4e m^2 ; 单位体积界面积 S_v = %.4e 1/m\n'
             % (A, A / V))
    # ★ 立体学: 板片(plate)的界面积密度 S_v = 2 f / t  =>  t = 2 f / S_v
    #   （先前误用 6V/A 当"等效板条厚"，那会把体积分数混进厚度里 —— 已更正并记账）
    Sv = A / V
    ftr = 1.0 - np.count_nonzero(lab == 0) / tot
    fh.write('  单位体积界面积 S_v = %.4e 1/m ; 板片厚度 t = 2f/S_v = %.1f nm\n'
             % (Sv, (2 * ftr / Sv * 1e9) if Sv > 0 else float('nan')))
    fh.write('  （旧写法 6V/A = %.1f nm 是错的：它把体积分数混进了厚度）\n'
             % (6 * V / A * 1e9))
    for v in range(nv):
        if frac[v] < 0.01:
            continue
        mi = mean_intercept_per_axis(lab, v)
        sv = 4 * frac[v] / (6 * V / A) if A > 0 else np.nan
        fh.write('    V%2d: f=%.3f  平均截距(x,y,z) = %s 格 = %s nm\n'
                 % (v + 1, frac[v], np.round(mi, 1), np.round(np.array(mi) * dx * 1e9, 1)))
    nd = iface_normals(lab)
    tot_b = sum(nd.values())
    top = sorted(nd.items(), key=lambda kv: -kv[1])[:8]
    fh.write('  界面法向（26 邻域）占比前 8:\n')
    for k, c in top:
        fh.write('    dir=%-12s %.4f\n' % (str(k), c / max(tot_b, 1e-30)))
    # 变体对统计
    pc = {}
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        nb = np.roll(lab, d, axis=(0, 1, 2))
        m = (nb != lab)
        a = lab[m].astype(int)
        b = nb[m].astype(int)
        for x, y in zip(a, b):
            k = (min(x, y), max(x, y))
            pc[k] = pc.get(k, 0) + 1
    tt = sum(pc.values())
    top2 = sorted(pc.items(), key=lambda kv: -kv[1])[:10]
    fh.write('  界面上的变体对（前三轴）占前 10:\n')
    for k, c in top2:
        fh.write('    (%d,%d): %.4f\n' % (k[0], k[1], c / max(tt, 1)))
    return frac, A


def shape_stats(lab, dx, eps0, C, fh, min_cells=40, topk=8):
    """回转张量形状统计 + 与晶体学预测（rank-1 相容法向）的对照 —— G4 的正确测度。
       板条判据: 回转张量本征值 a>=b>=c, 板条応 a≈b>>c（扁平）;
                最小本征值的本征向量 = 板的法向; 与"该变体对上预测的相容法向"比对夹角。"""
    from scipy import ndimage
    from windowB_pf3d import _lam_full
    struct = np.ones((3, 3, 3), int)
    nv = len(eps0)
    # 该变体对是否存在 rank-1 相容法向（Δε = sym(a(x)n)）: 用最小化 |(I-nn)Δ(I-nn)| 求
    from windowB_bench3d import rank1_normal
    comp = {}
    for a in range(nv):
        for b in range(a + 1, nv):
            res, n = rank1_normal(eps0[b] - eps0[a])
            if res < 1e-9:
                comp[(a + 1, b + 1)] = n
    fh.write('  --- 回转张量形状统计（G4 测度）---\n')
    fh.write('  rank-1 相容的变体对: %d 对；这里按"每对预测一个相容法向"做对照\n' % len(comp))
    rows = []
    for v in range(1, nv + 1):
        m = (lab == v)
        if not m.any():
            continue
        lbl, n = ndimage.label(m, structure=struct)
        sizes = ndimage.sum(m, lbl, range(1, n + 1))
        for j, sz in enumerate(sizes, start=1):
            if sz < min_cells:
                continue
            pts = np.argwhere(lbl == j).astype(float) * dx
            pts -= pts.mean(0)
            G = (pts.T @ pts) / len(pts)
            w, V = np.linalg.eigh(G)          # 升序
            rows.append((sz, v, w, V[:, 0]))
    rows.sort(key=lambda r: -r[0])
    fh.write('  最大的 %d 个域:\n' % min(topk, len(rows)))
    for sz, v, w, nvec in rows[:topk]:
        r31 = (w[2] / max(w[0], 1e-30)) ** 0.5
        r21 = (w[1] / max(w[0], 1e-30)) ** 0.5
        fh.write('    V%2d 体积=%6d 胞  回转半轴比 c:a=%.2f b:a=%.2f  n=[%+.2f %+.2f %+.2f]\n'
                 % (v, int(sz), r21, r31, *nvec))
    # 夹角: 每个大域的法向 vs "该变体与其最常见邻居"的相容法向
    angs = []
    for sz, v, w, nvec in rows[:40]:
        best = None
        for (a, b), nrm in comp.items():
            if v not in (a, b):
                continue
            ang = np.degrees(np.arccos(min(1.0, abs(float(nvec @ nrm)))))
            if best is None or ang < best:
                best = ang
        if best is not None:
            angs.append(best)
    if angs:
        fh.write('  大域法向 vs 该变体参与的【相容对法向】的最近夹角: 中位数 %.1f deg, '
                 '25%%分位 %.1f deg, 最小 %.1f deg\n'
                 % (np.median(angs), np.percentile(angs, 25), min(angs)))
    return rows


def main(N=96, dx=1e-8, nstep=300, df=5e7, gamma=0.15, k0='clamped',
         nsel=4000, tag='', seed=7, monitor=25, aniso=0.0, nplate=3, rfrac=0.25):
    os.makedirs(OUT, exist_ok=True)
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    L = N * dx
    g = GibbsLath(N, L, C, eps0, gamma, df, workers=8, k0_mode=k0)
    g.aniso = float(aniso)
    g._build_w_tables()
    nrm = []
    for v in range(g.nv):
        nv_, ev_ = g.favorable_normal(v)
        nrm.append(nv_)
    print('  各变体最省能法向（0.5 eps:Lam:eps）: %s'
          % np.round([g.favorable_normal(v)[1] for v in range(3)], 1))
    npl = 0
    for v in range(g.nv):
        npl += g.seed_plates(v, nrm[v], thick_cells=2, nplate=nplate, rng=seed + v,
                             radius_cells=max(3, int(rfrac * N)))
    print('=' * 96)
    print('Gibbs 面板条 RVE: N=%d dx=%.1f nm 域=%.2f um | gamma=%.3f df=%.2e k0=%s'
          % (N, dx * 1e9, L * 1e6, gamma, df, k0))
    print('  板条形核: 每变体 3 片 x 2 胞厚, 沿各自最省能法向 ; 实际放置 %d 片' % npl)
    print('  每遍提议 %d 个位点' % nsel)
    print('=' * 96)
    rng = np.random.default_rng(1)
    t0 = time.time()
    hist = []
    for k in range(nstep + 1):
        if k % monitor == 0 or k == nstep:
            Eb = g.E_el(); Es = g.E_surf(); Ec = g.E_chem()
            frac = np.array([np.count_nonzero(g.lab == v + 1) for v in range(g.nv)]) / g.lab.size
            hist.append((k, Eb, Es, Ec, Eb + Es + Ec, g.n_unlike(), frac.max()))
            print('  it %4d/%d  E_el=%.4e  E_surf=%.4e  E_chem=%.4e  E_tot=%.4e  '
                  'A键=%d  f_parent=%.3f  f_max=%.3f  墙上%.0fs'
                  % (k, nstep, Eb, Es, Ec, Eb + Es + Ec, g.n_unlike(),
                     1 - frac.sum(), frac.max(), time.time() - t0), flush=True)
        if k == nstep:
            break
        g.sweep(rng, nsel=nsel)
        if k % 10 == 9:                      # 每 10 遍加一批"整域换标签"的集体移动
            g.sweep_domain(rng, ntry=20, allow_parent=False)
        if k % 40 == 39:                     # 每 40 遍做一次"整族消除"的全局重排
            g.sweep_global(rng, ntest=2, allow_parent=False)
    g.save(tag)
    np.save(os.path.join(OUT, 'hist%s.npy' % tag), np.array(hist))
    with open(os.path.join(OUT, 'geom%s.txt' % tag), 'w') as fh:
        do_geometry(g.lab, dx, eps0, C, tag, fh)
        try:
            shape_stats(g.lab, dx, eps0, C, fh)
        except Exception as exc:
            fh.write('  [shape_stats 失败] %s\n' % exc)
    print(open(os.path.join(OUT, 'geom%s.txt' % tag)).read())
    return g


if __name__ == '__main__':
    kw = {}
    for a in sys.argv[1:]:
        k, v = a.split('=')
        try:
            kw[k] = int(v)
        except ValueError:
            try:
                kw[k] = float(v)
            except ValueError:
                kw[k] = v
    main(**kw)
