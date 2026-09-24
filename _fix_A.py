import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_pf.py'
s = io.open(P, encoding='utf-8').read()
# A0b: 含 DC 分量
old = """    En = pf.E_el()
    Ea = 2 * 0.5 * L ** dim * (amp / 2) ** 2 * np.einsum('ij,ijkl,kl->', e0, Lambda(C, k0), e0)"""
new = """    En = pf.E_el()
    E_DC = 0.5 * L ** dim * (0.5 ** 2) * np.einsum('ij,ijkl,kl->', e0, C, e0)
    E_k0 = 2 * 0.5 * L ** dim * (amp / 2) ** 2 * np.einsum('ij,ijkl,kl->', e0, Lambda(C, k0), e0)
    Ea = E_DC + E_k0"""
if old not in s: print('!! A0b'); raise SystemExit(1)
s = s.replace(old, new, 1)
# A1: 解析常数自推 + 界面分辨开 + 合适 dt
old2 = """    Nx, dx, kap = 1024, 1e-9, 2e-11
    print('A1 1D 界面标定（κ = %.1e 固定，扫描 W）' % kap)
    print('     W(J/m³)      w90(m)      2√(2κ/W)      γ(J/m²)     √(2κW)/3      w90/解析   γ/解析')
    for W in (2e8, 4.5e8, 1e9):
        p = 0.5 * (1 - np.tanh((np.arange(Nx) - Nx / 2) * dx / (2 * np.sqrt(kap / W))))
        for _ in range(3000):                          # 简单显式松弛到平衡
            lap = (np.roll(p, 1) - 2 * p + np.roll(p, -1)) / dx ** 2
            p = p - 1e-16 * (2 * W * p * (1 - p) * (1 - 2 * p) - kap * lap)
            np.clip(p, 0, 1, out=p)"""
new2 = """    Nx, dx = 2048, 1e-9
    print('A1 1D 界面标定（dx=1nm；κ 与 W 由目标宽度 w=10nm 定：κ = W w²/8）')
    print('     W(J/m³)      w90(m)      3.107√(κ/W)   γ(J/m²)     √(2κW)/6     w90/解析   γ/解析')
    for W in (1e8, 4e8, 1.6e9):
        w_t = 10e-9
        kap = W * w_t ** 2 / 8.0 * 4.0            # κ 取 4 倍以给更宽的界面（便于分辨）
        a = np.sqrt(kap / (2 * W))
        p = 0.5 * (1 - np.tanh((np.arange(Nx) - Nx / 2) * dx / (2 * a)))
        dt = 1e-9
        for _ in range(200000):                    # 显式松弛到平衡
            lap = (np.roll(p, 1) - 2 * p + np.roll(p, -1)) / dx ** 2
            p = p - dt * (2 * W * p * (1 - p) * (1 - 2 * p) - kap * lap)
            np.clip(p, 0, 1, out=p)"""
if old2 not in s: print('!! A1'); raise SystemExit(1)
s = s.replace(old2, new2, 1)
old3 = """        wth = 2 * np.sqrt(2 * kap / W); gth = np.sqrt(2 * kap * W) / 3"""
new3 = """        wth = 3.107 * np.sqrt(kap / W); gth = np.sqrt(2 * kap * W) / 6.0"""
if old3 not in s: print('!! A1b'); raise SystemExit(1)
s = s.replace(old3, new3, 1)
old4 = """        print('     2√(2κ/W)      γ(J/m²)     √(2κW)/3      w90/解析   γ/解析')"""
if old4 in s:
    s = s.replace(old4, """        print('     3.107√(κ/W)   γ(J/m²)     √(2κW)/6     w90/解析   γ/解析')""")
io.open(P, 'w', encoding='utf-8').write(s)
print('A0b/A1 已修')