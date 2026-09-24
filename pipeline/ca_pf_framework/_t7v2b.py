import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("    bulk = (12.0, 4.0, 4.0e14)", "    bulk = (6.0, 2.0, 2.0e14)", 1)
s = s.replace('    chk("T7a 打开溶质->生长反馈后，体形核晶粒变【等轴】",\n        "PASS" if (B["n_bulk"] and B["hw_eq"] <= 2.0) else "WARN",\n        "feedback ON: 体形核 h/w 中位 {:.2f}（判据 <=2）; 基底柱状 {:.2f}".format(\n            B["hw_eq"], B["hw_col"]), B["hw_eq"] if B["n_bulk"] else None)',
'''    chk("T7a 溶质->生长反馈打开后，体形核晶粒形貌",
        "PASS" if (B["n_bulk"] and B["hw_eq"] <= 2.0) else "WARN",
        "feedback ON: 体形核 {} 个, h/w 中位 {:.2f}（判据 <=2）".format(
            B["n_bulk"], B["hw_eq"]), B["hw_eq"] if B["n_bulk"] else None)''', 1)
# 增加分布打印
s = s.replace('    for tag, r in (("feedback OFF", A), ("feedback ON ", B)):\n        print("  [{}] 基底柱状 {} 个 (h/w 中位 {:.2f}); 体形核 {} 个 (h/w 中位 {})".format(\n            tag, r["n_col"], r["hw_col"], r["n_bulk"],\n            "{:.2f}".format(r["hw_eq"]) if r["n_bulk"] else "无"))',
'''    for tag, r in (("feedback OFF", A), ("feedback ON ", B)):
        print("  [{}] 各种晶粒 {} 个; 其中【初始液相内形核】的 {} 个, h/w 中位 {}".format(
            tag, r["n_col"] + r["n_bulk"], r["n_bulk"],
            "{:.2f}".format(r["hw_eq"]) if r["n_bulk"] else "无"))
        if r["n_bulk"]:
            print("       体形核晶粒 h/w 明细: " +
                  " ".join("{:.2f}".format(x) for x in sorted(x[1] for x in r["rows"] if x[0])))''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("retuned T7 v2b")