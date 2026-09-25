import numpy as np
import alloy_pf_std as S
for T in (1911.1,):
    print("T=%.1f  A=%.1f  RT/Vm=%.4e  A/RT=%.4f" % (T, S.A_of(T), S.R*T/S.VM, S.A_of(T)/(S.R*T)))
    for m, cs, cl in S._ct_roots(T):
        print("   root m=%.4e  c_s=%.6f  c_l=%.6f  k=%.6f" % (m, cs, cl, cs/cl))
    print("   -> physical:", S.common_tangent(T))