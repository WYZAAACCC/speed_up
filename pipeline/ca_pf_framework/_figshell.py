import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
if "域外边界盒壳" in s:
    print("already"); raise SystemExit
anchor = "    return (np.array(P, float), np.array(GI, int), np.array(ISGB, bool))"
add = '''    # ---- 域外边界盒壳（末态全固相 => 域内没有"固-空"面，必须单独补）----
    for axis in range(3):
        n = g.shape[axis]
        for i, plane_at in ((0, 0), (n - 1, n)):
            sl = [slice(None)] * 3; sl[axis] = i
            a = g[tuple(sl)]
            m = a > 0
            if not m.any():
                continue
            uu, vv = np.where(m)
            for t in range(len(uu)):
                c = _idx(axis, i, uu[t], vv[t])
                plane = list(c); plane[axis] = plane_at
                P.append(_quad(plane, axis, dx))
                GI.append(int(a[uu[t], vv[t]])); ISGB.append(False)
'''
assert anchor in s
s = s.replace(anchor, add + anchor, 1)
s = s.replace("SHELL_ALPHA = 0.06", "SHELL_ALPHA = 0.10", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched: add domain boundary shell")