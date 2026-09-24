#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ca3d_envelope.py --- 包络/归属/化学的【正面物理判据】（2026-09-23 审计后新增）

为什么单独一套：审计（CA3D_AUDIT_2026-09-23.md）发现既有 60 条判据里**没有一条**量
"包络各向异性必须等于 KD 八面体"，于是 `decentered` 的缺陷（各向异性 1.73 -> 1.05、
体积 -25%、且不随 dx 收敛）活了很久。本套把审计里的判据固化下来。

判据：
  E1 单晶包络 = KD 八面体 {sum_a|p_a.(x-x_g)| <= l}：径向函数 l/Σ、体积 8l^3/6
  E2 几何误差随 dx 收敛（O(dx)），且不是"格点不变量"
  E3 结果与语句顺序无关（打乱 OFFSETS 逐位相同）
  E4 不再制造 1 胞假晶粒（旧版一次调用可造 68578 个）
  E5 熔池界面质量：无孤岛、界面连通、且随 dt 收敛
  E6 化学：基底 = c0、质量守恒、晚凝固更富集、晶界相邻更富集
用法: /root/miniconda3/envs/ml/bin/python verify_ca3d_envelope.py
"""
import os, sys, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V, F_MIN, OFFSETS
from scipy import ndimage as ndi

RESULTS = []
BASE_OFF = list(ca3d.OFFSETS)


def chk(name, verdict, detail, value=None):
    RESULTS.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<58} {}".format(verdict, name, detail), flush=True)


def qaa(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))


def grow_one(dx, nell_target=15e-6, dT=12.0, N=61, mode="envelope"):
    ca = CA3D(N, N, N, dx, irf=IRF(), seed=7, capture=mode)
    c = (N//2, N//2, N//2)
    g = ca.add_grain(c[0], c[1], c[2], quat=qaa((0.3, 0.7, 0.2), 37.0))
    P = ca.axes[g]
    T = ca.T_iso(dT)
    V = float(ca.irf.capped(np.array([dT]))[0][0])
    dt = dx/(4*V)
    nst = int(round(nell_target/dt/V))
    t = 0.0
    for s in range(nst):
        ca.t = t
        ca.step(dt, T, window="full")
        t += dt
    ell = V*nst*dt
    solid = ca.gid > 0
    out = {}
    for nm, cv in (("<100>", (1, 0, 0)), ("<110>", (1, 1, 0)), ("<111>", (1, 1, 1))):
        cv = np.array(cv, float); cv /= np.linalg.norm(cv)
        nw = P @ cv
        sm = 0.0
        for r in np.arange(0.0, 2.5*ell, 0.1*dx):
            p = (np.array(c) + 0.5)*dx + r*nw
            idx = np.floor(p/dx).astype(int)
            if np.any(idx < 0) or np.any(idx >= N):
                break
            if solid[idx[0], idx[1], idx[2]]:
                sm = r
        out[nm] = sm/ell
    vol = int(solid.sum()); voli = (2*ell)**3/6.0/(dx**3)
    return out, vol, voli, ell


# =============================================== E1/E2 包络几何
def E1_E2():
    print("\n" + "="*96)
    print("E1/E2  包络 = KD 八面体；几何误差随 dx 收敛")
    print("="*96)
    tab = {}
    for dx in (0.5e-6, 1.0e-6, 2.0e-6, 3.0e-6):
        r, vol, voli, ell = grow_one(dx)
        tab[dx] = (r, vol, voli, ell)
        print("   dx=%.1f um  l=%.1f 胞 | r(<100>)/l=%.3f  r(<110>)/l=%.3f  r(<111>)/l=%.3f | "
              "体积 %d vs 解析 %d (%+.2f%%)" % (
            dx*1e6, ell/dx, r["<100>"], r["<110>"], r["<111>"], vol, int(voli),
            100.0*(vol-voli)/voli))
    r1 = tab[1.0e-6][0]
    ok1 = (abs(r1["<100>"] - 1.0) <= 0.06 and abs(r1["<111>"] - 0.577) <= 0.05)
    chk("E1a 径向函数 = l/Σ（dx=1um）", "PASS" if ok1 else "FAIL",
        "r(<100>)/l=%.3f (期望 1.00±0.06), r(<111>)/l=%.3f (0.577±0.05)" % (
            r1["<100>"], r1["<111>"]), r1)
    ratio = r1["<100>"]/r1["<111>"]
    chk("E1b KD 各向异性比 <100>:<111>", "PASS" if abs(ratio-1.732) <= 0.15 else "FAIL",
        "实测 %.3f (KD 八面体 1.732±0.15)" % ratio, ratio)
    errs = {dx: abs(100.0*(v[1]-v[2])/v[2]) for dx, v in tab.items()}
    mono = all(errs[a] <= errs[b] + 0.02 for a, b in ((0.5e-6, 1.0e-6), (1.0e-6, 2.0e-6), (2.0e-6, 3.0e-6)))
    chk("E2 体积误差随 dx 单调减小（O(dx)）", "PASS" if mono else "FAIL",
        "误差 dx=0.5/1/2/3um: %.3f%% / %.3f%% / %.3f%% / %.3f%%" % (
            errs[0.5e-6], errs[1.0e-6], errs[2.0e-6], errs[3.0e-6]), errs)


# =============================================== E3/E4 顺序无关 / 无假晶粒
def _cold_fill(offs, nseed=2, nx=41, iters=120, sep=10):
    ca3d.OFFSETS = offs
    c = CA3D(nx, nx, nx, 1e-6, irf=IRF(), seed=9)
    k = nx//2
    if nseed == 2:
        c.add_grain(k - sep//2, k, k); c.add_grain(k + sep//2, k, k)
    else:
        c.add_grain(0, 0, 0)
    T = np.full(c.shape, 300.0)
    for _ in range(iters):
        before = int((c.gid == 0).sum())
        c.thermal_capture(T, mode="count")
        if int((c.gid == 0).sum()) == before:
            break
    out = (c.gid.copy(), getattr(c, "n_spont", 0), int((c.gid == 0).sum()))
    ca3d.OFFSETS = BASE_OFF
    return out


def E3_E4():
    print("\n" + "="*96)
    print("E3/E4  顺序无关性；不再制造 1 胞假晶粒")
    print("="*96)
    g0, _, left0 = _cold_fill(BASE_OFF)
    diffs = []
    for s in range(3):
        o = BASE_OFF[:]; np.random.default_rng(s).shuffle(o)
        g, _, left = _cold_fill(o)
        diffs.append(int((g != g0).sum()))
    chk("E3a 打乱 OFFSETS 顺序 => 过冷液相归属逐位相同", "PASS" if max(diffs) == 0 else "FAIL",
        "3 次打乱分别不同 %s 胞（旧版 92~214 胞）" % diffs, diffs)
    ca3d.OFFSETS = BASE_OFF
    c = CA3D(61, 61, 61, 1e-6, irf=IRF(), seed=3)
    c.nucleate_substrate_grid(2, 2)
    c.seed_solid_from_substrate(np.full(c.shape, 300.0), T_SOL)
    s0 = c.gid.copy()
    ds = []
    for s in range(2):
        o = BASE_OFF[:]; np.random.default_rng(10+s).shuffle(o)
        ca3d.OFFSETS = o
        c2 = CA3D(61, 61, 61, 1e-6, irf=IRF(), seed=3)
        c2.nucleate_substrate_grid(2, 2)
        c2.seed_solid_from_substrate(np.full(c2.shape, 300.0), T_SOL)
        ds.append(int((c2.gid != s0).sum()))
        ca3d.OFFSETS = BASE_OFF
    chk("E3b 基底初始晶粒图顺序无关（各向异性 Voronoi）", "PASS" if max(ds) == 0 else "FAIL",
        "打乱后不同 %s 胞（旧版 30.16%% / 32.84%%）" % ds, ds)
    g1, nsp, left1 = _cold_fill(BASE_OFF, nseed=1)
    chk("E4 冷液相填充不制造新晶粒（旧版 41^3 盒造 68578 个）", "PASS" if nsp == 0 else "FAIL",
        "自发形核晶粒 %d 个；全盒填满(剩余液相 %d)" % (nsp, left1), nsp)


# =============================================== E5/E6 熔池
def _meltpool(fac=1.0, capture="envelope"):
    DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
    T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture=capture)
    ca.nucleate_substrate_grid(2, 3)
    ca.seed_solid_from_substrate(ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), T_SOL)
    pool0 = (ca.gid == 0).copy(); sub0 = ca.gid > 0
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max)/fac
    for s in range(int(1.2e-3/dt)):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
        if (ca.gid == 0).sum() == 0:
            break
    ca.finalize_chemistry()
    return ca, pool0, sub0


def _iface_quality(g, keep):
    gg = np.where(keep, g, 0)
    ft = []
    for ax in range(3):
        n = gg.shape[ax]
        a = np.take(gg, list(range(n-1)), axis=ax); b = np.take(gg, list(range(1, n)), axis=ax)
        for ii in np.argwhere((a > 0) & (b > 0) & (a != b)):
            ft.append((ax, tuple(ii)))
    proj = set()
    for ax, ii in ft:
        proj.add((ax,) + tuple(v for k, v in enumerate(ii) if k != ax))
    small = 0
    for gid in np.unique(g[keep & (g > 0)]):
        lab, _ = ndi.label(gg == gid)
        sz = np.bincount(lab.ravel())
        for L in range(1, len(sz)):
            if 0 < sz[L] < 8:
                small += int(sz[L])
    return len(ft), len(proj), small


def E5_E6():
    print("\n" + "="*96)
    print("E5/E6  熔池：界面质量 + dt 收敛；化学（局部路径/守恒/富集趋势）")
    print("="*96)
    res = {}
    for tag, fac in (("dt", 1.0), ("dt/2", 2.0)):
        ca, pool0, sub0 = _meltpool(fac)
        pool = pool0 & (ca.gid > 0)
        nf, npr, small = _iface_quality(ca.gid, pool)
        res[tag] = (nf, npr, small, ca)
        print("   %-5s 晶界面 %d, 投影面 %d, 粗糙度 %.2f, 孤岛胞 %d" % (
            tag, nf, npr, nf/max(npr,1), small))
    chk("E5a 池内无孤岛碎屑胞（<8 胞的块）", "PASS" if res["dt"][2] == 0 else "FAIL",
        "孤岛胞 = %d（旧 default 是 61，修后 0）" % res["dt"][2], res["dt"][2])
    d = abs(res["dt"][0] - res["dt/2"][0])/max(res["dt"][0], 1)
    chk("E5b 晶界面数随 dt 收敛（相邻差 <3%）", "PASS" if d < 0.03 else "FAIL",
        "dt: %d 面, dt/2: %d 面, 相对差 %.2f%%" % (res["dt"][0], res["dt/2"][0], 100*d), d)
    ca = res["dt"][3]; pool0 = (ca._liq0 if getattr(ca, "_liq0", None) is not None else (ca.gid > 0))
    pool = (ca.gid > 0) & (~np.isfinite(ca.ts) | (ca.ts >= 0.0))
    sub = np.isfinite(ca.ts) & (ca.ts < 0.0)
    chk("E6a 基底成分 = c0（旧版给 k*c0，低 37%）", "PASS" if abs(ca.c[sub].mean()-C0_V) < 1e-9 else "FAIL",
        "基底 c = %.4f (c0=%.4f)" % (ca.c[sub].mean(), C0_V), ca.c[sub].mean())
    mb = ca.mass_balance()
    chk("E6b 质量守恒（体平均/c0，修前 0.7324）", "PASS" if abs(mb-1.0) < 1e-3 else "FAIL",
        "%.5f" % mb, mb)
    capp = np.isfinite(ca.ts) & (ca.ts >= 0.0)
    corr = float(np.corrcoef(ca.ts[capp], ca.cl[capp])[0, 1])
    chk("E6c 越晚凝固越富集 corr(t_capture, c_l)", "PASS" if corr > 0.5 else "FAIL",
        "corr = %+.3f (>0.5)；旧全域-f 路径该项 ≈ 0（池内 c 几乎常数）" % corr, corr)
    rng = float((ca.cl[capp].max()-ca.cl[capp].min())/C0_V)
    chk("E6d c_l 空间动态范围 (max-min)/c0 > 1", "PASS" if rng > 1.0 else "FAIL",
        "实测 %.2f（修前 ~0.05）" % rng, rng)


def main():
    t0 = time.time()
    E1_E2(); E3_E4(); E5_E6()
    np_ = len(RESULTS)
    npass = sum(1 for r in RESULTS if r["verdict"] == "PASS")
    nwarn = sum(1 for r in RESULTS if r["verdict"] == "WARN")
    nfail = sum(1 for r in RESULTS if r["verdict"] == "FAIL")
    print("\n" + "="*96)
    print("汇总: %d 项  PASS %d / WARN %d / FAIL %d   (用时 %.0f s)" % (
        np_, npass, nwarn, nfail, time.time()-t0))
    print("="*96)
    return nfail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)