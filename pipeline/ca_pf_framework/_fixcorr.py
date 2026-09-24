import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_diag_corr.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("sorted(rows.tolist())", "sorted(rows)")
io.open(P, "w", encoding="utf-8").write(s)
print("fixed")