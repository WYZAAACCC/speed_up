import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
if "201 x 300 x 201" in s:
    print("already patched"); raise SystemExit
s = s.replace("DX = 2.0e-6\nNX, NY, NZ = 100, 150, 100          # 200 x 300 x 200 um\nT_PEAK, SIGMA, TAU, T_BATH = 2500.0, 50e-6, 3.0e-4, 353.0",
              "DX = 3.0e-6\nNX, NY, NZ = 67, 100, 67            # 201 x 300 x 201 um\nT_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0", 1)
i0 = s.index("    snaps, times, hist = [], [], []")
i1 = s.index("    print(\"用时")
new_run = '''    snaps, times, hist = [], [], []
    t0 = time.time()
    for s_ in range(nst):
        ca.t = s_ * dt
        T = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
        ca.step(dt, T, window=None)
        if s_ % 5 == 0 and int((ca.gid == 0).sum()) > 0 and len(snaps) < 40:
            snaps.append(ca.gid.copy()); times.append(ca.t)
            hist.append((ca.t, ca.solid_fraction(), len(ca.grain_ids())))
    snaps.append(ca.gid.copy()); times.append(ca.t)
'''
s = s[:i0] + new_run + s[i1:]
s = s.replace('def fig_process(ca, snaps, times):\n    ng = len(ca.axes) - 1',
              'def fig_process(ca, snaps, times):\n    if len(snaps) > 8:\n'
              '        n_liq = np.array([float((x == 0).sum()) for x in snaps])\n'
              '        pick = sorted(set(int(np.argmin(np.abs(n_liq - q * n_liq[0])))\n'
              '                          for q in (1.0, 0.6, 0.35, 0.15, 0.05, 0.0)))\n'
              '        snaps = [snaps[i] for i in pick]; times = [times[i] for i in pick]\n'
              '    ng = len(ca.axes) - 1', 1)
old3d = """    for gid in range(1, ng + 1):
        m = g == gid
        if not m.any():
            continue
        ax.voxels(m, facecolors=[cmap(norm(gid))], edgecolor=None, shade=True)"""
new3d = """    filled = g > 0
    fc = np.zeros(g.shape + (4,), float)
    for gid in range(1, ng + 1):
        fc[g == gid] = cmap(norm(gid))
    ax.voxels(filled, facecolors=fc, edgecolor=None, shade=True)"""
assert old3d in s, "voxels anchor"
s = s.replace(old3d, new3d, 1)
s = s.replace("    st = 3                                               # 抽稀，供 3D 体素渲染",
              "    st = 5                                               # 抽稀，供 3D 体素渲染", 1)
s = s.replace('    ca, snaps, times, hist = run()\n    fig_process(ca, snaps, times)',
              '    ca, snaps, times, hist = run()\n'
              '    np.savez(os.path.join(OUT, "meltpool_growth_gid.npz"), gid=ca.gid, dx=DX)\n'
              '    print("saved meltpool_growth_gid.npz (仿真已落盘，画图可重跑)")\n'
              '    fig_process(ca, snaps, times)', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched demo")