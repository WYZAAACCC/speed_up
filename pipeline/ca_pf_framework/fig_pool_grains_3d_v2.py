#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fig_pool_grains_3d_v2.py --- 熔池内晶粒的三维体渲染（真 z-buffer、不透明、剖切、光滑法向着色）

用户反馈（2026-09-23）："晶粒难道不应该是一整块吗？为什么小立方体不同面颜色不同、
一个区域内不同颜色的小立方体在交错？"  ==> 是旧版【渲染】的四个缺陷，不是数据问题：
  ① 池面外皮 alpha=0.30 半透明  => 背面晶粒透过来 => 颜色"交错"
  ② 画家算法按面片平均深度排序 => 阶梯面大量深度并列 => 顺序抖动（花斑）
  ③ 晶界面 alpha 0.85 且颜色 x0.8，池面 alpha 0.30
     => 同一个体素既有晶界面又有池面 => "一个小立方体的不同面颜色不同"
  ④ 每个面片描边 => 满屏网格，形状被淹没
数据实测（_diag_gid2.py / _diag_iface.py）：池内每个晶粒 >=99.71% 的胞属于单一 6-连通块。

本版：z-buffer 逐三角形光栅化、不透明、颜色只按晶粒区分；
      明暗用"光滑法向"（对每个晶粒的占位场做高斯模糊再取梯度）=> 同一晶粒连续同色、
      体素阶梯只在轮廓上可见，不会看成棋盘格。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/mnt/c/Windows/Fonts/simhei.ttf"
if os.path.exists(FONT):
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False

GCOL = {1: (0.86, 0.19, 0.14), 2: (0.16, 0.62, 0.26), 3: (0.13, 0.36, 0.86),
        4: (0.93, 0.55, 0.09), 5: (0.62, 0.18, 0.72), 6: (0.05, 0.63, 0.63)}
GB_ALL = (0.32, 0.34, 0.38)
GB_56 = (0.93, 0.42, 0.08)
BG = (1.0, 1.0, 1.0)
SMOOTH_SIGMA = 1.5


def pad_closed(a, val):
    out = np.full(tuple(s + 2 for s in a.shape), val, a.dtype)
    out[1:-1, 1:-1, 1:-1] = a
    return out


def build_faces(g, keep, dx, want_skin=True, want_gb=True, pair=None):
    """kind: 0 = 外皮(keep 与 !keep 之间), 1 = 晶界(两个不同 gid 的 keep 胞之间)
    返回 (P[M,4,3] um, GID[M], KIND[M], CELL[M,3] 归属胞, AXNRM[M,3] 轴向法向)"""
    P, GI, KI, CL, NR = [], [], [], [], []
    for ax in range(3):
        n = g.shape[ax]
        lo = np.arange(n - 1); hi = np.arange(1, n)
        klo = np.take(keep, lo, axis=ax); khi = np.take(keep, hi, axis=ax)
        glo = np.take(g, lo, axis=ax); ghi = np.take(g, hi, axis=ax)
        cases = []
        if want_skin:
            cases.append((klo & ~khi, True, 0, +1))
            cases.append((~klo & khi, False, 0, -1))
        if want_gb:
            m = klo & khi & (glo != ghi)
            if pair is not None:
                m = m & (np.minimum(glo, ghi) == pair[0]) & (np.maximum(glo, ghi) == pair[1])
            cases.append((m, True, 1, +1))
        for sel, low_kept, kind, sgn in cases:
            if not sel.any():
                continue
            ii = np.argwhere(sel)
            M = len(ii)
            gi = (glo if low_kept else ghi)[tuple(ii.T)].astype(np.int32)
            cell = ii.astype(np.float64)
            if not low_kept:
                cell[:, ax] += 1.0
            plane = ii[:, ax].astype(np.float64) + 1.0
            quad = np.empty((M, 4, 3), np.float64)
            o1, o2 = [k for k in range(3) if k != ax]
            u = cell[:, o1]; v = cell[:, o2]
            for t, (du, dv) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
                quad[:, t, o1] = u + du
                quad[:, t, o2] = v + dv
                quad[:, t, ax] = plane
            nrm = np.zeros((M, 3)); nrm[:, ax] = sgn
            P.append(quad * dx); GI.append(gi); KI.append(np.full(M, kind, np.int8))
            CL.append(cell.astype(np.int32)); NR.append(nrm)
    if not P:
        return (np.zeros((0, 4, 3)), np.zeros(0, np.int32), np.zeros(0, np.int8),
                np.zeros((0, 3), np.int32), np.zeros((0, 3)))
    return (np.concatenate(P), np.concatenate(GI), np.concatenate(KI),
            np.concatenate(CL), np.concatenate(NR))


