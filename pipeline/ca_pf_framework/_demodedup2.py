import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
old = '    np.savez(os.path.join(OUT, "meltpool_growth_gid.npz"), gid=ca.gid, dx=DX)\n'
assert old in s, "anchor"
s = s.replace(old, "", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("removed the overwriting savez")