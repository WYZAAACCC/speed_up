import numpy as np, alloy_pf_std as S
T = 1911.1
rt, A = S.R*T/S.VM, S.A_of(T)
def c_of(x): return 1.0/(1.0+np.exp(-np.clip(x/rt, -700, 700)))
def g(m):
    cl, cs = c_of(m), c_of(m - A/S.VM)
    return (S._fl(cs, rt) + A*cs/S.VM - m*cs) - (S._fl(cl, rt) - m*cl)
ms = np.linspace(rt*np.log(1e-9), rt*np.log(1-1e-9), 20001)
gg = np.array([g(x) for x in ms])
print("ms[0]=%.4e ms[-1]=%.4e n=%d" % (ms[0], ms[-1], ms.size))
print("gg: nan=%d  min=%.4e (at m=%.4e)  max=%.4e (at m=%.4e)" %
      (np.isnan(gg).sum(), gg.min(), ms[gg.argmin()], gg.max(), ms[gg.argmax()]))
ii = np.where(np.sign(gg[:-1])*np.sign(gg[1:]) < 0)[0]
print("sign changes:", ii.size, "at m =", ms[ii][:6])
for m in (-4.30e9, -4.12e9, -4.00e9, -3.93e9, -3.80e9, -2.0e9):
    print("   m=%.4e  cl=%.6f cs=%.6f  g=%+.4e" % (m, c_of(m), c_of(m-A/S.VM), g(m)))