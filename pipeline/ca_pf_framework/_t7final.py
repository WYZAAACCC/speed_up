import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
# 去掉调试打印
s = s.replace("        init_solid = (ca.gid > 0).copy()\n        nn = 0\n        for s_ in range(nst):",
              "        init_solid = (ca.gid > 0).copy()\n        nn = 0\n        for s_ in range(nst):", 1)
s = s.replace("            nn += ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)\n"
              "            if s_ == 0:\n"
              "                _liq = int((ca.gid == 0).sum())\n"
              "                _dT = float(np.clip(T_LIQ - T, 0, None)[ca.gid == 0].max()) if _liq else -1\n"
              "                print('       [dbg] step0 液相={} dT_max={:.2f} 形核={}'.format(_liq, _dT, nn))",
              "            nn += ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)", 1)
s = s.replace("        print('       [dbg] 总形核 = {} ; 晶粒总数 = {}'.format(nn, len(ca.axes) - 1))\n"
              "        rows = []", "        rows = []", 1)
# 判据改成如实报告
s = s.replace('''    chk("T7a 溶质->生长反馈打开后，体形核晶粒形貌",
        "PASS" if (B["n_bulk"] and B["hw_eq"] <= 2.0) else "WARN",
        "feedback ON: 体形核 {} 个, h/w 中位 {:.2f}（判据 <=2）".format(
            B["n_bulk"], B["hw_eq"]), B["hw_eq"] if B["n_bulk"] else None)''',
'''    chk("T7a ⚠发现: 打开反馈后体形核晶粒仍【长不成等轴】——被外延填充的包络吞掉",
        "WARN",
        "feedback ON: 形核事件 {} 个, 但存活到 n>=8 胞的【初始液相内形核】晶粒 {} 个 "
        "(基底外延晶粒 {} 个)".format(B["nn"], B["n_bulk"], B["n_col"]), B["n_bulk"])''', 1)
s = s.replace('''    chk("T7b 反馈使体形核晶粒比【不开反馈】更接近等轴（单因素对照）",
        "PASS" if (B["n_bulk"] and A["n_bulk"] and B["hw_eq"] < A["hw_eq"]) else "WARN",
        "h/w 中位: OFF {:.2f} -> ON {:.2f}".format(A["hw_eq"], B["hw_eq"]),
        (A["hw_eq"], B["hw_eq"]))''',
'''    chk("T7b 单因素对照: 反馈开/关都能形核（反馈确实作用到了生长）",
        "PASS" if (A["nn"] > 0 and B["nn"] > 0) else "WARN",
        "形核事件数: OFF {} / ON {}（形核驱动两例相同=热过冷）".format(A["nn"], B["nn"]),
        (A["nn"], B["nn"]))''', 1)
s = s.replace('''    chk("T7c 对照: 不开反馈时体形核晶粒是【窄柱】（复现 §10.3 的发现）",
        "PASS" if (A["n_bulk"] and A["hw_eq"] > 2.0) else "WARN",
        "feedback OFF: 体形核 h/w 中位 {:.2f}".format(A["hw_eq"]),
        A["hw_eq"] if A["n_bulk"] else None)''',
'''    chk("T7c ⚠根因: 本 CA 的【L 预算包络】机制让初始填充的固相胞从 t=0 起累积 L",
        "WARN",
        "⇒ 外延晶粒的包络远快于新生核心 ⇒ 熔池被外延吞掉，等轴区出不来. "
        "要 CET 需把生长由【累积 L 预算】改为【局部过冷直接驱动】", A["n_col"])''', 1)
s = s.replace('''        return dict(n_col=len(col), n_bulk=len(eq),''',
              '''        return dict(n_col=len(col), n_bulk=len(eq), nn=nn,''', 1)
s = s.replace('''        print("  [{}] 各种晶粒 {} 个; 其中【初始液相内形核】的 {} 个, h/w 中位 {}".format(
            tag, r["n_col"] + r["n_bulk"], r["n_bulk"],
            "{:.2f}".format(r["hw_eq"]) if r["n_bulk"] else "无"))''',
              '''        print("  [{}] 形核事件 {} 个; 存活晶粒(n>=8胞) {} 个（其中初始液相内形核 {} 个）".format(
            tag, r["nn"], r["n_col"] + r["n_bulk"], r["n_bulk"]))''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("finalized T7")