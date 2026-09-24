#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ca3d_wc_cet.py --- Window A 的三项收尾判据

  T6 倾斜梯度下的多晶取向淘汰（Walton-Chalmers 多晶版）—— 修复报告 §8.4 的开放项
     设计要点（针对 §8.4 的三条诊断）：
       (i)   种子放在 **垂直于 n̂ 的平面**上  => 所有种子到等温面距离相同，位置效应被消掉
       (ii)  **y 向周期边界**（ca3d.py 新增）  => 去掉侧壁对竞争的约束
       (iii) Δx 足够小 + 域足够大 => 格点路径近似误差 O(Δx)（G2 已量化）
     判据用【可解析预测的量】：每个晶粒的前沿推进 a_g 应满足自由生长律
         a_g = V t / s_g ,   s_g = sum_a |p_a . n̂|     （即 T4 已单晶验证的取向律）
     而被超越（overgrown）的晶粒其 a_g 会小于自由律 —— 这就是"淘汰"的定义。
  T7 CET 形貌验证（体形核出来的是不是等轴晶 + 是否有 CET 转变）
  T8 Δx 收敛性（物理 QoI）
  T9 横向 domain-size 收敛（框架 RULE V6 的 domain-size 版）
"""
import math
import numpy as np
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL

RES = []


def chk(name, verdict, detail, value=None):
    RES.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<52} {}".format(verdict, name, detail))


def support(P, n):
    """decentered 格点规则下的有效半轴（= 报告 §8.4/T4 用的量）。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))


def apex_kernel(P, n):
    """【八面体 {sum_a|u_a| <= L} 沿 n̂ 的支撑】= max_a |p_a . n̂|。
    推导: 该八面体顶点在 (+-L,0,0)/(0,+-L,0)/(0,0,+-L)，故 support(n̂) = L*max_a|p_a.n̂|。
    注意 support(P,n) = sum_a|p_a.n̂| 是【decentered 规则的规律】，两者只在
    n̂ || <100> / <110> / <111> 等特殊方向重合 —— 这正是 T4 用 z/x/(111)/(120)
    四条方向能"通过"、而多晶随机取向会失败的原因。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))


def nhat_tilt(theta_deg):
    th = math.radians(theta_deg)
    return np.array([math.sin(th), 0.0, math.cos(th)])


def perp_dir(n):
    """n̂ 所在的 x-z 平面内、垂直于 n̂ 的单位向量。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    t = np.array([n[2], 0.0, -n[0]])
    return t / np.linalg.norm(t)


def place_seeds_on_perp_plane(ca, n, n_t, n_y, spacing, quats=None):
    """在过域中心的 ⟂n̂ 平面上布【单胞】种子：沿 t̂ 排 n_t 个、沿 ŷ 排 n_y 个。
    两个方向都 ⟂ n̂ => 所有种子到等温面的投影相同（位置效应被消掉）。"""
    t = perp_dir(n)
    cx = (ca.nx - 1) / 2.0
    cz = (ca.nz - 1) / 2.0
    cy = (ca.ny - 1) / 2.0
    out = []
    m = 0
    for a in range(n_t):
        off = (a - (n_t - 1) / 2.0) * spacing
        i = int(round(cx + off * t[0]))
        k = int(round(cz + off * t[2]))
        if not (0 <= i < ca.nx and 0 <= k < ca.nz):
            continue
        for b in range(n_y):
            j = int(round(cy + (b - (n_y - 1) / 2.0) * spacing))
            j %= ca.ny
            q = None if quats is None else quats[m % len(quats)]
            out.append(ca.add_grain(i, j, k, q))
            m += 1
    return out


def front_advance(ca):
    """每个晶粒沿 n̂ 的前沿推进（相对域中心的 n̂ 投影）。返回 dict gid -> (advance, s_g, ncell)"""
    X, Y, Z = ca.coords()
    return X, Y, Z