def smoothed_grads(g, keep, sigma=SMOOTH_SIGMA):
    """每个晶粒在 keep 内的占位场 I 的高斯模糊梯度。
    返回 GBLUR[nmax+1, nx, ny, nz, 3]，便于按 (gid, cell) 直接向量化索引"""
    gmax = int(g.max())
    GBLUR = np.zeros((gmax + 1,) + g.shape + (3,), np.float32)
    for gam in np.unique(g[keep]):
        gam = int(gam)
        I = ((g == gam) & keep).astype(np.float64)
        if I.sum() == 0:
            continue
        Ib = gaussian_filter(I, sigma, mode="nearest")
        gz, gy, gx = np.gradient(Ib)
        GBLUR[gam, :, :, :, 0] = gx
        GBLUR[gam, :, :, :, 1] = gy
        GBLUR[gam, :, :, :, 2] = gz
    return GBLUR


def face_normals(CELL, GID, AXNRM, GBLUR):
    """面法向 = -(该晶粒占位场的模糊梯度)，取在归属胞中心 => 光滑着色"""
    n = -GBLUR[GID, CELL[:, 0], CELL[:, 1], CELL[:, 2]].astype(np.float64)
    ln = np.linalg.norm(n, axis=1)
    bad = ln < 1e-9
    n[bad] = AXNRM[bad]
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(ln, 1e-12)


def raster_tri(px, py, pz, col, zbuf, rgb):
    area = (px[1] - px[0]) * (py[2] - py[0]) - (px[2] - px[0]) * (py[1] - py[0])
    if area == 0.0:
        return
    if area < 0:
        px = px[[0, 2, 1]]; py = py[[0, 2, 1]]; pz = pz[[0, 2, 1]]; area = -area
    ix0 = max(int(np.floor(px.min())), 0); ix1 = min(int(np.ceil(px.max())), zbuf.shape[1] - 1)
    iy0 = max(int(np.floor(py.min())), 0); iy1 = min(int(np.ceil(py.max())), zbuf.shape[0] - 1)
    if ix1 < ix0 or iy1 < iy0:
        return
    X, Y = np.meshgrid(np.arange(ix0, ix1 + 1, dtype=np.float64),
                       np.arange(iy0, iy1 + 1, dtype=np.float64))
    w0 = (px[2] - px[1]) * (Y - py[1]) - (py[2] - py[1]) * (X - px[1])
    w1 = (px[0] - px[2]) * (Y - py[2]) - (py[0] - py[2]) * (X - px[2])
    w2 = (px[1] - px[0]) * (Y - py[0]) - (py[1] - py[0]) * (X - px[0])
    ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not ins.any():
        return
    z = (w0 * pz[0] + w1 * pz[1] + w2 * pz[2]) / area
    zf = np.where(ins, z, np.inf).astype(np.float32)
    reg = zbuf[iy0:iy1 + 1, ix0:ix1 + 1]
    upd = zf < reg
    if upd.any():
        reg[upd] = zf[upd]
        rgb[iy0:iy1 + 1, ix0:ix1 + 1][upd] = col


def view_basis(elev, azim):
    f = -np.array([np.cos(np.radians(elev)) * np.cos(np.radians(azim)),
                   np.cos(np.radians(elev)) * np.sin(np.radians(azim)),
                   np.sin(np.radians(elev))])
    f /= np.linalg.norm(f)
    right = np.cross([0.0, 0.0, 1.0], f); right /= np.linalg.norm(right)
    return f, right, np.cross(f, right)


def render(P, COL, W, H, elev, azim, SS=2, bg=BG):
    f, right, up2 = view_basis(elev, azim)
    sx = P @ right; sy = P @ up2; sz = P @ f
    x0, x1 = float(sx.min()), float(sx.max()); y0, y1 = float(sy.min()), float(sy.max())
    pad = 0.02 * max(x1 - x0, y1 - y0)
    x0 -= pad; x1 += pad; y0 -= pad; y1 += pad
    Wp, Hp = W * SS, H * SS
    scale = max((x1 - x0) / Wp, (y1 - y0) / Hp)
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    pxs = (sx - cx) / scale + (Wp - 1) / 2.0
    pys = (cy - sy) / scale + (Hp - 1) / 2.0
    zbuf = np.full((Hp, Wp), np.inf, np.float32)
    rgb = np.empty((Hp, Wp, 3), np.float32); rgb[...] = bg
    for m in range(len(P)):
        for t in ((0, 1, 2), (0, 2, 3)):
            raster_tri(pxs[m][list(t)], pys[m][list(t)], sz[m][list(t)], COL[m], zbuf, rgb)
    return rgb.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))


def colorize(gid, nrm, f, colmap):
    n = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    br = 0.58 + 0.32 * np.clip(n @ (-f), 0, 1) + 0.10 * np.clip(n[:, 2], 0, 1)
    base = np.array([colmap[int(i)] for i in gid], np.float32)
    return base * br[:, None]


