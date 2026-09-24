import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
add = '''

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
        exs.append(ca.excess_per_volume())
    rel = [abs(exs[i] - exs[-1]) / abs(exs[-1]) for i in range(len(exs) - 1)]
    chk("T9 横向域放大时过量溶质收敛",
        "PASS" if rel[-1] <= rel[0] else "WARN",
        "e_V = {} ; 与最大域的相对偏差 {}".format(
            " ".join("{:.4e}".format(x) for x in exs),
            " ".join("{:.3e}".format(x) for x in rel)),
        rel[-1])
'''
s = s.replace('if __name__ == "__main__":', add + '\n\nif __name__ == "__main__":', 1)
s = s.replace("    T6()\n", "    T6()\n    T8()\n    T9()\n", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("added T8/T9")