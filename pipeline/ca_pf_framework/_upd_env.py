import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_audit_env.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace('for mode in ("analytic", "decentered"):', 'for mode in ("envelope", "analytic", "decentered"):')
io.open(P, "w", encoding="utf-8").write(s)
print("ok")