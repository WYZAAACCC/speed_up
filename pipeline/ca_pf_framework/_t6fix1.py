import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()

# 1) 种子布置：改成一维/二维单胞栅格（不再铺满 y）
old_place = s[s.index("def place_seeds_on_perp_plane"):s.index("def front_advance")]
new_place = '''def place_seeds_on_perp_plane(ca, n, n_t, n_y, spacing, quats=None):
    """在过域中心的 ⟂n̂ 平面上布【单胞】种子：沿 t̂ 排 n_t 个、沿 ŷ 排 n_y 个。
    两个方向都 ⟂ n̂ => 所有种子到等温面的投影相同（位置效应被消掉）。"""
    t = perp_dir(n)
    cx = (ca.nx - 1) / 2.0
    cz = (ca.nz - 1) / 2.0
    cy = (ca.ny - 1) / 2.0
    out = []
    m = 0
    for a in range(n_t):
        off = (a - (n_t - 1) / 2.0) * spacing
        i = int(round(cx + off * t[0]))
        k = int(round(cz + off * t[2]))
        if not (0 <= i < ca.nx and 0 <= k < ca.nz):
            continue
        for b in range(n_y):
            j = int(round(cy + (b - (n_y - 1) / 2.0) * spacing))
            j %= ca.ny
            q = None if quats is None else quats[m % len(quats)]
            out.append(ca.add_grain(i, j, k, q))
            m += 1
    return out


'''
s = s.replace(old_place, new_place, 1)

# 2) 领先前沿：以【固相】的最大投影为基准
old_meas = '''    s0 = float(sp.mean())                      # 域中心的 n̂ 投影
    s_max = float(sp.max())
    lead = sp >= (s_max - 1.5 * ca.dx)         # 领先前沿（最前 ~1.5 胞）'''
new_meas = '''    s0 = float(sp.mean())                      # 域中心的 n̂ 投影
    solid = ca.gid > 0
    s_max = float(sp[solid].max()) if solid.any() else float(sp.max())
    lead = solid & (sp >= (s_max - 1.5 * ca.dx))   # 领先前沿（固相里最前 ~1.5 胞）'''
assert old_meas in s
s = s.replace(old_meas, new_meas, 1)

# 3) 情形 A/B 的调用改为二维栅格
s = s.replace('        gids = place_seeds_on_perp_plane(ca, n, nseed, spacing, jall=True, quats=quats)',
              '        gids = place_seeds_on_perp_plane(ca, n, nseed, 3, spacing, quats=quats)', 1)
s = s.replace('    gids = place_seeds_on_perp_plane(ca, n, 7, 9, jall=True, quats=quats)',
              '    gids = place_seeds_on_perp_plane(ca, n, 4, 3, 10, quats=quats)', 1)
s = s.replace('        ca = CA3D(64, 4, 64, dx, irf=irf, seed=2024 + nseed,',
              '        ca = CA3D(64, 10, 64, dx, irf=irf, seed=2024 + nseed,', 1)
s = s.replace('    ca = CA3D(64, 4, 64, dx, irf=irf, seed=77, periodic=(False, True, False))',
              '    ca = CA3D(64, 10, 64, dx, irf=irf, seed=77, periodic=(False, True, False))', 1)
s = s.replace('''    for nseed, spacing, tag in ((5, 10, "5 种子"), (9, 8, "9 种子")):''',
              '''    for nseed, spacing, tag in ((3, 10, "3x3 种子"), (5, 10, "5x3 种子")):''', 1)
s = s.replace('    nst = 80                                    # V t = 20 dx',
              '    nst = 120                                   # V t = 30 dx', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T6")