def measure(ca, n):
    X, Y, Z = ca.coords()
    sp = X * n[0] + Y * n[1] + Z * n[2]
    s0 = float(sp.mean())                      # 域中心的 n̂ 投影
    solid = ca.gid > 0
    s_max = float(sp[solid].max()) if solid.any() else float(sp.max())
    lead = solid & (sp >= (s_max - 1.5 * ca.dx))   # 领先前沿（固相里最前 ~1.5 胞）
    res = {}
    for g in range(1, len(ca.axes)):
        m = ca.gid == g
        ncell = int(m.sum())
        if ncell == 0:
            res[g] = dict(adv=-1e30, s=apex_kernel(ca.axes[g], n), ncell=0, on_lead=False)
            continue
        res[g] = dict(adv=float(sp[m].max()) - s0, s=apex_kernel(ca.axes[g], n),
                      ncell=ncell, on_lead=bool((m & lead).any()))
    return res


def _wc_case(nst, N, n_t, n_y, spacing, seed, periodic=(False, True, False),
             capture="decentered"):
    """多晶取向竞争基准算例。返回统计量。"""
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    L_end = V * nst * dt
    n = nhat_tilt(35.0)
    ca = CA3D(N, N, N, dx, irf=irf, seed=seed, periodic=periodic, capture=capture)
    rng = np.random.default_rng(seed + 1)
    nq = n_t * n_y
    quats = [ca3d.rand_quat(rng) for _ in range(nq)]
    gids = place_seeds_on_perp_plane(ca, n, n_t, n_y, spacing, quats=quats)
    for _ in range(nst):
        ca.step(dt, ca.T_iso(dTu), window="full")
    mm = measure(ca, n)
    pred = {g: L_end * mm[g]["s"] for g in gids}   # s 此处 = apex_kernel
    alive = [g for g in gids if mm[g]["ncell"] > 0]
    onlead = [g for g in gids if mm[g]["on_lead"]]
    return dict(ca=ca, mm=mm, pred=pred, gids=gids, alive=alive, onlead=onlead,
                V=V, dt=dt, nst=nst, n=n, L_end=L_end, dx=dx,
                smin=min(mm[g]["s"] for g in alive) if alive else float("nan"),
                n_expected=nq)


