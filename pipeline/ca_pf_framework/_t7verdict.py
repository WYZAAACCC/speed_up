import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace('''    chk("T7a 体形核晶粒是【等轴】、基底晶粒是【柱状】（形貌对照）",
        "PASS" if (A["eq"] and A["hw_eq"] <= 2.0 and A["hw_col"] >= 2.0) else "WARN",
        "thermal 驱动: 等轴 h/w 中位 {:.2f} vs 柱状 {:.2f}".format(A["hw_eq"], A["hw_col"]),
        A["hw_eq"] if A["eq"] else None)''',
'''    chk("T7a ⚠发现: 本 CA 的体形核晶粒【不是等轴】而是窄柱（生长不看溶质场）",
        "WARN",
        "体形核 h/w 中位 {:.2f} vs 基底柱状 {:.2f} ⇒ 只有形核驱动量、没有把 c_liq 接进【生长】"
        " ⇒ CET 的等轴形貌在本模型里产生不出来".format(A["hw_eq"], A["hw_col"]),
        A["hw_eq"] if A["eq"] else None)''', 1)
s = s.replace('chk("T7b 成分过冷驱动能形核到更高处（热前沿【之前】也能形核）",\n        "PASS" if B["zmax"] > A["zmax"] else "WARN",',
              'chk("T7b 成分过冷驱动 vs 热过冷：形核位置的差异（本轮差异很小，需再调参）",\n        "WARN" if B["zmax"] <= A["zmax"] else "PASS",', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T7 verdicts as findings")