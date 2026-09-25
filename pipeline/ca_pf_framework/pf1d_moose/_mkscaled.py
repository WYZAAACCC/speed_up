import io
p = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_quad.i"
s = io.open(p, encoding="utf-8").read()
a1 = 'expression = "k_c/2*(c-c0)^2 + A_part*c^2*(3*phi^2-2*phi^3)"'
b1 = 'expression = "1.0e9*(k_c/2*(c-c0)^2 + A_part*c^2*(3*phi^2-2*phi^3))"'
a2 = 'expression = "(DS+(DL-DS)*(1-phi))/(k_c+2*A_part*(3*phi^2-2*phi^3))"'
b2 = 'expression = "(DS+(DL-DS)*(1-phi))/(1.0e9*(k_c+2*A_part*(3*phi^2-2*phi^3)))"'
assert a1 in s and a2 in s, "anchors"
s = s.replace(a1, b1, 1).replace(a2, b2, 1)
s = s.replace("end_time = 1.0000e-04", "end_time = 2.0e-06", 1)
s = s.replace("nl_abs_tol = 1e-13", "nl_abs_tol = 1e-9", 1)
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/quadt/s.i", "w",
        encoding="utf-8").write(s)
print("ok")