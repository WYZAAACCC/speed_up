#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r400_viz.py —— 把块与块内板条**画出来**：三维等轴视图 + 二维斜切面 + 生长过程。

## 环境约束（已探明）
* 只有 `numpy / matplotlib / scipy`；**没有** vtk/pyvista/mayavi/skimage
  ⇒ 三维**自己实现**：降采样 + 暴露面多边形 + 画家算法（远→近）+ 面法向着色。
* **matplotlib 里没有中文字体** ⇒ 图内文字一律用**英文**（避免豆腐块）。

## 口径
* 颜色：**6 个变体 6 种色相**；同一变体的**两根板条**用同色相、不同明度
  ⇒ **块内板条堆叠一眼可见**。
* 切面：块沿 **(1,1,1) 对角线**排开 ⇒ 用过盒心、由
  @@u_1=(1,1,1)/\\sqrt3@@ 与 @@u_2=(1,-1,0)/\\sqrt2@@ 张成的**斜切面**（一次切到全部 6 块）。
* 三维：把 `region` 按 `--ds` 降采样（取块内**非零众数**，保薄结构）后画面。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
DX_NM = 62.5
U1 = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
U2 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)


# --------------------------------------------------------------------------- #
def snaps(tag):
    d = os.path.join(MB, 'dry_' + tag)
    return sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                  key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))


def load(f):
    z = np.load(f, allow_pickle=True)
    reg = np.asarray(z['region'], np.int64)
    vk = np.asarray(z['vmap_keys'], np.int64)
    vv = np.asarray(z['vmap_vals'], np.int64)
    var = {int(a): int(b) for a, b in zip(vk, vv)}
    return reg, var, int(z['N']), int(z['step'])


def palette(var, maxf):
    """6 变体 → 6 色相；同变体的两根板条用不同明度。返回 {场: RGBA}."""
    vs = sorted(set(var.values()))
    hue = {v: i for i, v in enumerate(vs)}
    base = plt.get_cmap('tab10')
    seen = {}
    out = {}
    for k in range(1, maxf + 1):
        v = var.get(k)
        if v is None:
            continue
        c = np.array(base(hue[v] % 10))
        n = seen.get(v, 0)
        seen[v] = n + 1
        f = 1.0 if n == 0 else 0.55           # 第二根同变体板条调暗
        rgb = 1.0 - (1.0 - c[:3]) * f
        out[k] = np.clip(np.concatenate([rgb, [1.0]]), 0, 1)
    return out


def oblique(reg, org_cell, u1, u2, half_cells=78):
    """过 `org_cell`、张成 `u1,u2` 的斜切面（最近邻采样）。返回 (M,M) 场号图。"""
    N = reg.shape[0]
    m = np.arange(-half_cells, half_cells)
    P = (org_cell[None, None, :]
         + m[:, None, None] * u1[None, None, :]
         + m[None, :, None] * u2[None, None, :])
    I = np.rint(P).astype(int)
    ok = np.all((I >= 0) & (I < N), -1)
    out = np.zeros((len(m), len(m)), np.int64)     # ⚠ 必须二维（第一版写成 m.shape=一维）
    ii = np.clip(I, 0, N - 1)
    out[ok] = reg[ii[..., 0][ok], ii[..., 1][ok], ii[..., 2][ok]]
    out[~ok] = -1
    return out


def window(reg, u1, u2, margin=10):
    """转变区在 (u1,u2) 平面上的投影窗口 ⇒ 用它裁切面，让块填满画面。"""
    ii = np.argwhere(reg > 0).astype(float)
    if ii.size == 0:
        return None
    a = ii @ u1
    b = ii @ u2
    c = np.array([reg.shape[0] / 2.0] * 3)
    c0 = np.array([c @ u1, c @ u2])
    return (int(a.min() - c0[0]) - margin, int(a.max() - c0[0]) + margin,
            int(b.min() - c0[1]) - margin, int(b.max() - c0[1]) + margin)


def draw_slice(ax, sl, pal, title):
    from matplotlib.colors import ListedColormap, BoundaryNorm
    n = max(pal) if pal else 1
    cmap = np.zeros((n + 2, 4))
    cmap[0] = [0.93, 0.93, 0.96, 1]           # 母相
    cmap[1] = [1, 1, 1, 0]                    # -1（盒外）= 透明
    for k, c in pal.items():
        cmap[k + 1] = c
    ax.imshow(sl + 1, origin='lower', interpolation='nearest',
              cmap=ListedColormap(cmap), vmin=0, vmax=n + 1)
    ax.set_title(title, fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])


