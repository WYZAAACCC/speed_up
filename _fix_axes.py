import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_pf.py'
s = io.open(P, encoding='utf-8').read()
reps = [
 ("        self.axk = tuple(range(1, 1 + dim))          # φ 的张量轴\n        self.axr = tuple(range(1 + dim))             # 空间轴\n        self.norm = N ** dim",
  "        self.axp = tuple(range(1, 1 + dim))          # φ(nv,N,..) 的空间轴\n        self.axc = (0, 1)                            # 张量 ε⁰(dim,dim,N,..) 的分量轴\n        self.axs = tuple(range(2, 2 + dim))          # 张量 ε⁰ 的空间轴\n        self.norm = N ** dim"),
 ("        ek = np.fft.fftn(e0r, axes=self.axk) / self.norm            # (dim,dim,N,..)\n        ek = np.transpose(ek, self.axr + self.axk).reshape(-1, self.dim, self.dim)",
  "        ek = np.fft.fftn(e0r, axes=self.axs) / self.norm            # (dim,dim,N,..)\n        ek = np.transpose(ek, self.axs + self.axc).reshape(-1, self.dim, self.dim)"),
 ("        sk = sk.reshape((self.N,) * self.dim + (self.dim, self.dim))\n        sk = np.transpose(sk, self.axk + self.axr)                  # (dim,dim,N,..)\n        sig = np.real(np.fft.ifftn(sk, axes=self.axk))",
  "        sk = sk.reshape((self.N,) * self.dim + (self.dim, self.dim))\n        sk = np.transpose(sk, self.axs + self.axc)                  # (dim,dim,N,..)\n        sig = np.real(np.fft.ifftn(sk, axes=self.axs))"),
 ("        lap = np.real(np.fft.ifftn(-self.k2 * np.fft.fftn(self.phi, axes=self.axk), axes=self.axk))",
  "        lap = np.real(np.fft.ifftn(-self.k2 * np.fft.fftn(self.phi, axes=self.axp), axes=self.axp))"),
]
for o, n in reps:
    if o not in s:
        print('!! 未找到:', o[:50]); raise SystemExit(1)
    s = s.replace(o, n, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('轴已统一')