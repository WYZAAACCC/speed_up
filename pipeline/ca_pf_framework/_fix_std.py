import io
p = "alloy_pf_std.py"
s = io.open(p, encoding="utf-8").read()

a = s[s.index("def common_tangent(T):"):s.index("def sech2(x):")]
b = '''def common_tangent(T, guess=(0.03, 0.05)):
    """f_s = f_l + A*c/Vm: common tangent -> (c_s, c_l, k_e).

    Solve in the (c_s, c_l) form with scipy.optimize.root from a PHYSICAL guess.
    (A hand-rolled Newton drifted to the degenerate near-zero root; that root
    exists because both curves are flat-ish as c->0.)
    """
    from scipy.optimize import root
    rt, A = R * T / VM, A_of(T)

    def F(v):
        cs, cl = v
        f1 = _flp(cs, rt) + A / VM - _flp(cl, rt)            # equal slopes
        b_l = _fl(cl, rt) - _flp(cl, rt) * cl
        b_s = _fl(cs, rt) + A * cs / VM - (_flp(cs, rt) + A / VM) * cs
        return np.array([f1, b_s - b_l])

    sol = root(F, np.array(guess), tol=1e-14)
    cs, cl = float(sol.x[0]), float(sol.x[1])
    if not (0 < cs < cl < 1) or np.max(np.abs(F(sol.x))) > 1e-6:
        raise RuntimeError("common tangent failed: %s x=%s" % (sol.message, sol.x))
    return cs, cl, cs / cl


'''
s = s.replace(a, b)

a = """        if dt is None:
            dt = min(0.05 * dx ** 2 / DL, 0.05 * self.ld ** 2 / DL)
        self.dt = dt"""
b = """        if dt is None:
            # ACCURACY-limited, not the explicit dx^2/D stability limit: the
            # scheme is implicit.  The physical scale is the relaxation time of
            # the solute boundary layer, l_D^2/D_L.
            dt = 0.05 * self.ld ** 2 / DL
        self.dt = dt"""
assert a in s; s = s.replace(a, b)

a = """            r = dt / dx ** 2
            main = np.ones(N)
            up = np.zeros(N - 1)
            lo = np.zeros(N - 1)
            main[1:-1] = 1.0 + r * (Df[:-1] + Df[1:])
            main[0] = 1.0 + r * Df[0]
            up[:-1] = -r * Df[1:-1]
            up[-1] = 0.0
            lo[1:] = -r * Df[1:-1]
            lo[0] = 0.0
            main[-1], lo[-1] = 1.0, 0.0"""
b = """            r = dt / dx ** 2
            main = np.ones(N)
            main[1:] += r * (Df[:-1] + Df[1:])      # nodes 1..N-2 interior (last overwritten)
            main[0] = 1.0 + r * Df[0]
            up = -r * Df.copy()                     # upper[k] couples (k, k+1), k=0..N-2
            lo = -r * Df.copy()                     # lower[k] couples (k+1, k)
            main[-1], lo[-1] = 1.0, 0.0"""
assert a in s; s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched alloy_pf_std.py")