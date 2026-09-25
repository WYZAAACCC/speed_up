import math
R, Vm, dgB, dHf, Tm = 8.314, 1.1345e-5, 7334.0, 14150.0, 1941.0
for T, tag in ((1941.0, "Tm"), (1911.1, "interface")):
    dg = dgB + dHf * (1 - T / Tm)
    r = math.exp(-dg / (R * T))
    # equilibrium pair with c_s = 0.036
    cl = 0.036 / (1 - 0.036) / r
    cl = cl / (1 + cl)
    print("%-10s T=%.1f  dg=%.2f  dg/RT=%.6f  ratio=%.6f  c_l(c_s=0.036)=%.6f  k_eff=c_s/c_l=%.5f"
          % (tag, T, dg, dg / (R * T), r, cl, 0.036 / cl))
print()
print("l_D = D_L/V =", 9.5e-9 / 0.1 * 1e9, "nm")
for W in (2.0e-7, 6.0e-8, 2.0e-8):
    print("W = %.0f nm -> V*W/D_L = %.3f" % (W * 1e9, 0.1 * W / 9.5e-9))