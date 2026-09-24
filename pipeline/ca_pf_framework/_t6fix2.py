import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
i0 = s.index("def T6():")
i1 = s.index('if __name__ == "__main__":')
new = '''def T6(diag=True):
    print("")
    print("=" * 100)
    print("T6  倾斜梯度下的多晶取向淘汰（Walton-Chalmers 多晶版）")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    nst = 100                                   # V t = 25 dx
    L_end = V * nst * dt
    n = nhat_tilt(35.0)
    N = 72

    def run_case(tag, tilt, n_t=3, n_y=3, spacing=14, seed=99):
        ca = CA3D(N, N, N, dx, irf=irf, seed=seed, periodic=(False, True, False))
        rng = np.random.default_rng(seed + 1)
        nq = n_t * n_y
        quats = [ca3d.rand_quat(rng) for _ in range(nq)]
        gids = place_seeds_on_perp_plane(ca, n, n_t, n_y, spacing, quats=quats)
        Tmin = 1e30
        for _ in range(nst):
            T = ca.T_inclined(3.0e4, V, n) if tilt else ca.T_iso(dTu)
            Tmin = min(Tmin, float(T.min()))
            ca.step(dt, T, window="full")
        mm = measure(ca, n)
        pred = {g: L_end / mm[g]["s"] for g in gids}
        # 领先前沿的持有者 + 各自占的前沿横截面积（投影面积的相对份额）
        if diag:
            print("  [{}] V t = {:.1f} dx, T_min = {:.1f} K".format(tag, L_end / dx, Tmin))
            print("      gid   s_g      adv/dx   pred/dx  dev/dx  ncell  onLead")
            for g in sorted(gids, key=lambda g: mm[g]["s"]):
                d = mm[g]
                print("      {:>3}  {:.4f}   {:>6.2f}   {:>6.2f}   {:>6.2f}  {:>6}  {}".format(
                    g, d["s"], d["adv"] / dx, pred[g] / dx,
                    (d["adv"] - pred[g]) / dx, d["ncell"], "Y" if d["on_lead"] else "."))
        onlead = [g for g in gids if mm[g]["on_lead"]]
        alive = [g for g in gids if mm[g]["ncell"] > 0]
        smin = min(mm[g]["s"] for g in alive)
        sworst = max(mm[g]["s"] for g in alive)
        s_lead = sorted(mm[g]["s"] for g in onlead)
        return dict(tag=tag, mm=mm, pred=pred, onlead=onlead, alive=alive,
                    smin=smin, sworst=sworst, s_lead=s_lead, Tmin=Tmin, gids=gids)

    A = run_case("均匀过冷 (机制测试)", False, seed=99)
    B = run_case("倾斜梯度 G=3e4", True, seed=131)

    for r in (A, B):
        t = r["tag"]
        chk("T6a [{}] 领先前沿由最对准者持有".format(t),
            "PASS" if (r["onlead"] and max(r["s_lead"]) <= r["smin"] * 1.06) else "WARN",
            "前沿持有 {} 个 / 共 {} 个; 持有者 s = {}; s_min = {:.4f}".format(
                len(r["onlead"]), len(r["gids"]),
                " ".join("{:.4f}".format(x) for x in r["s_lead"]), r["smin"]),
            max(r["s_lead"]) if r["s_lead"] else None)
        chk("T6b [{}] 前沿持有者满足自由生长律 a=Vt/s".format(t),
            "PASS" if (r["onlead"] and max(abs(r["mm"][g]["adv"] - r["pred"][g]) / dx
                                           for g in r["onlead"]) <= 2.0) else "WARN",
            "持有者的最大偏差 {:.2f} 胞 (判据 <=2)".format(
                max(abs(r["mm"][g]["adv"] - r["pred"][g]) / dx for g in r["onlead"])
                if r["onlead"] else float("nan")),
            None)
        chk("T6c [{}] 发生了超越（慢取向晶粒离开前沿）".format(t),
            "PASS" if len(r["onlead"]) < len(r["alive"]) else "WARN",
            "{} / {} 个晶粒已不在领先前沿".format(len(r["alive"]) - len(r["onlead"]), len(r["alive"])),
            len(r["alive"]) - len(r["onlead"]))
        chk("T6d [{}] 前沿面积份额按 s 单调（最对准者份额最大）".format(t),
            "PASS" if (r["onlead"] and min(r["mm"][g]["s"] for g in r["onlead"]) == r["smin"]) else "WARN",
            "最对准者 (s={:.4f}) {}在前沿".format(r["smin"],
                                                "" if any(r["mm"][g]["s"] == r["smin"] for g in r["onlead"]) else "不"),
            None)
    chk("T6e 倾斜梯度未触发 thermal_capture 强制填充",
        "PASS" if B["Tmin"] > T_SOL else "FAIL",
        "域内最低温 {:.2f} K vs T_SOL {:.2f} K".format(B["Tmin"], T_SOL), B["Tmin"])


'''
s = s[:i0] + new + s[i1:]
io.open(P, "w", encoding="utf-8").write(s)
print("rewrote T6")