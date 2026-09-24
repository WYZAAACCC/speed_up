#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_meltpool_fine.py --- 演示：从真实熔池底部外延生长 prior-beta 晶粒

依据（docs/LIT_SEARCH_BRIEF_Ti64_LPBF.md L124-126）：
  prior-beta 柱状晶【宽】 124-168 um；等轴 100-200 um；长径比 4.5-17.4、长 >1 mm。
  而 LPBF 熔池宽约 150 um ⇒ 池底横向只跨约 1-2 个 prior-beta 晶粒；
  沿熔道方向跨 3-6 个 ⇒【池底能外延长出的晶粒数 = 个位数】。本演示取 6 个。

设定：
  * 区域 200 x 300 x 200 um（dx = 2 um），位于熔池下方；**不重熔**。
  * 热场 = 静态熔池（激光关闭后指数衰减，与 thermal_layer.py / 决策 D3 同一设定）。
  * 底/侧面基底外延形核；熔池其余部分为液体，从池底与池壁向内凝固。
  * 输出：growth 过程快照 + 最终三维晶粒骨架/晶界网络 + VTK（ParaView）。

⚠ 记账（与本框架既有结论一致，不得省略）：
  * 包络捕获用的是 `decentered`（生产/历史规则）：驱动量取在【前沿】✓ 物理正确，
    但几何有 ~21% 的格点路径偏差（CA3D_REPORT §10.2 的 T8）。
  * 热场给定、潜热未与 CA 双向耦合（§4 局限 7）；凝固化学是亚网格 Schell（§4 局限 1）。