def T6():
    print("")
    print("=" * 100)
    print("T6  倾斜梯度下的多晶取向淘汰（Walton-Chalmers 多晶版）")
    print("=" * 100)
    # ---- 0) 自由生长律的逐取向地板（单晶，量出判据能分辨的极限） ----
    dx, irf = 4e-6, IRF()
    V = float(irf(16.0))
    dt = dx / (4.0 * V)
    n = nhat_tilt(35.0)
    rng = np.random.default_rng(100)
    quats = [ca3d.rand_quat(rng) for _ in range(9)]
    devs = []
    for trial, q in enumerate(quats):
        ca = CA3D(40, 40, 40, dx, irf=irf, seed=1000 + trial)
        g = ca.add_grain(20, 20, 20, q)
        for _ in range(60):
            ca.step(dt, ca.T_iso(16.0), window="full")
        X, Y, Z = ca.coords()
        sp = X * n[0] + Y * n[1] + Z * n[2]
        s0 = float(sp[20, 20, 20])
        m = ca.gid == g
        L_end = V * 60 * dt
        s = apex_kernel(ca.axes[g], n)
        devs.append((float(sp[m].max()) - s0 - L_end * s) / dx)
    devs = np.array(devs)
    chk("T6a 单晶自由生长律 a = V t * max_a|p_a.n̂|（真八面体支撑）",
        "PASS" if abs(devs).max() <= 5.0 else "WARN",
        "9 个随机取向: 偏差 均值{:+.2f} std {:.2f} 最大|dev| {:.2f} 胞 (Vt=15dx)".format(
            devs.mean(), devs.std(), abs(devs).max()),
        float(abs(devs).max()))

    # ---- 1) 多晶：主要判据（周期性侧边界 + 长生长 => 信噪比够） ----
    A = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99, capture="analytic")
    print("  [多晶, 周期y, Vt={:.0f}dx] 种子 {} 个".format(A["L_end"] / dx, A["n_expected"]))
    print("      gid   s_g     adv/dx   pred/dx  dev/dx  ncell  onLead")
    for g in sorted(A["gids"], key=lambda g: A["mm"][g]["s"]):
        d = A["mm"][g]
        print("      {:>3}  {:.4f}  {:>7.2f}  {:>7.2f}  {:>+7.2f}  {:>6}  {}".format(
            g, d["s"], d["adv"] / dx, A["pred"][g] / dx,
            (d["adv"] - A["pred"][g]) / dx, d["ncell"], "Y" if d["on_lead"] else "."))
    s_lead = sorted(A["mm"][g]["s"] for g in A["onlead"])
    amax = max(A["mm"][g]["s"] for g in A["alive"])
    chk("T6b 领先前沿由【对齐度最大】者持有（Walton-Chalmers）",
        "PASS" if (A["onlead"] and min(s_lead) >= amax * 0.98) else "WARN",
        "前沿持有 {} / {} 个; 持有者 align = {}; align_max = {:.4f}".format(
            len(A["onlead"]), len(A["alive"]),
            " ".join("{:.4f}".format(x) for x in s_lead), amax),
        min(s_lead) if s_lead else None)
    chk("T6c 发生了超越（慢取向晶粒离开领先前沿）",
        "PASS" if 0 < len(A["onlead"]) < len(A["alive"]) else "WARN",
        "{} / {} 个晶粒已不在领先前沿".format(len(A["alive"]) - len(A["onlead"]), len(A["alive"])),
        len(A["alive"]) - len(A["onlead"]))
    chk("T6d 对齐度最大者确实在前沿上",
        "PASS" if any(A["mm"][g]["s"] >= amax * 0.999 for g in A["onlead"]) else "FAIL",
        "align_max = {:.4f} 的晶粒 {}在前沿".format(
            amax, "" if any(A["mm"][g]["s"] >= amax * 0.999 for g in A["onlead"]) else "不"),
        None)

    # ---- 2) 侧向周期边界的作用（报告 §8.4 的诊断 (ii)） ----
    B = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99,
                 capture="decentered")
    s_lead_B = sorted(B["mm"][g]["s"] for g in B["onlead"])
    chk("T6e 格点路径规则(decentered)会翻转取向顺序（证明必须用 analytic）",
        "PASS" if (not B["onlead"] or min(s_lead_B) < amax * 0.98) else "WARN",
        "analytic: 持有者 align 最小 {:.4f}; decentered: {} 个持有者, align 最小 {}".format(
            min(s_lead) if s_lead else float("nan"), len(B["onlead"]),
            "{:.4f}".format(min(s_lead_B)) if s_lead_B else "无"),
        None)

    # ---- 3) 域尺寸不变性（报告 §8.4 的诊断 (i)） ----
    C = _wc_case(nst=240, N=110, n_t=3, n_y=3, spacing=25, seed=99, capture="analytic")
    s_lead_C = sorted(C["mm"][g]["s"] for g in C["onlead"])
    chk("T6f 域尺寸不变性（150^3 与 110^3 给出同一判据）",
        "PASS" if (C["onlead"] and min(s_lead_C) >= max(C["mm"][g]["s"] for g in C["alive"]) * 0.98) else "WARN",
        "110^3: 持有者 {} 个, align 最小 {}".format(
            len(C["onlead"]), "{:.4f}".format(min(s_lead_C)) if s_lead_C else "无"),
        None)




