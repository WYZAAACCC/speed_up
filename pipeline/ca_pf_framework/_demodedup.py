import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
old = ('    np.savez(os.path.join(OUT, "meltpool_growth_gid.npz"), gid=ca.gid, dx=DX)\n'
       '    print("saved meltpool_growth_gid.npz (仿真已落盘，画图可重跑)")\n')
if old in s:
    s = s.replace(old, "", 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("removed duplicate savez in __main__")
else:
    print("anchor not found (print all savez lines):")
    for i, l in enumerate(s.splitlines()):
        if "savez" in l:
            print(i + 1, l)