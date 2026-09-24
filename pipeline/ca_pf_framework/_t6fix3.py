import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
i0 = s.index("def T6(")
i1 = s.index('if __name__ == "__main__":')
new = '''def _wc_case(nst, N, n_t, n_y, spacing, seed, periodic=(False, True, False), quiet=True):
    """多晶取向竞争基准算例。返回统计量。"""
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    L_end = V * nst * dt
    n = nhat_tilt(35.0)
    ca = CA3D(N, N, N, dx, irf=irf, seed=seed, periodic=periodic)
    rng = np.random.default_rng(seed + 1)
    nq = n_t * n_y
    quats = [ca3d.rand_quat(rng) for _ in range(nq)]
    gids = place_seeds_on_perp_plane(ca, n, n_t, n_y, spacing, quats=quats)
    for _ in range(nst):
        ca.step(dt, ca.T_iso(dTu), window="full")
    mm = measure(ca, n)
    pred = {g: L_end / mm[g]["s"] for g in gids}
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
        s = support(ca.axes[g], n)
        devs.append((float(sp[m].max()) - s0 - L_end / s) / dx)
    devs = np.array(devs)
    chk("T6a 单晶自由生长律 a = V t / s（量出格点路径近似的地板）",
        "PASS" if abs(devs).max() <= 3.0 else "WARN",
        "9 个随机取向: 偏差 均值{:+.2f} std {:.2f} 最大|dev| {:.2f} 胞 (Vt=15dx)".format(
            devs.mean(), devs.std(), abs(devs).max()),
        float(abs(devs).max()))

    # ---- 1) 多晶：主要判据（周期性侧边界 + 长生长 => 信噪比够） ----
    A = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99)
    print("  [多晶, 周期y, Vt={:.0f}dx] 种子 {} 个".format(A["L_end"] / dx, A["n_expected"]))
    print("      gid   s_g     adv/dx   pred/dx  dev/dx  ncell  onLead")
    for g in sorted(A["gids"], key=lambda g: A["mm"][g]["s"]):
        d = A["mm"][g]
        print("      {:>3}  {:.4f}  {:>7.2f}  {:>7.2f}  {:>+7.2f}  {:>6}  {}".format(
            g, d["s"], d["adv"] / dx, A["pred"][g] / dx,
            (d["adv"] - A["pred"][g]) / dx, d["ncell"], "Y" if d["on_lead"] else "."))
    s_lead = sorted(A["mm"][g]["s"] for g in A["onlead"])
    chk("T6b 领先前沿由最对准者持有（淘汰后只留 best）",
        "PASS" if (A["onlead"] and max(s_lead) <= A["smin"] * 1.05) else "WARN",
        "前沿持有 {} / {} 个; 持有者 s = {}; s_min = {:.4f}".format(
            len(A["onlead"]), len(A["alive"]),
            " ".join("{:.4f}".format(x) for x in s_lead), A["smin"]),
        max(s_lead) if s_lead else None)
    chk("T6c 发生了超越（慢取向晶粒离开领先前沿）",
        "PASS" if 0 < len(A["onlead"]) < len(A["alive"]) else "WARN",
        "{} / {} 个晶粒已不在领先前沿".format(len(A["alive"]) - len(A["onlead"]), len(A["alive"])),
        len(A["alive"]) - len(A["onlead"]))
    chk("T6d 最对准者确实在前沿上",
        "PASS" if any(A["mm"][g]["s"] <= A["smin"] * 1.001 for g in A["onlead"]) else "FAIL",
        "s_min = {:.4f} 的晶粒 {}在前沿".format(
            A["smin"], "" if any(A["mm"][g]["s"] <= A["smin"] * 1.001 for g in A["onlead"]) else "不"),
        None)

    # ---- 2) 侧向周期边界的作用（报告 §8.4 的诊断 (ii)） ----
    B = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99,
                 periodic=(False, False, False))
    s_lead_B = sorted(B["mm"][g]["s"] for g in B["onlead"])
    chk("T6e 关掉侧向周期边界后判据失效（证明周期边界是必需的修法）",
        "PASS" if (not B["onlead"] or max(s_lead_B) > A["smin"] * 1.05) else "WARN",
        "周期开: 持有者 s 最大 {:.4f}; 周期关: {} 个持有者, s 最大 {}".format(
            max(s_lead) if s_lead else float("nan"), len(B["onlead"]),
            "{:.4f}".format(max(s_lead_B)) if s_lead_B else "无"),
        None)

    # ---- 3) 域尺寸不变性（报告 §8.4 的诊断 (i)） ----
    C = _wc_case(nst=240, N=110, n_t=3, n_y=3, spacing=25, seed=99)
    s_lead_C = sorted(C["mm"][g]["s"] for g in C["onlead"])
    chk("T6f 域尺寸不变性（150^3 与 110^3 给出同一判据）",
        "PASS" if (C["onlead"] and max(s_lead_C) <= C["smin"] * 1.05) else "WARN",
        "110^3: 持有者 {} 个, s 最大 {}".format(
            len(C["onlead"]), "{:.4f}".format(max(s_lead_C)) if s_lead_C else "无"),
        None)


'''
s = s[:i0] + new + s[i1:]
io.open(P, "w", encoding="utf-8").write(s)
print("rewrote T6 v3")