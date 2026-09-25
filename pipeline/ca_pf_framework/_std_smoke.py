import alloy_pf_std as S
cs, cl, ke = S.common_tangent(1911.1)
print("common tangent: c_s=%.6f c_l=%.6f k_e=%.6f  (target c0/k_e=%.6f)" % (cs, cl, ke, S.C0/ke))
g = S.StdFront(W=1e-8, V=0.1, dx=2.5e-9, L=5.7e-6)
print("N=%d l_D=%.0f nm dt=%.3e s (dt/(l_D^2/D_L)=%.4f) nsteps=%d" % (g.N, g.ld*1e9, g.dt, g.dt/(g.ld**2/S.DL), int(1.4e-5/g.dt)))
for a_t in (0.0, S.A_T_KR):
    g.c = __import__("numpy").full(g.N, S.C0)
    g.run(a_t=a_t, tend=1.4e-5)
    st = g.stats(1.4e-5)
    print("a_t=%.4f : c_int=%.6f (dev %+.2f%%)  k_eff=%.4f (k_e=%.4f)  spike=%+.1f%%  c_min=%.5f" %
          (a_t, st["c_int"], 100*st["dev"], st["k_eff"], st["ke"], 100*st["spike"], st["c_min"]))