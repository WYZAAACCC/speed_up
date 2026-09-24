import io
# 1) 默认改回 False
P2 = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d_solute.py"
s2 = io.open(P2, encoding="utf-8").read()
s2 = s2.replace("    def step_solute(self, dt, T, window=None, constitutional=True):",
                "    def step_solute(self, dt, T, window=None, constitutional=False):", 1)
s2 = s2.replace("        constitutional=True（默认）: 把上一步的 c_liq 接进【生长】判据（成分过冷）\n        —— 显式交错耦合（先几何、后化学；本步几何用的是上一步的 c_liq）。\"\"\"",
                "        constitutional: 是否把上一步的 c_liq 接进【生长】判据（成分过冷）。\n"
                "        默认 False => 历史行为逐位不变（既有算例可复现）。\n"
                "        物理上应当为 True（这是\"溶质 -> 拓扑\"的显式反馈）；开启会改变结果。\n"
                "        耦合是显式交错的（先几何、后化学），因此引入算子分裂误差：\n"
                "        未耦合时不可分辨，耦合后约 1.8%（见 verify_ca3d_physics.T5b）。\"\"\"", 1)
assert "constitutional=False" in s2 and "1.8%" in s2, "solute patch"
io.open(P2, "w", encoding="utf-8").write(s2)
print("default -> False")

# 2) 用熔池场重写 T7
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
i0 = s.index("def T7():")
i1 = s.index('if __name__ == "__main__":')
new = '''def T7():
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
    nst = 200
    bulk = (12.0, 4.0, 4.0e14)

    def run_one(constitutional, seed=3):
        ca = CA3DSolute(40, 40, 56, dx, irf=irf, seed=seed,
                        D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
        ca.nucleate_substrate_grid(4, 4)
        T0 = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
        ca.seed_solid_from_substrate(T0, TS)
        init_solid = (ca.gid > 0).copy()
        for s_ in range(nst):
            ca.t = s_ * dt
            T = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
            ca.step_solute(dt, T, window="full", constitutional=constitutional)
            ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt,
                             c_l=ca.c_liq, m_L=ML)
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
        return dict(n_col=len(col), n_bulk=len(eq),
                    hw_col=float(np.median(col)) if col else float("nan"),
                    hw_eq=float(np.median(eq)) if eq else float("nan"), rows=rows)

    A = run_one(False)
    B = run_one(True)
    for tag, r in (("feedback OFF", A), ("feedback ON ", B)):
        print("  [{}] 基底柱状 {} 个 (h/w 中位 {:.2f}); 体形核 {} 个 (h/w 中位 {})".format(
            tag, r["n_col"], r["hw_col"], r["n_bulk"],
            "{:.2f}".format(r["hw_eq"]) if r["n_bulk"] else "无"))
    chk("T7a 打开溶质->生长反馈后，体形核晶粒变【等轴】",
        "PASS" if (B["n_bulk"] and B["hw_eq"] <= 2.0) else "WARN",
        "feedback ON: 体形核 h/w 中位 {:.2f}（判据 <=2）; 基底柱状 {:.2f}".format(
            B["hw_eq"], B["hw_col"]), B["hw_eq"] if B["n_bulk"] else None)
    chk("T7b 反馈使体形核晶粒比【不开反馈】更接近等轴（单因素对照）",
        "PASS" if (B["n_bulk"] and A["n_bulk"] and B["hw_eq"] < A["hw_eq"]) else "WARN",
        "h/w 中位: OFF {:.2f} -> ON {:.2f}".format(A["hw_eq"], B["hw_eq"]),
        (A["hw_eq"], B["hw_eq"]))
    chk("T7c 对照: 不开反馈时体形核晶粒是【窄柱】（复现 §10.3 的发现）",
        "PASS" if (A["n_bulk"] and A["hw_eq"] > 2.0) else "WARN",
        "feedback OFF: 体形核 h/w 中位 {:.2f}".format(A["hw_eq"]),
        A["hw_eq"] if A["n_bulk"] else None)


'''
s = s[:i0] + new + s[i1:]
io.open(P, "w", encoding="utf-8").write(s)
print("rewrote T7 -> meltpool single-factor")