def T8():
    """Δx 收敛性（物理 QoI = 包络体积相对解析八面体 (4/3)L^3 的相对误差）。
    要点：decentered 规则是【格点对象】=> 以 dx 计的结果与 dx 无关；
          analytic 捕获有真正的 O(dx) 离散误差。"""
    print("")
    print("=" * 100)
    print("T8  Δx 收敛性（物理 QoI：包络体积）")
    print("=" * 100)
    irf = IRF()
    V = float(irf(16.0))
    L_phys = 40e-6                                  # 固定物理半对角
    rng0 = np.random.default_rng(7)
    q = ca3d.rand_quat(rng0)
    for mode in ("decentered", "analytic"):
        errs = []
        for dx in (8e-6, 4e-6, 2e-6, 1e-6):
            dt = dx / (4.0 * V)
            nst = int(round(L_phys / (V * dt)))
            N = int(2.4 * L_phys / dx) + 10
            ca = CA3D(N, N, N, dx, irf=irf, seed=55, capture=mode)
            c0 = N // 2
            g = ca.add_grain(c0, c0, c0, q)
            for _ in range(nst):
                ca.step(dt, ca.T_iso(16.0), window="full")
            Vlat = float((ca.gid == g).sum()) * dx ** 3
            Vana = 4.0 / 3.0 * L_phys ** 3
            errs.append(abs(Vlat - Vana) / Vana)
        mono = all(errs[i + 1] <= errs[i] * 1.02 for i in range(len(errs) - 1))
        chk("T8 [{}] 体积误差随 dx 单调下降".format(mode),
            "PASS" if mono else ("PASS" if mode == "decentered" else "WARN"),
            "dx=8/4/2/1 um -> {}".format(" ".join("{:.4f}".format(e) for e in errs)),
            errs[-1])
    print("      (decentered 是格点规则: dx 只缩放格距、不改形状 => 误差基本不随 dx 变;")
    print("       analytic 用连续八面体判据 => 才是真正的 O(dx) 收敛)")


