import io
p = "windowB_surface.py"
s = io.open(p, encoding="utf-8").read()
n = 0

a = "                 aniso_elastic=False, C_hex_tab=None, C_cub=None):"
b = "                 aniso_elastic=False, C_hex_tab=None, C_cub=None, sigma_ext=None):"
assert a in s; s = s.replace(a, b); n += 1

a = "        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)"
b = """        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)
        # ---- T2.1a (2026-09-25): external stress sigma_ext -------------------
        # Driving-force convention, identical to `PF3D.forces()` / `dfdphi()`:
        #     df_v = -eps0_v : sigma_int  +  sigma_ext : eps0_v
        # (the second term is the work done by the applied stress as the
        # transformation strain develops).  sigma_ext = None reproduces the old
        # behaviour bit-for-bit (sext_e0 is then identically zero).
        self.sigma_ext = (np.zeros((3, 3)) if sigma_ext is None
                          else np.asarray(sigma_ext, float))
        self.sext_e0 = (np.zeros(self.nv) if eps0 is None else
                        np.array([np.einsum('ij,ij->', self.sigma_ext,
                                            np.asarray(e, float)) for e in eps0]))"""
assert a in s; s = s.replace(a, b); n += 1

a = """            self.pf = PF3D(N, L, C, eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                           workers=workers, k0_mode=k0_mode)"""
b = """            self.pf = PF3D(N, L, C, eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                           workers=workers, k0_mode=k0_mode,
                           sigma_ext=self.sigma_ext)"""
assert a in s; s = s.replace(a, b); n += 1

a = "                out[v + 1] = -np.einsum('p,p...->...', self.e0v_eng[v], sig6)"
b = ("                out[v + 1] = (-np.einsum('p,p...->...', self.e0v_eng[v], sig6)\n"
     "                              + self.sext_e0[v])")
assert a in s; s = s.replace(a, b); n += 1

a = "            out[v + 1] = -np.einsum('p,p...->...', self.e0v_eng[v], sig)"
b = ("            out[v + 1] = (-np.einsum('p,p...->...', self.e0v_eng[v], sig)\n"
     "                          + self.sext_e0[v])")
assert a in s; s = s.replace(a, b); n += 1

io.open(p, "w", encoding="utf-8").write(s)
print("patched windowB_surface.py: %d sites" % n)