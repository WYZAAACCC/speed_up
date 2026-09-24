import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
old = "                GI.append(int(a[uu[t], vv[t]])); KIND.append(0)"
new = ("                nv = [0.0, 0.0, 0.0]\n"
       "                nv[axis] = -1.0 if plane_at == 0 else 1.0\n"
       "                GI.append(int(a[uu[t], vv[t]])); KIND.append(0); NRM.append(nv)")
assert old in s, "anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("fixed NRM in shell block")