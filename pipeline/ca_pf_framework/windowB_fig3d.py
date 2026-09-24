#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_fig3d.py --- 三维 RVE 结果的检查与出图
用法: python windowB_fig3d.py tag=_quick
输出: bench/windowB_rve3d/分析文本 + FIG_rve3d_<tag>_slices.png + FIG_rve3d_<tag>_3d.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D  # noqa

OUT = '/mnt/f/speed_up/bench/windowB_rve3d'
FONT = '/mnt/c/Windows/Fonts/simhei.ttf'


def analyse(phi, dx, tag, fh):
    nv, N = phi.shape[0], phi.shape[1]
    s = phi.sum(0)
    dom = np.argmax(phi, 0)                 # 0..nv-1; 用 s 判断是否转变
    trans = s > 0.5
    pure = (phi.max(0) > 0.9)
    fh.write('  N=%d  dx=%.1f nm\n' % (N, dx * 1e9))
    fh.write('  Sum(phi): min=%.4f mean=%.4f max=%.4f\n' % (s.min(), s.mean(), s.max()))
    fh.write('  已转变体积分数 = %.4f ; 其中"纯"(max_phi>0.9) 占比 = %.4f\n'
             % (trans.mean(), (trans & pure).sum() / max(trans.sum(), 1)))
    fh.write('  全局 max(phi) = %.4f ; 已转变胞的 max(phi) 均值 = %.4f\n'
             % (phi.max(), phi.max(0)[trans].mean() if trans.any() else np.nan))
    frac = phi.reshape(nv, -1).mean(1)
    fh.write('  各变体体积分数: %s\n' % np.round(frac, 4))
    fh.write('  最大/最小变体分数比 = %.2f (1.0 = 完全均分)\n'
             % (frac.max() / max(frac.min(), 1e-12)))
    # 结构因子 -> 特征板条周期（沿各轴平均）
    k = 2 * np.pi * np.fft.fftfreq(N, d=dx)
    kmag = np.sqrt(k[:, None, None] ** 2 + k[None, :, None] ** 2 + k[None, None, :] ** 2)
    P = np.zeros(N // 2)
    for v in range(nv):
        ph = np.fft.fftn(phi[v]) / N ** 3
        pw = np.abs(ph) ** 2
        pw[0, 0, 0] = 0
        kb = np.round(kmag / (2 * np.pi / (N * dx))).astype(int).ravel()
        S = np.bincount(kb, weights=pw.ravel(), minlength=N // 2 + 1)
        P += S[1:N // 2 + 1]
    nz = np.where(P > 0)[0]
    if len(nz):
        imax = int(nz[np.argmax(P[nz])]) + 1
        Lam = N * dx / imax
        fh.write('  结构因子峰 => 特征周期 ~ %.1f nm (峰在 %d 个胞)\n' % (Lam * 1e9, imax))
    return frac, dom, trans


def fig_slices(phi, dx, tag, path):
    nv, N = phi.shape[0], phi.shape[1]
    s = phi.sum(0)
    dom = np.argmax(phi, 0)
    disp = np.where(s > 0.5, dom, nv)          # nv = 母相
    cmap = ListedColormap(list(plt.get_cmap('tab20').colors[:nv]) +
                          [(0.85, 0.85, 0.85, 1.0)])
    norm = BoundaryNorm(np.arange(-0.5, nv + 1.5), nv + 1)
    mid = N // 2
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 5.2))
    for ax, (sl, ttl) in zip(axs, [(disp[mid], 'xy 面 (z=中点)'),
                                   (disp[:, mid, :], 'xz 面 (y=中点)'),
                                   (disp[:, :, mid], 'yz 面 (x=中点)')]):
        im = ax.imshow(sl.T, origin='lower', cmap=cmap, norm=norm, interpolation='nearest',
                       extent=[0, N * dx * 1e6, 0, N * dx * 1e6])
        ax.set_title(ttl, fontsize=11)
        ax.set_xlabel('um'); ax.set_ylabel('um')
    handles = [Patch(facecolor=cmap.colors[v], label='variant %d' % (v + 1)) for v in range(nv)]
    handles.append(Patch(facecolor=cmap.colors[nv], label='parent (beta)'))
    fig.legend(handles=handles, loc='lower center', ncol=7, fontsize=8, frameon=False)
    fig.suptitle('Window B 3D RVE: dominant variant on mid-planes  (dx=%.0f nm, 域=%.2f um)'
                 % (dx * 1e9, N * dx * 1e6), fontsize=12)
    fig.tight_layout(rect=[0, 0.08, 1, 0.96])
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_3d(phi, dx, tag, path, topk=6, stride=1, ax_um=None):
    """三维: 按【主变体】着色的半透明体素云（只看关心区域 = 只画被关心的变体）"""
    nv, N = phi.shape[0], phi.shape[1]
    s = phi.sum(0)
    dom = np.argmax(phi, 0)
    dom = np.where(s > 0.5, dom, -1)
    frac = np.array([phi[v].mean() for v in range(nv)])       # 体积分数按 phi 积分
    order = np.argsort(-frac)[:topk]
    x = (np.arange(N) + 0.5) * dx * 1e6
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    fig = plt.figure(figsize=(11.5, 9.5))
    ax = fig.add_subplot(111, projection='3d')
    cols = plt.get_cmap('tab20').colors
    for v in order:
        m = (dom == v)
        if m.sum() == 0:
            continue
        xs, ys, zs = X[m][::stride], Y[m][::stride], Z[m][::stride]
        ax.scatter(xs, ys, zs, s=3.5, c=[cols[v]], alpha=0.45, linewidths=0)
    if ax_um is not None:
        ax.set_xlim(*ax_um); ax.set_ylim(*ax_um); ax.set_zlim(*ax_um)
    ax.set_xlabel('um'); ax.set_ylabel('um'); ax.set_zlabel('um')
    ax.set_title('Window B 3D RVE: dominant variant, top %d (semi-transparent)' % topk,
                 fontsize=11)
    ax.view_init(elev=24, azim=38)
    handles = []
    for v in order:
        handles.append(Patch(facecolor=cols[v], alpha=0.6,
                             label='V%d (f=%.3f)' % (v + 1, frac[v])))
    fig.legend(handles=handles, loc='lower right', fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(tag=''):
    # dx 由 tag 决定（不要用猜的：曾把 dx=1nm 的算例按 10nm 解读）
    if 'dx1nm' in tag:
        dx = 1.0e-9
    elif 'dx2nm' in tag:
        dx = 2.0e-9
    elif 'quick' in tag:
        dx = 2.0e-8
    elif 'free' in tag:
        dx = 2.0e-9
    else:
        dx = 1.0e-8
    phi = np.load(os.path.join(OUT, 'phi_final%s.npy' % tag))
    txt = os.path.join(OUT, 'analysis%s.txt' % tag)
    with open(txt, 'w') as fh:
        fh.write('Window B 3D RVE 分析 (tag=%s)\n' % tag)
        frac, dom, trans = analyse(phi, dx, tag, fh)
    print(open(txt).read())
    fig_slices(phi, dx, tag, os.path.join(OUT, 'FIG_rve3d%s_slices.png' % tag))
    fig_3d(phi, dx, tag, os.path.join(OUT, 'FIG_rve3d%s_3d.png' % tag),
           stride=3 if phi.shape[1] > 80 else 2)
    print('图: %s/FIG_rve3d%s_slices.png , FIG_rve3d%s_3d.png' % (OUT, tag, tag))


if __name__ == '__main__':
    tg = ''
    for a in sys.argv[1:]:
        if a.startswith('tag='):
            tg = a[4:]
    main(tg)