def main():
    npz = sys.argv[1] if len(sys.argv) > 1 else "meltpool_growth_gid.npz"
    outp = sys.argv[2] if len(sys.argv) > 2 else "FIG_pool_grains_3d_v2.png"
    d = np.load(npz if os.path.isabs(npz) else os.path.join(HERE, npz))
    g0 = d["gid"].astype(np.int32); dx = float(d["dx"]); s0 = d["snaps"][0]
    pool = (s0 == 0)
    nx, ny, nz = g0.shape
    print("域 %d x %d x %d 胞, dx=%.2f um" % (nx, ny, nz, dx * 1e6))
    inside = pool & (g0 > 0); tot = 0; frac = {}
    for gid in range(1, g0.max() + 1):
        n = int((inside & (g0 == gid)).sum())
        if n:
            frac[gid] = n; tot += n
    print("池内晶粒体积占比:", "  ".join("gid%d=%.1f%%" % (k, 100.0 * v / tot) for k, v in frac.items()))

    keep_pool = pool
    g_pad = pad_closed(g0, 0)
    GN = smoothed_grads(g_pad, pad_closed(keep_pool, False))

    xc = (nx - 1) // 2; yc = (ny - 1) // 2
    qcut = np.zeros_like(keep_pool); qcut[:xc + 1, yc:, :] = True
    hcut = np.zeros_like(keep_pool); hcut[:, yc:, :] = True

    views = []

    def add(title, keep, want_skin, want_gb, pair, colmap, elev, azim, W=1150, H=880):
        kp = pad_closed(keep, False)
        P, gidv, kind, cell, axn = build_faces(g_pad, kp, dx, want_skin, want_gb, pair)
        if len(P) == 0:
            img = np.ones((H, W, 3), np.float32)
            print("  [%s] 面片 0（该晶界对不存在）-> 占位" % title)
            views.append((title, img))
            return
        nrm = face_normals(cell, gidv, axn, GN)
        f, _, _ = view_basis(elev, azim)
        COL = colorize(gidv, nrm, f, colmap)
        img = render(P, COL, W, H, elev, azim)
        print("  [%s] 面片 %d" % (title, len(P)))
        views.append((title, img))

    add("① 完整熔池外壳：按晶粒上色（不透明）", keep_pool, True, True, None, GCOL, 22, -55)
    add("② 1/4 剖切：切掉近角 (+x,-y)，露出两块正交截面", keep_pool & qcut, True, True, None, GCOL, 22, -55)
    add("③ 对半剖切正视：截面就是各晶粒的区域（像金相）", keep_pool & hcut, True, True, None, GCOL, 8, -90)
    add("④ 晶界曲面网络（同样 1/4 剖切，只看面）",
        keep_pool & qcut, False, True, None, {k: GB_ALL for k in GCOL}, 22, -55)
    top2 = sorted(frac, key=lambda k: -frac[k])[:2]
    if len(top2) == 2:
        p2 = (min(top2), max(top2))
        add("⑤ 只用 gid%d|gid%d 之间的那张晶界面（不剖切，看整张面）" % p2,
            keep_pool, False, True, p2, {k: GB_56 for k in GCOL}, 26, -48)
    else:
        add("⑤ （池内只有一个晶粒，无晶界面）", keep_pool, False, True, (1, 2),
            {k: GB_56 for k in GCOL}, 26, -48)
    add("⑥ 俯视完整外壳：顶面（自由表面）被晶粒分成几块", keep_pool, True, True, None, GCOL, 72, -90)

    fig, axes = plt.subplots(2, 3, figsize=(19.5, 12.0))
    for (t, img), ax in zip(views, axes.ravel()):
        ax.imshow(img); ax.set_title(t, fontsize=12.5); ax.axis("off")
    hs = [plt.Line2D([], [], marker="s", ls="", ms=11, color=GCOL[k],
                     label="gid %d   %4.1f%%（池内体积）" % (k, 100.0 * v / tot)) for k, v in frac.items()]
    hs.append(plt.Line2D([], [], marker="s", ls="", ms=11, color=GB_ALL, label="晶界曲面"))
    if len(top2) == 2:
        hs.append(plt.Line2D([], [], marker="s", ls="", ms=11, color=GB_56,
                             label="gid%d|gid%d 界面" % (min(top2), max(top2))))
    fig.legend(handles=hs, loc="lower center", ncol=len(hs), fontsize=11, framealpha=0.92)
    fig.suptitle("熔池内部晶粒三维形状（真 z-buffer、不透明、光滑法向着色、dx = %.0f um 全分辨率）"
                 "—— 每个晶粒是一整块闭合体" % (dx * 1e6), fontsize=13)
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    p = outp if os.path.isabs(outp) else os.path.join(HERE, outp)
    fig.savefig(p, dpi=145); plt.close(fig)
    print("saved", p)


if __name__ == "__main__":
    main()