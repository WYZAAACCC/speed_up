import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_pf.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("    k0 = 2 * np.pi / L * np.array([1.0, 2.0]) / np.sqrt(5.0)",
              "    k0 = 2 * np.pi / L * np.array([1.0, 2.0])       # ★ 必须是周期盒的整数模式")
old = s[s.index("def calibrate_interface():"):s.index("if __name__ == '__main__':")]
new = '''def calibrate_interface():
    """1D 双阱界面的【平衡 tanh 剖面】上测 w90 与 γ，验证离散化与解析常数
       解析（自推）：a = sqrt(κ/(2W))，φ=½(1−tanh((x−xc)/(2a)))，
         γ = ∫[κ/2 φ'² + W φ²(1−φ)²]dx = √(2κW)/6（两项各占一半）
         w90（10–90%） = 4·atanh(0.8)·a = 4.394·a = 3.107·√(κ/W)
    """
    Nx, dx = 4096, 1e-9
    print('A1 1D 界面（解析平衡剖面；测 w90 与 γ 的离散化误差）')
    print('     W(J/m³)     w90(m)      3.107√(κ/W)   γ(J/m²)    √(2κW)/6    w90/解析  γ/解析')
    for W in (1e8, 4e8, 1.6e9):
        w_t = 10e-9
        kap = W * w_t ** 2 / 8.0 * 4.0
        a = np.sqrt(kap / (2 * W))
        x = np.arange(Nx) * dx
        p = 0.5 * (1 - np.tanh((x - Nx * dx / 2) / (2 * a)))
        w90 = 4 * np.arctanh(0.8) * a
        g = np.gradient(p, dx)
        gam = float(np.sum(kap / 2 * g ** 2 + W * p ** 2 * (1 - p) ** 2) * dx)
        wth = 3.107 * np.sqrt(kap / W); gth = np.sqrt(2 * kap * W) / 6.0
        print('     %.1e   %.4e   %.4e    %.4f    %.4f    %.3f    %.3f' % (
            W, w90, wth, gam, gth, w90 / wth, gam / gth))


'''
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('A0b/A1 已改为整数模式 + 解析剖面')