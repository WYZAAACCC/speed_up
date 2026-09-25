import io
p = "pf1d_moose/_chk_profile3.py"
s = io.open(p, encoding="utf-8").read()
a = """CASES.append(("PROD W2 A0", "prod1d_A0_W2_kc1e-14", PROD))
CASES.append(("PROD W2 A2", "prod1d_A2_W2_kc1e-14", PROD))
CASES.append(("PROD W2 A4", "prod1d_A4_W2_kc1e-14", PROD))
# T1.2 (W_F three-way) -- dirs appear once the runs finish
for a, w in [("2", "2e-06"), ("2", "4e-06"), ("2", "1.05e-07"),
             ("4", "1.05e-07"), ("8", "1.05e-07")]:
    CASES.append(("PROD WF=%s A%s" % (w, a), "prod1d_A%s_W%s_kc1e-14" % (a, w), PROD))"""
b = """# --- production instrument, FIXED dt = 4.1667e-8 s (2026-09-25 clean re-run) ---
for tag, d in [("PROD L150 A0 W2", "prod1d_A0_W2_kc1e-14_L150"),
               ("PROD L150 A2 W2", "prod1d_A2_W2_kc1e-14_L150"),
               ("PROD L150 A4 W2", "prod1d_A4_W2_kc1e-14_L150"),
               ("PROD L150 A2 W4", "prod1d_A2_W4_kc1e-14_L150"),
               ("PROD L150 A2 Wc", "prod1d_A2_W0.105_kc1e-14_L150"),
               ("PROD L150 A4 Wc", "prod1d_A4_W0.105_kc1e-14_L150"),
               ("PROD L150 A8 Wc", "prod1d_A8_W0.105_kc1e-14_L150"),
               ("PROD L300 A0 W2", "prod1d_A0_W2_kc1e-14_L300"),
               ("PROD L300 A2 W2", "prod1d_A2_W2_kc1e-14_L300"),
               ("PROD L300 A4 W2", "prod1d_A4_W2_kc1e-14_L300"),
               ("PROD A2 W2 dt/4", "prod1d_A2_W2_kc1e-14_L150dt4")]:
    CASES.append((tag, d, PROD))"""
assert a in s, "anchor not found"
s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched ok")