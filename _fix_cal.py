import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_bench.py'
s = io.open(P, encoding='utf-8').read()
# 用体积分数测界面速度、单 Δf 标定；迁移率按目标速度定
old_cal = s[s.index('def calib_L():'):s.index('def mk(')]
new_cal = '''def calib_L(df=1e7, L_trial=1e-8, nst=4000, dt=1e-9, Nx=128):
    """1D 平面界面：用【变体体积分数增长】测界面速度（符号明确）
       v = (ΔF)·L_box/t ；标定常数 C1 = v/(L_trial·Δf)（量纲 1，物理上 ≈ 界面半宽）"""
    dx = 2e-9
    Lbox = Nx * dx
    C = C_iso(100e9, 0.3, 2)
    eps0 = np.zeros((1, 2, 2))
    a = np.sqrt(KAP / (2 * WBAR))
    x = (np.arange(Nx) + 0.5) * dx
    pf = MartensitePF(Nx, Lbox, C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM, dG=df)
    pf.W = WBAR; pf.Lmob = L_trial
    pf.phi[0] = 0.5 * (1 - np.tanh((x - 0.25 * Lbox) / (2 * a)))
    f0 = pf.phi[0].mean()
    for _ in range(nst):
        pf.step(dt, cap_sum=False)
    v = (pf.phi[0].mean() - f0) * Lbox / (nst * dt)
    return v / (L_trial * df), v


'''
s = s.replace(old_cal, new_cal, 1)
s = s.replace("MINT = 1e-6            # 目标：v = M_int·Δf 的\"sharp-interface 迁移率\" [m^4/(J s)] ⇒ v≈10 m/s",
              "V_TARGET = 100.0       # 目标界面速度 [m/s]（位移型界面很快；远小于热循环时间尺度 ⇒ 建造期"瞬完"）")
s = s.replace("""    C1 = calib_L()
    Lmob = MINT / C1""",
"""    C1, v_raw = calib_L()
    Lmob = V_TARGET / (1e7 * C1)          # 使 v = M_int·Δf = 100 m/s（在 Δf=1e7 处）
    MINT = V_TARGET / 1e7""")
s = s.replace("      1D 界面迁移率标定: C1 = v/(L·Δf) = %.3e 1/m ⇒ 取 M_int=%.1e 得 L = %.3e' % (\n        C1, MINT, Lmob))",
              "      1D 标定(体积分数法): C1 = %.3e, v(L=1e-8)= %.3e m/s ⇒ 取 v_target=%.0f m/s 得 L = %.3e' % (\n        C1, v_raw, V_TARGET, Lmob))")
s = s.replace("    ns = 3000\n    dt = 1e-11", "    ns = 4000\n    dt = 2e-12")
io.open(P, 'w', encoding='utf-8').write(s)
print('标定与时间尺度已按"体积分数法"改好')