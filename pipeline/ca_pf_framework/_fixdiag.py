import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_t6diag2.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("quats = [ca3d.rand_quat(rng) for _ in range(9)]",
              "quats = [ca3d.rand_quat(rng) for _ in range(9)]\nSS = [support(ca3d.quat_to_axes(q), n) for q in quats]")
s = s.replace("""        L_end / min(support(ca.axes[g], n) for g in range(1, 10)) - L_end / max(support(ca.axes[g], n) for g in range(1, 10))))""",
              """        L_end / min(SS) - L_end / max(SS)))""")
io.open(P, "w", encoding="utf-8").write(s)
print("fixed")