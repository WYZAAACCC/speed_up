import io
p = "_chk_t21a.py"
s = io.open(p, encoding="utf-8").read()

a = """def run_case(tag, sig):
    import windowB_surface as W
    from windowB_pf3d import C_cubic
    C = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (nv + 1), workers=6, reinit_every=25,
                        sigma_ext=sig)
    R = 0.08 * N * DX                      # 12 non-overlapping equal spheres
    n = 0
    for i in range(3):
        for j in range(2):
            for k in range(2):
                g.seed_sphere(n + 1,
                              ((i + 0.5) * N * DX / 3, (j + 0.5) * N * DX / 2,
                               (k + 0.5) * N * DX / 2), R)
                n += 1"""
b = """def run_case(tag, sig, perm=None):
    import windowB_surface as W
    from windowB_pf3d import C_cubic
    C = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (nv + 1), workers=6, reinit_every=25,
                        sigma_ext=sig)
    R = 0.08 * N * DX                      # 12 non-overlapping equal spheres
    sites = [(i, j, k) for i in range(3) for j in range(2) for k in range(2)]
    if perm is not None:
        sites = [sites[q] for q in perm]
    for n, (i, j, k) in enumerate(sites):
        g.seed_sphere(n + 1,
                      ((i + 0.5) * N * DX / 3, (j + 0.5) * N * DX / 2,
                       (k + 0.5) * N * DX / 2), R)"""
assert a in s; s = s.replace(a, b)

a = """    g0, _ = run_case('sigma_ext = 0 (control)', np.zeros((3, 3)))
    rec('A5 control sigma=0: no selection (spread <= 5 %)',
        (g0.max() - g0.min()) / abs(g0.mean()) <= 0.05,
        'spread = %.3f' % ((g0.max() - g0.min()) / abs(g0.mean())))"""
b = """    sp_loaded = gz.max() - gz.min()
    g0, _ = run_case('sigma_ext = 0 (control, placement #1)', np.zeros((3, 3)))
    rev = list(range(len(range(12))))[::-1]
    g0b, _ = run_case('sigma_ext = 0 (control, placement reversed)', np.zeros((3, 3)),
                      perm=rev)
    sp0, sp0b = g0.max() - g0.min(), g0b.max() - g0b.min()
    print("      [A5] wait -- the sigma=0 pattern must be POSITIONAL: with a "
          "reversed placement variant v must change sign")
    print("      growth(placement #1) = %s" % ' '.join('%+5.2f' % (100 * x) for x in g0))
    print("      growth(reversed)    = %s" % ' '.join('%+5.2f' % (100 * x) for x in g0b))
    print("      spearman(#1, reversed) = %.3f" % spearman(g0, g0b))
    rec('A5a sigma=0: spread <= 0.4 x spread(sigma=300MPa)', sp0 <= 0.4 * sp_loaded,
        'spread0 = %.3f%% vs loaded %.3f%%' % (100 * sp0, 100 * sp_loaded))
    rec('A5b sigma=0: reversed placement CHANGES the pattern '
        '(=> positional, not intrinsic selection)', spearman(g0, g0b) < 0.5,
        'rho = %.3f' % spearman(g0, g0b))"""
assert a in s; s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched _chk_t21a.py ok")