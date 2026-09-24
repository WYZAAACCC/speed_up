#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fig_meltpool_3d.py --- 演示三维图（软件体素渲染器；读 npz，不重跑 CA）

本环境无 VTK/PyVista/Plotly，mplot3d 对上千小面片的深度排序又会画成"梳齿"。
故自己做【画家算法 + 正交投影】：
  面片 = ① 晶粒-空 的外表面（半透明盒壳） ② 相邻【不同】晶粒的共享面（实心深色 = 晶界）
  按相机深度从远到近排序后填充 ⇒ 透明壳内的晶界可被看穿且层次正确。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.collections import PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/mnt/c/Windows/Fonts/simhei.ttf"
if os.path.exists(FONT):
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False

DOWN = 2
SHELL_ALPHA = 0.09
SL_COLOR = (0.20, 0.55, 0.95)
SL_ALPHA = 0.45
GB_DARK = 0.72
SH_SIDE = 0.80


def load():
    d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    return d["gid"][::DOWN, ::DOWN, ::DOWN], float(d["dx"]) * DOWN


def _quad(plane, axis, dx):
    a, b, c = plane
    if axis == 0:
        pts = [(a, b, c), (a, b + 1, c), (a, b + 1, c + 1), (a, b, c + 1)]
    elif axis == 1:
        pts = [(a, b, c), (a + 1, b, c), (a + 1, b, c + 1), (a, b, c + 1)]
    else:
        pts = [(a, b, c), (a + 1, b, c), (a + 1, b + 1, c), (a, b + 1, c)]
    return [(x * dx, y * dx, z * dx) for (x, y, z) in pts]


def _idx(axis, i, u, v):
    """把 (沿轴 i, 另两轴 u,v) 组装成 (nx,ny,nz) 索引。axis=0 -> (i,u,v) 等。"""
    if axis == 0:
        return (i, u, v)
    if axis == 1:
        return (u, i, v)
    return (u, v, i)


def faces(g, dx):
    nx, ny, nz = g.shape
    P, GI, KIND, NRM = [], [], [], []
    for axis in range(3):
        n = g.shape[axis]
        for i in range(n):
            for step in (-1, +1):
                j = i + step
                if j < 0 or j >= n:
                    continue
                if step == -1 and axis >= 0:
                    pass
                cells = np.arange(np.prod([g.shape[k] for k in range(3) if k != axis])).reshape(
                    [g.shape[k] for k in range(3) if k != axis])
                sl_s = [slice(None)] * 3; sl_s[axis] = i
                sl_n = [slice(None)] * 3; sl_n[axis] = j
                a = g[tuple(sl_s)]
                b = g[tuple(sl_n)]
                gb = (a > 0) & (b > 0) & (b != a)
                if gb.any() and step == +1:
                    gb = np.zeros_like(gb)           # 晶界面片只从低索引侧出一次，避免 z-fighting
                if gb.any():
                    uu, vv = np.where(gb)
                    for t in range(len(uu)):
                        c = _idx(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        nv = [0.0, 0.0, 0.0]
                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(1); NRM.append(nv)
                sl = (a > 0) & (b == 0)
                if sl.any():
                    uu, vv = np.where(sl)
                    for t in range(len(uu)):
                        c = _idx(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        nv = [0.0, 0.0, 0.0]
                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(2); NRM.append(nv)
    # ---- 域外边界盒壳（末态全固相 => 域内没有"固-空"面，必须单独补）----
    for axis in range(3):
        n = g.shape[axis]
        for i, plane_at in ((0, 0), (n - 1, n)):
            sl = [slice(None)] * 3; sl[axis] = i
            a = g[tuple(sl)]
            m = a > 0
            if not m.any():
                continue
            uu, vv = np.where(m)
            for t in range(len(uu)):
                c = _idx(axis, i, uu[t], vv[t])
                plane = list(c); plane[axis] = plane_at
                P.append(_quad(plane, axis, dx))
                nv = [0.0, 0.0, 0.0]
                nv[axis] = -1.0 if plane_at == 0 else 1.0
                GI.append(int(a[uu[t], vv[t]])); KIND.append(0); NRM.append(nv)
    return (np.array(P, float), np.array(GI, int), np.array(KIND, int),
            np.array(NRM, float))


def render(fname, g, dx, cmap, norm, elev=22.0, azim=-58.0, gb_only=False,
           title="", figsize=(9.2, 7.4), dpi=160, crop=None, cull_front=True,
           legend=True, shell_alpha=SHELL_ALPHA):
    g0 = g
    if crop is not None:
        (z0, z1), (y0, y1), (x0, x1) = crop
        g = g[x0:x1, y0:y1, z0:z1]
    P, GI, KIND, NRM = faces(g, dx)
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    if cull_front:
        front = (NRM @ d) > 1e-9
        keep = ~((KIND == 0) & front)
        P, GI, KIND, NRM = P[keep], GI[keep], KIND[keep], NRM[keep]
    if gb_only:
        m = KIND == 1
        P, GI, KIND, NRM = P[m], GI[m], KIND[m], NRM[m]
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(d, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, d)
    flat = P.reshape(-1, 3)
    sx = (flat @ right).reshape(-1, 4)
    sy = (flat @ up2).reshape(-1, 4)
    dep = (flat @ d).reshape(-1, 4).mean(axis=1)
    order = np.argsort(dep)
    polys, cols = [], []
    for k in order:
        c = cmap(norm(GI[k]))
        if gb_only or KIND[k] == 1:
            cols.append((c[0] * GB_DARK, c[1] * GB_DARK, c[2] * GB_DARK, 1.0))
        elif KIND[k] == 2:
            cols.append((SL_COLOR[0], SL_COLOR[1], SL_COLOR[2], SL_ALPHA))
        else:
            cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, shell_alpha))
        polys.append(list(zip(sx[k], sy[k])))
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="none", linewidths=0))
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
    if title:
        ax.set_title(title, fontsize=12)
    if legend and not gb_only:
        from matplotlib.patches import Patch
        ng_ = int(g0.max())
        tot = float((g0 > 0).sum())
        hs = []
        for gid in range(1, ng_ + 1):
            frac = 100.0 * float((g0 == gid).sum()) / tot
            hs.append(Patch(facecolor=cmap(norm(gid)),
                            label="gid %d   %4.2f%%" % (gid, frac)))
        ax.legend(handles=hs, loc="upper left", fontsize=9, framealpha=0.85,
                  title="晶粒（体积占比）")
    fig.tight_layout(); fig.savefig(fname, dpi=dpi); plt.close(fig)
    print("saved", fname, " 面片", len(polys))


