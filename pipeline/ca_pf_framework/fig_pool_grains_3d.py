#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fig_pool_grains_3d.py --- 只看【熔池内部】的晶粒三维形状

用户要求（2026-09-23）：
  * 只关注熔池内部的晶粒形状，不要整个计算盒
  * 每个晶粒用【不同颜色的半透明三维体】显示，能看出彼此区别与三维形状
  * 精度高一点

做法：
  1. 用【首帧的液相掩膜】(snaps[0]==0) 定义熔池体积（= 激光关掉那一刻的液池），
     并向外膨胀 DIL 个胞（否则晶粒表面正好被池面切掉、看不到外皮）
  2. 在这个掩膜内取末态 gid，抽面片：
       · 晶粒-晶粒（不同 gid）-> 晶界面，画得浓一些（不透明、深一档）
       · 晶粒-掩膜外          -> 池面/切面，画成该晶粒色的半透明外皮
  3. 画家算法（远->近）正交投影；每个面片加细描边 => 形状清楚、不糊
  4. 全分辨率（DOWN=1, dx=3um），不抽稀
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/mnt/c/Windows/Fonts/simhei.ttf"
if os.path.exists(FONT):
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False

DIL = 2                 # 池掩膜向外膨胀的胞数（0 = 严格只画池内）
ALPHA_SKIN = 0.30       # 池面/切面（晶粒外皮）
ALPHA_GB = 0.85         # 晶界面
EDGE_W = 0.25

PALETTE = [(0.85, 0.20, 0.15), (0.15, 0.62, 0.25), (0.20, 0.42, 0.88),
           (0.95, 0.55, 0.10), (0.55, 0.25, 0.72), (0.10, 0.62, 0.62),
           (0.60, 0.45, 0.15), (0.85, 0.30, 0.60)]


def dilate(m, n):
    out = m.copy()
    for _ in range(n):
        a = out.copy()
        for ax in range(3):
            for s in (+1, -1):
                sl = [slice(None)] * 3; ds = [slice(None)] * 3
                sl[ax] = slice(None, -1) if s > 0 else slice(1, None)
                ds[ax] = slice(1, None) if s > 0 else slice(None, -1)
                a[tuple(ds)] |= out[tuple(sl)]
        out = a
    return out


def _quad(plane, axis, dx):
    a, b, c = plane
    if axis == 0:
        p = [(a, b, c), (a, b + 1, c), (a, b + 1, c + 1), (a, b, c + 1)]
    elif axis == 1:
        p = [(a, b, c), (a + 1, b, c), (a + 1, b, c + 1), (a, b, c + 1)]
    else:
        p = [(a, b, c), (a + 1, b, c), (a + 1, b + 1, c), (a, b + 1, c)]
    return [(x * dx, y * dx, z * dx) for (x, y, z) in p]


def _idx3(axis, i, u, v):
    if axis == 0:
        return (i, u, v)
    if axis == 1:
        return (u, i, v)
    return (u, v, i)


def faces_masked(g, mask, dx):
    """在 mask 内取面片。返回 P[N,4,3], GI[N], ISGB[N]"""
    gg = np.where(mask, g, 0)
    P, GI, ISGB = [], [], []
    nx, ny, nz = g.shape
    for axis in range(3):
        n = g.shape[axis]
        for i in range(n):
            for step in (+1, -1):
                j = i + step
                if j < 0 or j >= n:
                    continue
                sl = [slice(None)] * 3; sn = [slice(None)] * 3
                sl[axis] = i; sn[axis] = j
                a = gg[tuple(sl)]; b = gg[tuple(sn)]
                gbm = (a > 0) & (b > 0) & (b != a)
                if gbm.any() and step == +1:
                    gbm = np.zeros_like(gbm)
                sk = (a > 0) & (b == 0)
                for m, isgb in ((gbm, True), (sk, False)):
                    if not m.any():
                        continue
                    uu, vv = np.where(m)
                    for t in range(len(uu)):
                        c = _idx3(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        P.append(_quad(plane, axis, dx))
                        GI.append(int(g[c])); ISGB.append(isgb)
    return np.array(P, float), np.array(GI, int), np.array(ISGB, bool)


def draw(ax, P, GI, ISGB, cmap, elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(d, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, d)
    flat = P.reshape(-1, 3)
    sx = (flat @ right).reshape(-1, 4); sy = (flat @ up2).reshape(-1, 4)
    dep = (flat @ d).reshape(-1, 4).mean(axis=1)
    order = np.argsort(dep)
    polys, fc, ec = [], [], []
    for k in order:
        c = np.array(cmap(GI[k]))
        if ISGB[k]:
            col = (c * 0.80, ALPHA_GB)
        else:
            col = (c, ALPHA_SKIN)
        polys.append(list(zip(sx[k], sy[k])))
        fc.append((col[0][0], col[0][1], col[0][2], col[1]))
        ec.append((c[0] * 0.45, c[1] * 0.45, c[2] * 0.45, 0.9))
    ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors=ec, linewidths=EDGE_W))
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")


def main():
    d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    g = d["gid"]; dx = float(d["dx"]); s0 = d["snaps"][0]
    pool = (s0 == 0)
    pin = dilate(pool, DIL)
    print("熔池胞(首帧液相) = %d (%.2f%% 全域); 膨胀 %d 胞后 = %d" % (
        int(pool.sum()), 100.0 * pool.mean(), DIL, int(pin.sum())))
    ng = int(g.max())
    cmap = lambda i: PALETTE[(i - 1) % len(PALETTE)]
    P, GI, ISGB = faces_masked(g, pin, dx)
    print("掩膜内面片: 共 %d (晶界 %d, 池面 %d)" % (len(P), int(ISGB.sum()), int((~ISGB).sum())))
    tot = 0
    frac = {}
    for gid in range(1, ng + 1):
        n = int(((g == gid) & pin).sum()); frac[gid] = n; tot += n
    print("池内各晶粒胞数:", "  ".join("gid%d=%d(%.1f%%)" % (k, v, 100.0 * v / tot)
                                       for k, v in frac.items() if v > 0))
    views = [((26, -60), "① 斜视（elev 26°, azim -60°）"),
             ((12, 25), "② 斜视（elev 12°, azim 25°）"),
             ((62, -90), "③ 俯视（elev 62°）"),
             ((-22, -60), "④ 仰视（从池底往上看，正是晶粒长出来的地方）")]
    fig, axes = plt.subplots(2, 2, figsize=(15, 13))
    for (v, t), ax in zip(views, axes.ravel()):
        draw(ax, P, GI, ISGB, cmap, *v)
        ax.set_title(t, fontsize=12)
    hs = [Patch(facecolor=cmap(k), edgecolor="k", label="gid %d   %4.1f%%（池内）" % (k, 100.0 * v / tot))
          for k, v in frac.items() if v > 0]
    fig.legend(handles=hs, loc="lower center", ncol=len(hs), fontsize=11, framealpha=0.9,
               title="熔池内的晶粒（体积占比按【池内】计）")
    fig.suptitle("熔池内部（首帧液相区域，膨胀 %d 胞）的晶粒三维形状：不同晶粒不同颜色半透明；"
                 "浓面 = 晶界，浅面 = 池边界/切面；dx = %.0f um 全分辨率" % (DIL, dx * 1e6),
                 fontsize=13)
    fig.tight_layout(rect=[0, 0.06, 1, 0.95])
    p = os.path.join(HERE, "FIG_pool_grains_3d.png")
    fig.savefig(p, dpi=150); plt.close(fig)
    print("saved", p)


if __name__ == "__main__":
    main()