"""
import math, os, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from mpl_toolkits.mplot3d import Axes3D                      # noqa: F401
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE
FONT = "/mnt/c/Windows/Fonts/simhei.ttf"
if os.path.exists(FONT):
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False

DX = 1.5e-6
NX, NY, NZ = 134, 200, 134          # 201 x 300 x 201 um, dx=1.5um
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
NGX, NGY = 2, 3                      # 6 个种子（池底能长出的量级）


def run(nsnap=6):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
    n0 = len(ca.nucleate_substrate_grid(NGX, NGY))
    T_init = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    nfill = ca.seed_solid_from_substrate(T_init, T_SOL)
    print("基底种子 {} 个；初始固相填充 {} 胞（T<T_SOL）；初始液相 {} 胞".format(
        n0, nfill, int((ca.gid == 0).sum())))
    irf = ca.irf
    V_max = max(float(irf(np.array([T_LIQ - T_SOL]))[0]), 0.2)
    dt = DX / (4.0 * V_max)
    t_end = 1.2e-3
    nst = int(t_end / dt)
    print("V_max={:.3f} m/s -> dt={:.2e} s, 步数 {}".format(V_max, dt, nst))
    snaps, times, hist = [], [], []
    t0 = time.time()
    for s_ in range(nst):
        ca.t = s_ * dt
        T = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
        ca.step(dt, T, window=None)
        if s_ % 5 == 0 and int((ca.gid == 0).sum()) > 0 and len(snaps) < 40:
            snaps.append(ca.gid.copy()); times.append(ca.t)
            hist.append((ca.t, ca.solid_fraction(), len(ca.grain_ids())))
    snaps.append(ca.gid.copy()); times.append(ca.t)
    print("用时 {:.1f} s；末态 f_s={:.4f}；晶粒 {} 个；晶界网络面积 {:.3e} m^2".format(
        time.time() - t0, ca.solid_fraction(), len(ca.grain_ids()), ca.gb_area()))
    return ca, snaps, times, hist


def _cmap(ng):
    base = plt.get_cmap("tab20")
    cols = [(1.0, 1.0, 1.0, 1.0)]                     # gid = 0 -> 液相(白)
    for i in range(1, ng + 1):
        cols.append(base((i - 1) % 20))
    return ListedColormap(cols), BoundaryNorm(np.arange(-0.5, ng + 1.5), ng + 1)


def fig_process(ca, snaps, times):
    if len(snaps) > 8:
        n_liq = np.array([float((x == 0).sum()) for x in snaps])
        pick = sorted(set(int(np.argmin(np.abs(n_liq - q * n_liq[0])))
                          for q in (1.0, 0.6, 0.35, 0.15, 0.05, 0.0)))
        snaps = [snaps[i] for i in pick]; times = [times[i] for i in pick]
    ng = len(ca.axes) - 1
    cmap, norm = _cmap(ng)
    jc = NY // 2
    n = len(snaps)
    fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4.0 * ((n + 1) // 2), 7.4))
    axes = np.atleast_1d(axes).ravel()
    for k in range(n):
        ax = axes[k]
        sl = snaps[k][:, jc, :].T                        # x-z 切片
        ax.imshow(sl, origin="lower", cmap=cmap, norm=norm, interpolation="nearest",
                  extent=[0, NX * DX * 1e6, 0, NZ * DX * 1e6], aspect="equal")
        ax.set_title("t = {:.2e} s   (f_s = {:.2f})".format(times[k], float((snaps[k] > 0).mean())),
                     fontsize=10)
        ax.set_xlabel("x [um]"); ax.set_ylabel("z [um]")
    for k in range(n, len(axes)):
        axes[k].axis("off")
    fig.suptitle("熔池底部外延生长过程（x-z 中心切片，颜色=晶粒身份，白色=液体）", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p = os.path.join(OUT, "FIG_meltpool_growth_process_fine.png")
    fig.savefig(p, dpi=140); plt.close(fig)
    print("saved", p)


def fig_final3d(ca):
    ng = len(ca.axes) - 1
    cmap, norm = _cmap(ng)
    st = 5                                               # 抽稀，供 3D 体素渲染
    g = ca.gid[::st, ::st, ::st]
    xs = (np.arange(g.shape[0]) + 0.5) * DX * st * 1e6
    ys = (np.arange(g.shape[1]) + 0.5) * DX * st * 1e6
    zs = (np.arange(g.shape[2]) + 0.5) * DX * st * 1e6
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    fig = plt.figure(figsize=(13, 6.2))
    ax = fig.add_subplot(121, projection="3d")
    filled = g > 0
    fc = np.zeros(g.shape + (4,), float)
    for gid in range(1, ng + 1):
        fc[g == gid] = cmap(norm(gid))
    ax.voxels(filled, facecolors=fc, edgecolor=None, shade=True)
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]"); ax.set_zlabel("z [um]")
    ax.set_title("最终三维晶粒骨架（{} 个 prior-beta 晶粒，抽稀 {}x 渲染）".format(ng, st),
                 fontsize=11)
    ax.view_init(elev=22, azim=-58)
    ax.set_box_aspect((NX, NY, NZ))
    # 右图：晶界网络（胞面点云）
    ax2 = fig.add_subplot(122, projection="3d")
    gb = np.zeros(g.shape, bool)
    gb[:-1] |= (g[:-1] != g[1:]); gb[1:] |= (g[:-1] != g[1:])
    gb[:, :-1] |= (g[:, :-1] != g[:, 1:]); gb[:, 1:] |= (g[:, :-1] != g[:, 1:])
    gb[:, :, :-1] |= (g[:, :, :-1] != g[:, :, 1:]); gb[:, :, 1:] |= (g[:, :, :-1] != g[:, :, 1:])
    gb &= (g > 0)
    idx = np.where(gb)
    if len(idx[0]):
        cols = cmap(norm(g[gb]))
        ax2.scatter(X[gb], Y[gb], Z[gb], c=cols, s=1.2, marker="s", depthshade=False)
    ax2.set_xlabel("x [um]"); ax2.set_ylabel("y [um]"); ax2.set_zlabel("z [um]")
    ax2.set_title("晶界网络（grain ID 场的间断集合）", fontsize=11)
    ax2.set_box_aspect((NX, NY, NZ))
    ax2.view_init(elev=22, azim=-58)
    p = os.path.join(OUT, "FIG_meltpool_final_3d.png")
    fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    print("saved", p)


if __name__ == "__main__":
    ca, snaps, times, hist = run()
    n_liq = np.array([float((x == 0).sum()) for x in snaps])
    snap_pick = sorted(set(int(np.argmin(np.abs(n_liq - q * n_liq[0])))
                           for q in (1.0, 0.75, 0.5, 0.3, 0.12, 0.0)))
    np.savez(os.path.join(OUT, "meltpool_growth_fine.npz"), gid=ca.gid, dx=DX,
             snaps=np.array([snaps[i] for i in snap_pick]),
             snap_t=np.array([times[i] for i in snap_pick]))
    print("过程快照 {} 张已存盘 (t = {})".format(
        len(snap_pick), " ".join("%.2e" % times[i] for i in snap_pick)))
    print("saved meltpool_growth_fine.npz (仿真已落盘，画图可重跑)")
    fig_process(ca, snaps, times)
    # 三维图统一由 fig_meltpool_3d.py 出（那里的软件渲染器才能把晶界画成实心面片）
    # fig_final3d(ca)
    vtk = os.path.join(OUT, "meltpool_growth_final.vtk")
    ca.write_vtk(vtk)
    print("saved", vtk)
    print("saved meltpool_growth_fine.npz")