def render3d(reg, pal, ax, ds=4, elev=22.0, azim=-58.0, bg='white'):
    """自实现的体素三维渲染（暴露面 + 画家算法 + 着光）。"""
    N = reg.shape[0]
    n = N // ds
    sub = reg[:n * ds, :n * ds, :n * ds].reshape(n, ds, n, ds, n, ds)
    sub = sub.transpose(0, 2, 4, 1, 3, 5).reshape(n * n * n, ds ** 3)
    nz = sub > 0
    cnt = np.zeros(sub.shape[0], np.int64)
    mode = np.zeros(sub.shape[0], np.int64)
    for k in np.unique(sub[nz]):
        m = (sub == k).sum(1)
        upd = m > cnt
        mode[upd] = k
        cnt[upd] = m[upd]
    cube = mode.reshape(n, n, n)
    occ = (cube > 0)
    if not occ.any():
        ax.set_axis_off(); return
    A, B, C = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing='ij')
    vidx = np.argwhere(occ)
    val = cube[occ]
    # 视角基
    e, a = np.radians(elev), np.radians(azim)
    fwd = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up0 = np.array([0, 0, 1.0])
    right = np.cross(up0, fwd); right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    light = (fwd + up * 0.6 + right * 0.4)
    light /= np.linalg.norm(light)
    FACES = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
             ((-1, 0, 0), [(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)]),
             ((0, 1, 0), [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)]),
             ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
             ((0, 0, -1), [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)])]
    polys, cols, depth = [], [], []
    for fdir, corners in FACES:
        nd = np.array(fdir, float)
        if nd @ fwd > -1e-9:
            continue
        nb = vidx + np.array(fdir)
        inb = np.all((nb >= 0) & (nb < n), axis=1)
        exposed = np.ones(len(vidx), bool)
        ok = inb
        exposed[ok] = (~occ[nb[ok, 0], nb[ok, 1], nb[ok, 2]]) | \
                      (cube[nb[ok, 0], nb[ok, 1], nb[ok, 2]] != val[ok])
        sel = np.where(exposed)[0]
        shade = 0.55 + 0.45 * float(np.clip(nd @ light, 0.0, 1.0))
        for i in sel:
            p0 = vidx[i].astype(float)
            pts = np.array([p0 + np.array(c, float) for c in corners])
            depth.append(float((p0 + 0.5) @ fwd))
            polys.append(pts)
            c = pal.get(int(val[i]), np.array([0.5, 0.5, 0.5, 1.0]))
            cols.append(np.clip(np.concatenate([c[:3] * shade, [1.0]]), 0, 1))
    if not polys:
        ax.set_axis_off(); return
    order = np.argsort(depth)[::-1]
    proj = []
    for i in order:
        p = polys[i]
        proj.append(np.stack([p @ right, p @ up], -1))
    pc = PolyCollection(proj, facecolors=[cols[i] for i in order],
                        edgecolors=[cols[i] for i in order], linewidths=0.15,
                        antialiased=False)
    ax.add_collection(pc)
    allp = np.concatenate(proj, 0)
    ax.set_xlim(allp[:, 0].min(), allp[:, 0].max())
    ax.set_ylim(allp[:, 1].min(), allp[:, 1].max())
    ax.set_aspect('equal'); ax.set_axis_off()
    ax.set_facecolor(bg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', default='saSet2P0')
    ap.add_argument('--outdir', default=os.path.join(HERE, '_viz'))
    ap.add_argument('--nsteps', type=int, default=8)
    ap.add_argument('--ds', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    fs = snaps(a.arm)
    if not fs:
        print('⚠ 无快照'); return 2
    sel = [fs[i] for i in np.linspace(0, len(fs) - 1, a.nsteps).astype(int)]
    reg0, var, N, _ = load(fs[0])
    pal = palette(var, int(reg0.max()))

    # ---------- 图 1：生长过程（斜切面，**固定窗口 = 末态**） ----------
    org = np.array([N / 2.0] * 3)
    half = 110
    grid = np.arange(-half, half)
    # ★ 关键：窗口**只按末快照算一次**，所有面板共用
    #   （第一版每面板各自裁切 ⇒ 每格都缩放到自己大小 ⇒ **生长看不出来**）
    regL, _, _, _ = load(sel[-1])
    wfix = window(regL, U1, U2, margin=14)
    print('  固定窗口（按末快照）：%s' % (wfix,))
    fig, axes = plt.subplots(2, a.nsteps // 2, figsize=(3.4 * (a.nsteps // 2), 7.6))
    for ax, f in zip(axes.ravel(), sel):
        reg, _, _, st = load(f)
        sl = oblique(reg, org, U1, U2, half)
        if wfix is not None:
            i0 = max(np.searchsorted(grid, wfix[0]), 0)
            i1 = np.searchsorted(grid, wfix[1])
            j0 = max(np.searchsorted(grid, wfix[2]), 0)
            j1 = np.searchsorted(grid, wfix[3])
            sl = sl[i0:i1, j0:j1]
        draw_slice(ax, sl, pal, 'step %d' % st)
    fig.suptitle('%s   oblique slice, FIXED window (from the last frame)   '
                 'u1=(1,1,1) along the block chain, u2=(1,-1,0)' % a.arm,
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p1 = os.path.join(a.outdir, '%s_slices_growth.png' % a.arm)
    fig.savefig(p1, dpi=130); plt.close(fig)
    print('  写出 %s' % p1)

    # ---------- 图 2：三维（同样的时刻） ----------
    n3 = min(6, len(sel))
    sel3 = [sel[i] for i in np.linspace(0, len(sel) - 1, n3).astype(int)]
    fig = plt.figure(figsize=(3.6 * n3, 4.2))
    for i, f in enumerate(sel3):
        reg, _, _, st = load(f)
        ax = fig.add_subplot(1, n3, i + 1)
        render3d(reg, pal, ax, ds=a.ds)
        ax.set_title('step %d' % st, fontsize=10)
    # 图例：变体 → 颜色
    vs = sorted(set(var.values()))
    hs = []
    for v in vs:
        kk2 = [k for k in pal if var.get(k) == v]
        hs.append(plt.Line2D([], [], marker='s', ls='', ms=8,
                             color=pal[kk2[0]],
                             label='V%d (fields %s)' % (v, kk2)))
    fig.legend(handles=hs, loc='lower center', ncol=len(vs), fontsize=9,
               frameon=False)
    fig.suptitle('%s   3D voxel view (downsample %d; two laths of a variant '
                 'share the hue, 2nd is darker)' % (a.arm, a.ds), fontsize=12)
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])
    p2 = os.path.join(a.outdir, '%s_3d_growth.png' % a.arm)
    fig.savefig(p2, dpi=130, facecolor='white'); plt.close(fig)
    print('  写出 %s' % p2)

    # ---------- 图 3：单个块的板条堆叠特写 ----------
    reg, _, _, st = load(sel[-1])
    # 取胞数最多的那个块（同变体、连通）—— 简化：取同一变体里胞数最多的场
    cnt = {k: int((reg == k).sum()) for k in range(1, int(reg.max()) + 1)}
    kk = max(cnt, key=cnt.get)
    vk_ = var[kk]
    sib = [k for k in var if var[k] == vk_]
    ii = np.argwhere(np.isin(reg, sib))
    lo, hi = ii.min(0) - 4, ii.max(0) + 5
    lo = np.maximum(lo, 0); hi = np.minimum(hi, N)
    sub = reg[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    print('  特写块：变体 %d，场 %s；子盒 %s' % (vk_, sib, sub.shape))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    for ax, (ax_i, lab) in zip(axes, ((0, 'x'), (1, 'y'), (2, 'z'))):
        mid = sub.shape[ax_i] // 2
        sl = np.take(sub, mid, axis=ax_i)
        draw_slice(ax, sl.T if ax_i != 2 else sl,
                   pal, 'variant %d laths %s : %s=%d' % (vk_, sib, lab, mid))
    fig.suptitle('%s  step %d  close-up of one block (variant %d, %d laths)'
                 % (a.arm, st, vk_, len(sib)), fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p3 = os.path.join(a.outdir, '%s_block_closeup.png' % a.arm)
    fig.savefig(p3, dpi=140); plt.close(fig)
    print('  写出 %s' % p3)
    return 0


if __name__ == '__main__':
    sys.exit(main())
