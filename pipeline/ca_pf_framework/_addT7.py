import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
add = '''

def T7():
    """CET 体形核：形貌验证 + 【成分过冷 vs 热过冷】两种驱动量对照。"""
    print("")
    print("=" * 100)
    print("T7  CET：等轴晶形貌 + 成分过冷(ΔT_CS)与热过冷(ΔT)两种驱动量对照")
    print("=" * 100)
    from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT
    from ca3d import T_LIQ as TL, M_L as ML, C0_V as C0
    dx = 4e-6
    irf = IRF()
    G = 5.0e5
    V = float(irf(16.0))
    v_pull = V
    dt = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    nst = 240
    bulk = (12.0, 4.0, 4.0e15)      # (dT_mean, dT_sigma, N_max)  [A] 演示参数

    def run_one(driver, seed=5):
        ca = CA3DSolute(40, 40, 52, dx, irf=irf, seed=seed,
                        D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
        ca.nucleate_substrate_grid(4, 4)
        nseed0 = len(ca.axes) - 1
        for s_ in range(nst):
            ca.t = s_ * dt
            T = ca.T_directional(G, v_pull, z0=0.0)
            ca.step_solute(dt, T, window="full")
            if driver == "constitutional":
                ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt,
                                 c_l=ca.c_liq, m_L=ML)
            else:
                ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)
        return ca, nseed0

    res = {}
    for drv in ("thermal", "constitutional"):
        ca, nseed0 = run_one(drv)
        rows = []
        for g in range(1, len(ca.axes)):
            m = ca.gid == g
            n = int(m.sum())
            if n < 20:
                continue
            ii, jj, kk = np.where(m)
            hw = (kk.max() - kk.min() + 1) / max(ii.max() - ii.min() + 1,
                                                 jj.max() - jj.min() + 1, 1)
            sz = ca.seeds[g][2]
            rows.append((sz, hw, n, g))
        col = [r[1] for r in rows if r[0] == 0]
        eq = [r[1] for r in rows if r[0] > 0]
        zmax_bulk = max([r[0] for r in rows if r[0] > 0], default=0)
        res[drv] = dict(n_bulk=len(eq), col=col, eq=eq, zmax=zmax_bulk,
                        hw_col=float(np.median(col)) if col else float("nan"),
                        hw_eq=float(np.median(eq)) if eq else float("nan"))
        print("  [{:14s}] 基底柱状 {} 个 (h/w 中位 {:.2f}); 体形核 {} 个 (h/w 中位 {}), 最高种子层 k={}".format(
            drv, len(col), res[drv]["hw_col"], len(eq),
            "{:.2f}".format(res[drv]["hw_eq"]) if eq else "无", zmax_bulk))

    A, B = res["thermal"], res["constitutional"]
    chk("T7a 体形核晶粒是【等轴】、基底晶粒是【柱状】（形貌对照）",
        "PASS" if (A["eq"] and A["hw_eq"] <= 2.0 and A["hw_col"] >= 2.0) else "WARN",
        "thermal 驱动: 等轴 h/w 中位 {:.2f} vs 柱状 {:.2f}".format(A["hw_eq"], A["hw_col"]),
        A["hw_eq"] if A["eq"] else None)
    chk("T7b 成分过冷驱动能形核到更高处（热前沿【之前】也能形核）",
        "PASS" if B["zmax"] > A["zmax"] else "WARN",
        "最高种子层: thermal k={} vs constitutional k={} (域高 {} 层)".format(
            A["zmax"], B["zmax"], 52), B["zmax"])
    chk("T7c 成分过冷驱动给出更多体形核（CET 更强）",
        "PASS" if B["n_bulk"] > A["n_bulk"] else "WARN",
        "体形核数: thermal {} vs constitutional {}".format(A["n_bulk"], B["n_bulk"]),
        B["n_bulk"])
'''
s = s.replace('if __name__ == "__main__":', add + '\n\nif __name__ == "__main__":', 1)
s = s.replace("    T6()\n    T8()\n    T9()\n", "    T6()\n    T8()\n    T9()\n    T7()\n", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("added T7")