import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_diagT7.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("ca.nucleate_bulk(T, 12.0, 4.0, 4.0e14, dt, c_l=ca.c_liq, m_L=M_L)",
              "ca.nucleate_bulk(T, 6.0, 2.0, 2.0e14, dt)")
s = s.replace('    if s_ % 50 == 0:', '    if s_ % 5 == 0:')
io.open(P, "w", encoding="utf-8").write(s)
print("diag patched")