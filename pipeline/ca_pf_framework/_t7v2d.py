import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("    nst = 200\n    bulk = (6.0, 2.0, 2.0e14)", "    nst = 400\n    bulk = (6.0, 2.0, 2.0e14)", 1)
s = s.replace("ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)", "ca.T_meltpool(2500.0, 60e-6, 1.0e-3, 353.0)")
s = s.replace("T = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)", "T = ca.T_meltpool(2500.0, 60e-6, 1.0e-3, 353.0)")
s = s.replace("        if n < 30:\n            continue", "        if n < 8:\n            continue", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T7 v2d")