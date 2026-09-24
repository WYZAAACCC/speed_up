import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("        exs.append(float(ca.c.max()))", "        exs.append(float(ca.c_liq.max()))", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T9 -> c_liq.max()")