def growth_3d(snaps, ts, dx, cmap, norm, crop=None, elev=22.0, azim=-58.0):
    """生长过程三维序列。视口可裁到熔池附近；剔除朝向相机的近侧壳面（切开看内部）。"""
    n = len(snaps); ncol = 3; nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.6 * ncol, 4.8 * nrow))
    axes = np.atleast_1d(axes).ravel()
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(d, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, d)
    for k in range(n):
        g = snaps[k][::DOWN, ::DOWN, ::DOWN]
        if crop is not None:
            (z0, z1), (y0, y1), (x0, x1) = crop
            g = g[x0:x1, y0:y1, z0:z1]
        P, GI, KIND, NRM = faces(g, dx)
        keep = ~((KIND == 0) & ((NRM @ d) > 1e-9))
        P, GI, KIND, NRM = P[keep], GI[keep], KIND[keep], NRM[keep]
        flat = P.reshape(-1, 3)
        sx = (flat @ right).reshape(-1, 4); sy = (flat @ up2).reshape(-1, 4)
        dep = (flat @ d).reshape(-1, 4).mean(axis=1)
        order = np.argsort(dep)
        polys, cols = [], []
        for q in order:
            c = cmap(norm(GI[q]))
            if KIND[q] == 1:
                cols.append((c[0] * GB_DARK, c[1] * GB_DARK, c[2] * GB_DARK, 1.0))
            elif KIND[q] == 2:
                cols.append((SL_COLOR[0], SL_COLOR[1], SL_COLOR[2], SL_ALPHA))
            else:
                cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, 0.30))
            polys.append(list(zip(sx[q], sy[q])))
        ax = axes[k]
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="none", linewidths=0))
        ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
        liq = float((g == 0).sum()) / float(g.size)
        ax.set_title("t = {:.2e} s   液相占【视口】{:.1f}%".format(ts[k], 100 * liq), fontsize=11)
    for k in range(n, len(axes)):
        axes[k].axis("off")
    fig.suptitle("熔池底部外延生长【过程】三维序列（已裁到熔池附近；剔近侧壳面以看内部）："
                 "蓝色=液态熔池，彩色实心面=晶界", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(HERE, "FIG_meltpool_growth_3d.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("saved", p)


def main():
    g, dx = load()
    ng = int(g.max())
    base = plt.get_cmap("tab20")
    cols = [(1.0, 1.0, 1.0, 1.0)] + [base((2 * (i - 1)) % 20) for i in range(1, ng + 1)]
    cmap = ListedColormap(cols); norm = BoundaryNorm(np.arange(-0.5, ng + 1.5), ng + 1)
    print("网格 {} (抽稀 {}x, 胞 {:.0f} um)  晶粒 {} 个".format(g.shape, DOWN, dx * 1e6, ng))
    d0 = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    crop = None
    if "snaps" in d0:
        s0 = d0["snaps"][0][::DOWN, ::DOWN, ::DOWN]
        ii, jj, kk = np.where(s0 == 0)
        m = 3          # 余量 3 个粗胞 = 18 um（太大则熔池在视口里占比过小）
        nx, ny, nz = s0.shape
        crop = ((max(0, kk.min() - m), min(nz, kk.max() + 1 + m)),
                (max(0, jj.min() - m), min(ny, jj.max() + 1 + m)),
                (max(0, ii.min() - m), min(nx, ii.max() + 1 + m)))
        box = (crop[2][1] - crop[2][0]) * dx * 1e6, (crop[1][1] - crop[1][0]) * dx * 1e6, \
              (crop[0][1] - crop[0][0]) * dx * 1e6
        vf = float((s0 == 0).sum()) / float((crop[2][1]-crop[2][0])*(crop[1][1]-crop[1][0])*(crop[0][1]-crop[0][0]))
        print("裁剪框 = {:.0f} x {:.0f} x {:.0f} um（熔池 + 18um 余量）; 其中首帧液相占 {:.1f}%".format(
            box[0], box[1], box[2], 100 * vf))
    render(os.path.join(HERE, "FIG_meltpool_final_3d.png"), g, dx, cmap, norm, elev=22, azim=-58,
           crop=crop, shell_alpha=0.34,
           title="最终三维：prior-beta 晶粒（壳半透明，按 gid 着色）+ 晶界（实心面片）；已切开近侧壳面")
    render(os.path.join(HERE, "FIG_meltpool_gb_network_3d.png"), g, dx, cmap, norm, elev=22,
           azim=-58, gb_only=True,
           title="晶界网络单独视图（相邻晶粒的共享面片，按晶粒身份着色）")
    d2 = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    if "snaps" in d2:
        growth_3d(d2["snaps"], d2["snap_t"], dx, cmap, norm, crop=crop)


if __name__ == "__main__":
    main()