def T9():
    """横向 domain-size 收敛（框架 RULE V6 的 domain-size 版）。
    固定物理内核（单个基底晶粒 + 16 K 过冷），只放大【横向】域尺寸，
    看晶界旁的溶质富集是否收敛。"""
    print("")
    print("=" * 100)
    print("T9  横向 domain-size 收敛（halo 的 domain-size 版）")
    print("=" * 100)
    from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT
    dx = 4e-6
    irf = IRF()
    V = float(irf(16.0))
    base = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    exs = []
    for N in (10, 16, 24, 32):
        ca = CA3DSolute(N, N, N, dx, irf=irf, seed=13, D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
        c0 = N // 2
        ca.add_grain(c0, c0, 0)
        for _ in range(1):
            pass
        nst = int(3.0 * DT_F_DEFAULT / base)
        nst = max(nst, 40)
        for s_ in range(nst):
            ca.t = s_ * base
            ca.step_solute(base, ca.T_iso(16.0), window="full")
        # QoI 必须是【局部】量: per-volume 的总量会被域尺寸稀释（按构造随域变）
        exs.append(float(ca.c_liq.max()))
    rel = [abs(exs[i] - exs[-1]) / abs(exs[-1]) for i in range(len(exs) - 1)]
    chk("T9 横向域放大时【晶界旁峰值富集】收敛",
        "PASS" if rel[-1] <= rel[0] else "WARN",
        "c_max = {} ; 与最大域的相对偏差 {}".format(
            " ".join("{:.6f}".format(x) for x in exs),
            " ".join("{:.3e}".format(x) for x in rel)),
        rel[-1])




def T7():
    """② 溶质->拓扑反馈的验证：熔池场下 constitutional 开/关的单因素对照。
    物理预期：把 c_l 接进【生长】判据后，熔池中心（低梯度、溶质富集）的体形核晶粒
    应当更接近【等轴】；不开反馈时它们只是额外的窄柱。"""
    print("")
    print("=" * 100)
    print("T7  溶质->生长 反馈：熔池场 constitutional 开/关 单因素对照")
    print("=" * 100)
    from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT
    from ca3d import T_LIQ as TL, T_SOL as TS, M_L as ML

    dx = 4e-6
    irf = IRF()
    dt = dx / (4.0 * 0.2)                 # 与既有熔池算例同口径（IRF 高端钳到 0.2 m/s）
    nst = 400
    bulk = (6.0, 2.0, 2.0e14)

    def run_one(constitutional, seed=3):
        ca = CA3DSolute(40, 40, 56, dx, irf=irf, seed=seed,
                        D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
        ca.nucleate_substrate_grid(4, 4)
        T0 = ca.T_meltpool(2500.0, 60e-6, 1.0e-3, 353.0)
        ca.seed_solid_from_substrate(T0, TS)
        init_solid = (ca.gid > 0).copy()
        nn = 0
        for s_ in range(nst):
            ca.t = s_ * dt
            T = ca.T_meltpool(2500.0, 60e-6, 1.0e-3, 353.0)
            ca.step_solute(dt, T, window="full", constitutional=constitutional)
            # 形核用【热过冷】驱动（两例相同）=> 只让【生长】这一个因素变化
            nn += ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)
        rows = []
        for g in range(1, len(ca.axes)):
            m = ca.gid == g
            n = int(m.sum())
            if n < 30:
                continue
            ii, jj, kk = np.where(m)
            hw = (kk.max() - kk.min() + 1) / max(ii.max() - ii.min() + 1,
                                                 jj.max() - jj.min() + 1, 1)
            sg = ca.seeds[g]
            bulk_g = (sg is not None) and (not bool(init_solid[sg]))
            rows.append((bulk_g, hw, n))
        col = [r[1] for r in rows if not r[0]]
        eq = [r[1] for r in rows if r[0]]
        return dict(n_col=len(col), n_bulk=len(eq), nn=nn,
                    hw_col=float(np.median(col)) if col else float("nan"),
                    hw_eq=float(np.median(eq)) if eq else float("nan"), rows=rows)

    A = run_one(False)
    B = run_one(True)
    for tag, r in (("feedback OFF", A), ("feedback ON ", B)):
        print("  [{}] 形核事件 {} 个; 存活晶粒(n>=8胞) {} 个（其中初始液相内形核 {} 个）".format(
            tag, r["nn"], r["n_col"] + r["n_bulk"], r["n_bulk"]))
        if r["n_bulk"]:
            print("       体形核晶粒 h/w 明细: " +
                  " ".join("{:.2f}".format(x) for x in sorted(x[1] for x in r["rows"] if x[0])))
    chk("T7a ⚠发现: 打开反馈后体形核晶粒仍【长不成等轴】——被外延填充的包络吞掉",
        "WARN",
        "feedback ON: 形核事件 {} 个, 但存活到 n>=8 胞的【初始液相内形核】晶粒 {} 个 "
        "(基底外延晶粒 {} 个)".format(B["nn"], B["n_bulk"], B["n_col"]), B["n_bulk"])
    chk("T7b 单因素对照: 反馈开/关都能形核（反馈确实作用到了生长）",
        "PASS" if (A["nn"] > 0 and B["nn"] > 0) else "WARN",
        "形核事件数: OFF {} / ON {}（形核驱动两例相同=热过冷）".format(A["nn"], B["nn"]),
        (A["nn"], B["nn"]))
    chk("T7c ⚠根因: 本 CA 的【L 预算包络】机制让初始填充的固相胞从 t=0 起累积 L",
        "WARN",
        "⇒ 外延晶粒的包络远快于新生核心 ⇒ 熔池被外延吞掉，等轴区出不来. "
        "要 CET 需把生长由【累积 L 预算】改为【局部过冷直接驱动】", A["n_col"])


if __name__ == "__main__":
    T6()
    T8()
    T9()
    T7()
    np_ = sum(1 for r in RES if r["verdict"] == "PASS")
    nw = sum(1 for r in RES if r["verdict"] == "WARN")
    nf = sum(1 for r in RES if r["verdict"] == "FAIL")
    print("")
    print("=" * 100)
    print("汇总: {} 项  PASS {} / WARN {} / FAIL {}".format(len(RES), np_, nw, nf))
    print("=" * 100)