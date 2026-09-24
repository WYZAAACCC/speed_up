#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_ca3d_meltpool.py --- Window A 的三维算例

设定（沿用用户已确认的建模范围）：
  * 三维小立方体区域，位于熔池底部；**不重熔**。
  * 热场 = 静态熔池（激光关掉后指数衰减），与 thermal_layer.py 同一设定（决策 D3）。
  * 底部为基底/外延形核（prior-beta 从熔池底部长出）；上方是液体，无晶粒干扰。
  * 输出：冻结的 prior-beta 晶粒骨架 + 晶界网络几何 + 胞界成分场（Window B/C 的输入）。

用法: /root/miniconda3/envs/ml/bin/python demo_ca3d_meltpool.py
"""

import math, os, time
import numpy as np
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V, M_L

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_ca3d")
os.makedirs(OUT, exist_ok=True)


def main():
    dx = 2.0e-6
    nx, ny, nz = 48, 48, 36          # 96 x 96 x 72 um
    irf = IRF()
    ca = CA3D(nx, ny, nz, dx, irf=irf, seed=2026)

    # ---- 基底/外延形核：底面 8x8 个取向随机的 prior-beta 种子 ----
    ng0 = ca.nucleate_substrate_grid(8, 8)
    print("底面外延形核: {} 个种子".format(len(ng0)))

    # ---- 热场：静态熔池 + 指数衰减（峰值在顶部中心，所以从底部/边缘先凝固）----
    T_peak, sigma, tau, T_bath = 2500.0, 25e-6, 3.1e-4, 353.0

    # ---- 初始固相区：熔池之外（底部基底 + 两侧已凝固熔道）本来就不是液体 ----
    T_init = ca.T_meltpool(T_peak, sigma, tau, T_bath)
    n_seed_solid = ca.seed_solid_from_substrate(T_init, T_SOL)
    print("初始固相区（T<T_SOL 的外延填充）: {} 个胞".format(n_seed_solid))

    # ---- 时间步：由最快生长速度定（dx/(4 V_max)）----
    V_max = float(irf(np.array([T_LIQ - T_SOL]))[0])
    V_max = max(V_max, 0.2)
    dt = dx / (4.0 * V_max)
    t_end = 1.2e-3                     # 足够让熔池完全凝固
    nst = int(t_end / dt)
    print("V_max={:.3f} m/s -> dt={:.3e} s, 步数 {}".format(V_max, dt, nst))

    hist = []
    t0 = time.time()
    for s in range(nst):
        ca.t = s * dt
        T = ca.T_meltpool(T_peak, sigma, tau, T_bath)
        nnew = ca.step(dt, T, window=None)
        if s % max(1, nst // 12) == 0 or s == nst - 1:
            hist.append((ca.t, ca.solid_fraction(), len(ca.grain_ids())))
            print("  t={:.3e} s  f_s={:.4f}  晶粒数={}  本步捕获={}  ({:.0f} s)".format(
                ca.t, hist[-1][1], hist[-1][2], nnew, time.time() - t0))

    ca.scheil_chemistry()
    fs = ca.solid_fraction()
    print("热力学约束: 外延并入 {} 胞 ; 自发形核 {} 个".format(getattr(ca, "n_thermal", 0), getattr(ca, "n_spont", 0)))
    nl = max(getattr(ca, "n_front_steps", 1), 1)
    print("IRF 越界(只算前沿固相胞): dT<lo {:.3f}% ; dT>hi {:.3f}%  (共 {} 前沿胞步)".format(100.0 * getattr(ca, "n_dT_low", 0) / nl, 100.0 * getattr(ca, "n_dT_high", 0) / nl, nl))
    pool0 = T_init >= T_SOL
    print("初始熔池(液相)胞数: {} ({:.1f}% 体积)".format(int(pool0.sum()), 100.0 * pool0.mean()))

    # ---------------- 结果与诊断 ----------------
    print("")
    print("=" * 90)
    print("三维结果")
    print("=" * 90)
    print("末态固相分数        : {:.4f}".format(fs))
    print("存活晶粒数          : {} / 初始 {} (竞争淘汰 {:.0f}%)".format(
        len(ca.grain_ids()), len(ng0), 100 * (1 - len(ca.grain_ids()) / max(len(ng0), 1))))
    print("晶界网络面积        : {:.3e} m2  (= {:.1f} 个胞面)".format(
        ca.gb_area(), ca.gb_area() / dx ** 2))
    vf = ca.grain_volume_frac()
    if vf:
        arr = np.array(sorted(vf.values(), reverse=True))
        print("晶粒体积分数 top5   : {}".format(np.round(arr[:5], 4)))
        print("最大/平均晶粒占比   : {:.3f} / {:.5f}".format(arr[0], arr.mean()))

    # 柱状度：每个晶粒的高度 / 等效横向宽度
    solid = (ca.gid > 0) & pool0      # 柱状度只在【初始熔池】内统计（外延基底不算）
    aspects = []
    for g in ca.grain_ids():
        m = ca.gid == g
        ext = []
        for ax in range(3):
            idx = np.where(m.any(axis=tuple(i for i in range(3) if i != ax)))[0]
            ext.append((idx.max() - idx.min() + 1) * dx if idx.size else dx)
        if ext[0] > 0 and ext[1] > 0:
            aspects.append(ext[2] / (0.5 * (ext[0] + ext[1])))
    if aspects:
        print("柱状度 h/w (中位/最大) : {:.2f} / {:.2f}".format(
            float(np.median(aspects)), float(np.max(aspects))))

    c = ca.cl[ca.gid > 0]
    print("")
    print("化学场（胞界/枝晶间 V 摩尔分数，Window C 的输入）")
    print("  范围 {:.4f} ~ {:.4f}  中位 {:.4f}  (c0={:.4f}, Scheil 上限 0.198)".format(
        c.min(), c.max(), float(np.median(c)), C0_V))
    print("  = 富集比 s = c/cl_bulk: {:.2f} ~ {:.2f}".format(c.min() / C0_V, c.max() / C0_V))

    # 守恒恒等式（逐点精确）
    ident = ca.check_scheil_conservation()
    print("  Scheil 守恒恒等式最大偏差: {:.2e}".format(
        max(abs(t - C0_V) / C0_V for (f, t) in ident)))

    # ---------------- 切片图（自己看一眼结构是否合理）----------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    zs = [2, nz // 4, nz // 2, nz - 3]
    fig, axes = plt.subplots(1, len(zs), figsize=(4 * len(zs), 4))
    for ax, z in zip(axes, zs):
        im = ax.imshow(ca.gid[:, :, z].T, origin="lower", cmap="tab20",
                       interpolation="nearest")
        ax.set_title("z = {} ({} um)".format(z, int((z + 0.5) * dx * 1e6)))
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("CA3D melt-pool solidification: grain ID slices (3D run)")
    fig.tight_layout()
    png = os.path.join(OUT, "ca3d_slices.png")
    fig.savefig(png, dpi=110)
    print("切片图: " + png)

    # ---------------- 输出 ----------------
    p_npz = ca.save(os.path.join(OUT, "ca3d_meltpool.npz"))
    # VTK: gid 用整数场, 另加 fcap / cl / c
    ca.fcap = np.where(np.isfinite(ca.fcap), ca.fcap, 0.0)
    p_vtk = ca.write_vtk(os.path.join(OUT, "ca3d_meltpool.vtk"),
                         fields=("gid", "c", "cl", "ts", "fcap"))
    print("")
    print("已写出:")
    print("  " + p_npz)
    print("  " + p_vtk + "   (ParaView 可直接打开看三维晶粒骨架)")

    with open(os.path.join(OUT, "ca3d_meltpool_stats.txt"), "w") as f:
        f.write("dx={:g} m  grid={}x{}x{}\n".format(dx, nx, ny, nz))
        f.write("seeds={} survivors={} fs={:.4f}\n".format(len(ng0), len(ca.grain_ids()), fs))
        f.write("gb_area_m2={:.6e}\n".format(ca.gb_area()))
        f.write("aspect_median={:.3f} aspect_max={:.3f}\n".format(
            float(np.median(aspects)) if aspects else 0.0,
            float(np.max(aspects)) if aspects else 0.0))
        f.write("cl_min={:.5f} cl_max={:.5f} cl_med={:.5f}\n".format(
            c.min(), c.max(), float(np.median(c))))
        f.write("history t,fs,ngrains:\n")
        for h in hist:
            f.write("  {:.4e} {:.4f} {}\n".format(*h))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
