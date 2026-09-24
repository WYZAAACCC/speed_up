import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_pf.py'
s = io.open(P, encoding='utf-8').read()
old = "        self.dx = L / N\n        self.k = [2 * np.pi * np.fft.fftfreq(N, d=self.dx) for _ in range(dim)]"
new = "        self.dx = L / N\n        self.phi = np.zeros((self.nv,) + (N,) * dim)\n        self.k = [2 * np.pi * np.fft.fftfreq(N, d=self.dx) for _ in range(dim)]"
if old not in s: print('!! 锚点'); raise SystemExit(1)
io.open(P, 'w', encoding='utf-8').write(s.replace(old, new, 1))
print('已补 self.phi 初始化')