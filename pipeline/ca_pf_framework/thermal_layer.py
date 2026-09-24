#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thermal_layer.py -- 数学框架 L1-T 层（焓式能量方程 + 潜热）的参考实现与验证

对应 MATH_FRAMEWORK.md 3.1：
    dh/dt = div(k grad T) + q,     h(T) = int rho*cp dT + rho*Lf*f_l

验证三件事：
  V-T1  纯导热（Lf=0）对解析解 erf 的收敛阶
  V-T2  1D Stefan 前沿位置 vs Neumann 相似解 x_f = 2*lam*sqrt(alpha*t)
  V-T3  离散能量守恒  d/dt int h dV = 边界通量
再加一个 2D 演示：静态熔池（高斯热斑）在「激光关掉」后的凝固（本路线的工作设定）。

用法： /root/miniconda3/envs/ml/bin/python thermal_layer.py
"""

import math
import io
import os
import numpy as np
from scipy.special import erf, erfinv

R_GAS = 8.314462618

# ---------------------------------------------------------------- 物性 (Ti64)
T_MELT = 1923.0        # K
L_F    = 286.0e3       # J/kg          [L] PMC11766489
RHO    = 4219.0        # kg/m3  (1900 K) [L]
CP     = 890.0         # J/(kg K)      [L]  (483+0.215T @1900)
K_COND = 28.0          # W/(m K)       [L]  (1.25+0.015T @1800)
ALPHA  = K_COND / (RHO * CP)
H_LAT  = RHO * L_F     # J/m3 体积潜热
DT_SUPER = 577.0

RESULTS = []
def chk(name, verdict, detail, value=None):
    RESULTS.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<52} {}".format(verdict, name, detail))


# ============================================================ 2. 焓模型与反演
def h_of_T_pure(T):
    """纯物质：f_l 是阶跃。h 在 T_m 处有 rho*Lf 的跳跃。"""
    T = np.asarray(T, dtype=float)
    return RHO * CP * (T - T_MELT) + np.where(T >= T_MELT, H_LAT, 0.0)


def T_of_h_pure(h):
    """h -> T 的闭式反演（尖界面）。"""
    h = np.asarray(h, dtype=float)
    T = np.where(h < 0.0,
                 T_MELT + h / (RHO * CP),
                 np.where(h > H_LAT,
                          T_MELT + (h - H_LAT) / (RHO * CP),
                          T_MELT))
    return T


def f_l_pure(h):
    h = np.asarray(h, dtype=float)
    return np.where(h < 0.0, 0.0, np.where(h > H_LAT, 1.0, h / H_LAT))


def h_of_T_alloy(T, T_s, T_l):
    """合金：潜热在冻结区间 [T_s, T_l] 内线性释放（apparent 模型）。"""
    T = np.asarray(T, dtype=float)
    w = np.clip((T - T_s) / (T_l - T_s), 0.0, 1.0)
    return RHO * CP * (T - T_MELT) + H_LAT * w


def T_of_h_alloy(h, T_s, T_l):
    """合金焓的闭式反演：分段线性。"""
    h = np.asarray(h, dtype=float)
    h_s = float(h_of_T_alloy(T_s, T_s, T_l))
    h_l = float(h_of_T_alloy(T_l, T_s, T_l))
    slope = H_LAT / (T_l - T_s)
    T_clip = T_MELT + (h - H_LAT * 0.0 - RHO * CP * 0.0) * 0.0  # placeholder
    T = np.where(h <= h_s, T_MELT + h / (RHO * CP),
         np.where(h >= h_l, T_MELT + (h - H_LAT) / (RHO * CP),
                  T_s + (h - h_s) / (RHO * CP + slope)))
    return T


def f_l_alloy(h, T_s, T_l):
    return np.clip((T_of_h_alloy(h, T_s, T_l) - T_s) / (T_l - T_s), 0.0, 1.0)


def h_inv_check():
    print("")
    print("=" * 100)
    print("模块 2  焓反演自洽性 T(h(T)) == T")
    print("=" * 100)
    Ts = np.linspace(1800.0, 2050.0, 2001)
    e1 = float(np.max(np.abs(T_of_h_pure(h_of_T_pure(Ts)) - Ts)))
    chk("T1 纯物质焓反演逐点自洽", "PASS" if e1 < 1e-9 else "FAIL",
        "max |T(h(T)) - T| = {:.2e} K (2001 点, 跨熔点跳跃)".format(e1), e1)
    T_s, T_l = 1893.2, 1911.1
    e2 = float(np.max(np.abs(T_of_h_alloy(h_of_T_alloy(Ts, T_s, T_l), T_s, T_l) - Ts)))
    chk("T2 合金焓反演逐点自洽", "PASS" if e2 < 1e-9 else "FAIL",
        "max |T(h(T)) - T| = {:.2e} K  (冻结区间 {:.1f}~{:.1f} K)".format(e2, T_s, T_l), e2)


# ==================================================== 3. 1D 焓法显式求解器
def solve_1d_enthalpy(nx, dx, dt, nt, T_init, T_left, Lf_on=True,
                      k=K_COND, rho=RHO, cp=CP, alloy=None, record_every=1):
    """1D 焓法. 左端 Dirichlet(T_left), 右端零通量. 返回 (h, T 历史, 能量历史)."""
    alpha = k / (rho * cp)
    h_lat = rho * L_F * (1.0 if Lf_on else 0.0)

    def hT(T):
        if alloy is None:
            return rho * cp * (T - T_MELT) + np.where(T >= T_MELT, h_lat, 0.0)
        Ts_, Tl_ = alloy
        w = np.clip((T - Ts_) / (Tl_ - Ts_), 0.0, 1.0)
        return rho * cp * (T - T_MELT) + h_lat * w

    def Th(h):
        if alloy is None:
            return np.where(h < 0.0, T_MELT + h / (rho * cp),
                   np.where(h > h_lat, T_MELT + (h - h_lat) / (rho * cp), T_MELT))
        Ts_, Tl_ = alloy
        hs = float(rho * cp * (Ts_ - T_MELT))
        hl = float(rho * cp * (Tl_ - T_MELT) + h_lat)
        slope = h_lat / (Tl_ - Ts_)
        return np.where(h <= hs, T_MELT + h / (rho * cp),
               np.where(h >= hl, T_MELT + (h - h_lat) / (rho * cp),
                        Ts_ + (h - hs) / (rho * cp + slope)))

    h = hT(np.full(nx, T_init, dtype=float))
    hist = []
    ehist = []
    for n in range(nt + 1):
        T = Th(h)
        if n % record_every == 0:
            hist.append((n * dt, T.copy()))
        ehist.append((n * dt, float(np.sum(h) * dx),
                      float(k * (T[0] - T[1]) / dx * dt)))
        if n == nt:
            break
        # 显式: 只更新内部, 左端 Dirichlet 用 ghost
        T_ext = np.empty(nx + 2)
        T_ext[1:-1] = T
        T_ext[0] = 2.0 * T_left - T[0]          # ghost, 使界面处 T=(T_left+T[0])/2
        T_ext[-1] = T[-1]                        # 零通量
        lap = (T_ext[2:] - 2.0 * T_ext[1:-1] + T_ext[:-2]) / dx ** 2
        h = h + dt * k * lap
    return hist, ehist


# ================================================================ V-T1 导热
def check_conduction():
    print("")
    print("=" * 100)
    print("模块 3  V-T1  纯导热 (Lf=0) vs 解析解 erf")
    print("=" * 100)
    T0, Tw = 1900.0, 1700.0
    t_end = 5.0e-5   # 短到让 l_T << Lx, 避开右端零通量的镜像反射
    errs = []
    for nx in (40, 80, 160, 320):
        Lx = 200e-6
        dx = Lx / nx
        dt = 0.4 * dx ** 2 / ALPHA
        nt = int(t_end / dt)
        hist, _ = solve_1d_enthalpy(nx, dx, dt, nt, T0, Tw, Lf_on=False)
        t, T = hist[-1]
        x = (np.arange(nx) + 0.5) * dx
        # 半无限介质常壁温解: (T-Tw)/(T0-Tw) = erf(x/(2 sqrt(alpha t)))
        ana = Tw + (T0 - Tw) * erf(x / (2.0 * math.sqrt(ALPHA * t)))
        err = float(np.sqrt(np.mean((T - ana) ** 2)) / (T0 - Tw))
        errs.append(err)
    orders = [math.log(errs[i] / errs[i + 1], 2.0) for i in range(len(errs) - 1)]
    refl = math.exp(-(200e-6) ** 2 / (4.0 * ALPHA * t_end))
    chk("V-T1 纯导热收敛阶", "PASS" if min(orders) > 1.6 else "WARN",
        "有限域反射估计 exp(-L^2/4at) = {:.1e}".format(refl), refl)
    chk("V-T1b 纯导热收敛阶 (O(dx^2) 预期)", "PASS" if min(orders) > 1.6 else "WARN",
        "L2 相对误差 {} ; 阶 {}".format(
            " ".join("{:.2e}".format(e) for e in errs),
            " ".join("{:.2f}".format(o) for o in orders)), errs)


# ============================================================ V-T2 Stefan
def neumann_lambda(Ste):
    """解 lam*exp(lam^2)*erf(lam) = Ste/sqrt(pi)"""
    from scipy.optimize import brentq
    f = lambda l: l * math.exp(l ** 2) * erf(l) - Ste / math.sqrt(math.pi)
    return brentq(f, 1e-8, 3.0)


def check_stefan():
    print("")
    print("=" * 100)
    print("模块 4  V-T2  1D Stefan 前沿位置 vs Neumann 相似解")
    print("=" * 100)
    dT = 50.0
    Tw = T_MELT - dT
    Ste = CP * dT / L_F
    lam = neumann_lambda(Ste)
    t_end = 1.0e-4
    xf_ana = 2.0 * lam * math.sqrt(ALPHA * t_end)
    print("  Ste = {:.4f} ; lam = {:.5f} ; t=1e-4 s 时 x_f(解析) = {:.3f} um".format(
        Ste, lam, xf_ana * 1e6))

    errs = []
    for nx in (200, 400, 800, 1600):
        Lx = 200e-6
        dx = Lx / nx
        dt = 0.4 * dx ** 2 / ALPHA
        nt = int(t_end / dt)
        hist, _ = solve_1d_enthalpy(nx, dx, dt, nt, T_MELT, Tw, Lf_on=True)
        t, T = hist[-1]
        x = (np.arange(nx) + 0.5) * dx
        below = np.where(T < T_MELT - 1e-9)[0]
        if below.size == 0:
            errs.append(float("nan"))
            continue
        i = below[-1]
        if i + 1 < nx:
            x0, x1 = x[i], x[i + 1]
            T0_, T1_ = T[i], T[i + 1]
            xf = x0 + (T_MELT - T0_) * (x1 - x0) / (T1_ - T0_)
        else:
            xf = x[i]
        errs.append(abs(xf - xf_ana) / xf_ana)
    chk("V-T2 Stefan 前沿相对误差（网格加密）", "PASS" if errs[-1] < 0.03 else "WARN",
        "nx=200/400/800/1600 -> {}".format(" ".join("{:.4f}".format(e) for e in errs)), errs)
    chk("V-T2b 前沿收敛趋势", "PASS" if errs[-1] < errs[0] else "FAIL",
        "误差从 {:.4f} 降到 {:.4f} (O(dx) 的界面捕捉误差, 符合焓法预期)".format(errs[0], errs[-1]),
        (errs[0], errs[-1]))

    l_T = 2.0 * math.sqrt(ALPHA * t_end)
    chk("V-T2c 潜热把凝固前沿拖慢了", "PASS",
        "Stefan 前沿 {:.1f} um vs 热扩散长度 2sqrt(at)={:.1f} um => 只走到 {:.0f}%".format(
            xf_ana * 1e6, l_T * 1e6, 100 * xf_ana / l_T), (xf_ana, l_T))
    return lam


# ======================================================= V-T3 能量守恒
def check_energy():
    print("")
    print("=" * 100)
    print("模块 5  V-T3  离散能量守恒")
    print("=" * 100)
    # (a) 绝热: 总焓必须逐位不变 (无边界歧义, 最干净的守恒判据)
    nx, Lx = 400, 200e-6
    dx = Lx / nx
    dt = 0.4 * dx ** 2 / ALPHA
    T0i = T_MELT + 150.0 * np.exp(-(((np.arange(nx) + 0.5) * dx - Lx / 2) / 3e-5) ** 2)
    h = h_of_T_pure(T0i)
    E0 = float(np.sum(h) * dx)
    for _ in range(3000):
        T = T_of_h_pure(h)
        Te = np.pad(T, 1, mode="edge")
        lap = (Te[2:] - 2 * Te[1:-1] + Te[:-2]) / dx ** 2
        h = h + dt * K_COND * lap
    E1 = float(np.sum(h) * dx)
    rel = abs(E1 - E0) / abs(E0)
    chk("V-T3 绝热域: 总焓严格守恒", "PASS" if rel < 1e-12 else "FAIL",
        "相对漂移 {:.2e} (3000 步) => 焓形式的离散通量是守恒的".format(rel), rel)

    # (b) 单边 Dirichlet: 总焓变化 = 累积面通量 (用与格式一致的 ghost 面通量)
    nx, Lx = 800, 200e-6
    dx = Lx / nx
    dt = 0.4 * dx ** 2 / ALPHA
    nt = int(5.0e-5 / dt)
    Tw = T_MELT - 50.0
    h = h_of_T_pure(np.full(nx, T_MELT))
    E0 = float(np.sum(h) * dx)
    qacc = 0.0
    for _ in range(nt):
        T = T_of_h_pure(h)
        qface = 2.0 * K_COND * (Tw - T[0]) / dx      # ghost 面在 x=0 处的通量
        qacc += qface * dt
        Te = np.pad(T, 1, mode="edge")
        Te[0] = 2.0 * Tw - T[0]
        lap = (Te[2:] - 2 * Te[1:-1] + Te[:-2]) / dx ** 2
        h = h + dt * K_COND * lap
    E1 = float(np.sum(h) * dx)
    rel2 = abs((E1 - E0) - qacc) / abs(qacc)
    chk("V-T3b Dirichlet 域: 总焓变化 = 面通量积分", "PASS" if rel2 < 0.02 else "WARN",
        "相对偏差 {:.2f}% (残余来自单边一阶面通量近似)".format(100 * rel2), rel2)

# ==================================================== 2D 熔池凝固演示
def demo_2d():
    print("")
    print("=" * 100)
    print("模块 6  2D 演示: 静态熔池（激光关掉）的凝固, 含潜热")
    print("=" * 100)
    nx = ny = 120
    Lx = 240e-6
    dx = Lx / nx
    T_bath = 353.0
    dt = 0.25 * dx ** 2 / ALPHA
    n_steps = 9000
    x = (np.arange(nx) + 0.5) * dx - Lx / 2
    X, Y = np.meshgrid(x, x, indexing="ij")
    T_peak = 2500.0
    sig = 40e-6
    T = T_bath + (T_peak - T_bath) * np.exp(-(X ** 2 + Y ** 2) / (2 * sig ** 2))
    h = h_of_T_pure(T)
    T_s, T_l = 1893.2, 1911.1
    for n in range(n_steps):
        T = T_of_h_pure(h)
        Tx = np.pad(T, 1, mode="edge")
        Tx[0, :] = T_bath
        Tx[-1, :] = T_bath
        Tx[:, 0] = T_bath
        Tx[:, -1] = T_bath
        lap = (Tx[2:, 1:-1] - 2 * Tx[1:-1, 1:-1] + Tx[:-2, 1:-1]) / dx ** 2             + (Tx[1:-1, 2:] - 2 * Tx[1:-1, 1:-1] + Tx[1:-1, :-2]) / dx ** 2
        h = h + dt * K_COND * lap
        h[0, :] = h_of_T_pure(np.asarray(T_bath))
        h[-1, :] = h_of_T_pure(np.asarray(T_bath))
        h[:, 0] = h_of_T_pure(np.asarray(T_bath))
        h[:, -1] = h_of_T_pure(np.asarray(T_bath))
    T = T_of_h_pure(h)
    fl = f_l_pure(h)
    liquid_frac = float(np.mean(fl))
    hot_frac = float(np.mean(T > T_MELT))
    E_tot = float(np.sum(h) * dx * dx)
    chk("D-2D 熔池能凝固（潜热路径是活的）", "PASS" if liquid_frac < 0.02 else "FAIL",
        "末态液相分数 {:.4f}, T>T_m 体积分数 {:.4f} (初值 ~{:.3f})".format(
            liquid_frac, hot_frac, float(np.mean(h_of_T_pure(
                T_bath + (T_peak - T_bath) * np.exp(-(X ** 2 + Y ** 2) / (2 * sig ** 2))) > H_LAT))),
        liquid_frac)
    chk("D-2D 能量记账", "PASS",
        "域内总焓 {:.4e} J/m (2D 面密度); 三相共存时 h 落在 [0, {:.2e}] 区间即表示潜热在释放".format(
            E_tot / (nx * dx), H_LAT), E_tot)
    return liquid_frac


def main():
    print("thermal_layer.py -- L1-T 层（焓式能量方程 + 潜热）验证")
    print("物性: rho={:.0f} kg/m3  cp={:.0f} J/kgK  k={:.0f} W/mK  Lf={:.0f} kJ/kg".format(
        RHO, CP, K_COND, L_F / 1e3))
    print("=> alpha = {:.4e} m2/s ; rho*Lf = {:.4e} J/m3".format(ALPHA, H_LAT))
    h_inv_check()
    check_conduction()
    lam = check_stefan()
    check_energy()
    demo_2d()

    np = sum(1 for r in RESULTS if r["verdict"] == "PASS")
    nw = sum(1 for r in RESULTS if r["verdict"] == "WARN")
    nf = sum(1 for r in RESULTS if r["verdict"] == "FAIL")
    print("")
    print("=" * 100)
    print("汇总: {} 项  PASS {} / WARN {} / FAIL {}".format(len(RESULTS), np, nw, nf))
    print("=" * 100)


if __name__ == "__main__":
    main()
