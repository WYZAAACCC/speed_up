import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("GI.append(int(a[uu[t], vv[t]])); ISGB.append(False)", "GI.append(int(a[uu[t], vv[t]])); KIND.append(0)", 1)
assert "ISGB" not in s, "still has ISGB"
io.open(P, "w", encoding="utf-8").write(s)
print("fixed")