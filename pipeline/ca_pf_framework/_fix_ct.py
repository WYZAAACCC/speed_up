import io
p = "alloy_pf_std.py"
s = io.open(p, encoding="utf-8").read()
i0 = s.index("def common_tangent(T, guess=(0.03, 0.05)):")
i1 = s.index("def sech2(x):")
b = '''def _ct_roots(T):
    """All sign changes of the tangent-intercept condition, parametrised by the
    common slope m.  c_l = sigmoid(m/rt), c_s = sigmoid((m - A/Vm)/rt)."""
    from scipy.optimize import brentq
    rt, A = R * T / VM, A_of(T)

    def c_of(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x / rt, -700, 700)))

    def g(m):
        cl, cs = c_of(m), c_of(m - A / VM)
        return (_fl(cs, rt) + A * cs / VM - m * cs) - (_fl(cl, rt) - m * cl)

    # scan m over c in [1e-9, 1-1e-9]; the degenerate c->0 root sits at the
    # very cold end and is rejected by the physical-range filter below.
    ms = np.linspace(rt * np.log(1e-9), rt * np.log(1 - 1e-9), 20001)
    gg = np.array([g(x) for x in ms])
    out = []
    for k in np.where(np.sign(gg[:-1]) * np.sign(gg[1:]) < 0)[0]:
        r = brentq(g, ms[k], ms[k + 1], xtol=1e-3, rtol=1e-15)
        out.append((r, c_of(r - A / VM), c_of(r)))
    return out


def common_tangent(T, cmin=1e-4):
    """Common tangent of f_s = f_l + A*c/Vm  ->  (c_s, c_l, k_e)."""
    roots = _ct_roots(T)
    phys = [r for r in roots if r[2] > cmin]
    if not phys:
        raise RuntimeError("no physical common tangent; roots=%s" % roots)
    m, cs, cl = max(phys, key=lambda r: r[2])
    return cs, cl, cs / cl


'''
s = s[:i0] + b + s[i1:]
io.open(p, "w", encoding="utf-8").write(s)
print("patched common_tangent")