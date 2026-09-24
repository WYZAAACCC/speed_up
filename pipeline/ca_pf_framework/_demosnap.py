import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
if "snap_pick" in s:
    print("already"); raise SystemExit
old = '    np.savez(os.path.join(OUT, "meltpool_growth_gid.npz"), gid=ca.gid, dx=DX)'
new = ('    n_liq = np.array([float((x == 0).sum()) for x in snaps])\n'
       '    snap_pick = sorted(set(int(np.argmin(np.abs(n_liq - q * n_liq[0])))\n'
       '                           for q in (1.0, 0.75, 0.5, 0.3, 0.12, 0.0)))\n'
       '    np.savez(os.path.join(OUT, "meltpool_growth_gid.npz"), gid=ca.gid, dx=DX,\n'
       '             snaps=np.array([snaps[i] for i in snap_pick]),\n'
       '             snap_t=np.array([times[i] for i in snap_pick]))\n'
       '    print("过程快照 {} 张已存盘 (t = {})".format(\n'
       '        len(snap_pick), " ".join("%.2e" % times[i] for i in snap_pick)))')
assert old in s, "npz anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched demo to save snapshots")