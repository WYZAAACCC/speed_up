#!/usr/bin/env python3
"""_chk_ct.py --- SA-1: does the free energy admit a COMMON TANGENT?

This is the sharp form of README (pf1d_moose) 7.4 "root-cause candidate #2",
upgraded from a candidate to a PROOF.

Instrument free energy (pf1d_moose/p1c_ak3.i line 68):
    f(phi,c) = (RT/Vm)*[c ln c + (1-c)ln(1-c)] + h(phi)*(A/Vm)*c,   h = 3phi^2-2phi^3
  => f_s - f_l = (A/Vm)*c : linear in c with NO constant term.

Common tangent of f_l and f_s = f_l + (A/Vm)c requires a slope m and a pair
(c_s < c_l) with equal slopes AND equal intercepts.  Combining the two:
    f_l(c_s) - f_l(c_l) - f_l'(c_l)(c_s - c_l) = -(A/Vm) c_s
The LHS is >= 0 by convexity of f_l; the RHS is < 0 for A > 0.  => NO SOLUTION,
except the degenerate c -> 0 root (where both sides vanish).

Consequence: the interface has NO thermodynamically defined local equilibrium,
so a Karma-Rappel antitrapping current -- whose entire derivation assumes local
equilibrium -- can never repair it.  That is exactly the observed 50x
KR-amplitude and the W -> 0 divergence.

The corrected (standard) form carries the constant of the linear term:
    f_s - f_l = [a(1-c) + b c]/Vm
which does admit a common tangent; (a, b) are fixed by the tie line at the
liquidus of the alloy, i.e. (c_s, c_l) = (k_e c0, c0).
"""
import numpy as np
import alloy_pf_std as S

RT_VM = S.R * 1911.1 / S.VM
AVM = S.A_of(1911.1) / S.VM
C0 = S.C0
KE = 0.6303
ok = {}


def rec(tag, good, extra=''):
    ok[tag] = bool(good)
    print('   %-58s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


def I(c):
    c = np.clip(c, 1e-15, 1 - 1e-15)
    return (1 - c) * np.log1p(-c) + c * np.log(c)


def crossings(m, g):
    s = np.sign(g)
    return np.where(s[:-1] * s[1:] < 0)[0]


def g_instrument(m):
    """intercept difference for f_s = f_l + (A/Vm)c  (slope-parametrised)"""
    cl = 1.0 / (1.0 + np.exp(-np.clip(m / RT_VM, -700, 700)))
    cs = 1.0 / (1.0 + np.exp(-np.clip((m - AVM) / RT_VM, -700, 700)))
    return (RT_VM * I(cs) + AVM * cs - m * cs) - (RT_VM * I(cl) - m * cl)


def g_corrected(m, a, b):
    cl = 1.0 / (1.0 + np.exp(-np.clip(m / RT_VM, -700, 700)))
    cs = 1.0 / (1.0 + np.exp(-np.clip((m - (b - a)) / RT_VM, -700, 700)))
    fs = RT_VM * I(cs) + (a * (1 - cs) + b * cs)
    return (fs - m * cs) - (RT_VM * I(cl) - m * cl)


ms = np.linspace(RT_VM * np.log(1e-9), RT_VM * np.log(1 - 1e-9), 20001)

print("---- SA-1: common tangent of the INSTRUMENT free energy ----")
print("   A/Vm = %.4e Pa (= J/m^3)   RT/Vm = %.4e" % (AVM, RT_VM))
gg = np.array([g_instrument(x) for x in ms])
ii = crossings(ms, gg)
print("   g(m) in [%.4e, %.4e] ; sign changes = %d" % (gg.min(), gg.max(), ii.size))
rec('SA-1a instrument f admits a common tangent', ii.size > 0,
    '=> NO thermodynamic local equilibrium exists' if ii.size == 0 else '')
# the only "root" is the degenerate c->0 one
rec('SA-1b the only root is the degenerate c->0 one',
    gg.min() > 0 and ms[gg.argmin()] < -1e10,
    'min g = %.3e at m = %.3e' % (gg.min(), ms[gg.argmin()]))

print()
print("---- SA-1c calibrated standard form ----")
cs_t, cl_t = KE * C0, C0
a = RT_VM * (np.log1p(-cl_t) - np.log1p(-cs_t))
b = a + RT_VM * np.log((cl_t / (1 - cl_t)) / (cs_t / (1 - cs_t)))
print("   tie line at T=1911.1 K: c_s = %.5f  c_l = %.5f  k = %.4f" %
      (cs_t, cl_t, cs_t / cl_t))
print("   => a = %.4e J/m^3   b = %.4e J/m^3   (b-a = %.4e ; A/Vm = %.4e)" %
      (a, b, b - a, AVM))
gg2 = np.array([g_corrected(x, a, b) for x in ms])
ii2 = crossings(ms, gg2)
print("   sign changes = %d" % ii2.size)
if ii2.size:
    from scipy.optimize import brentq
    m = brentq(lambda x: g_corrected(x, a, b), ms[ii2[-1]], ms[ii2[-1] + 1], xtol=1e-3)
    cl = 1.0 / (1.0 + np.exp(-m / RT_VM))
    cs = 1.0 / (1.0 + np.exp(-(m - (b - a)) / RT_VM))
    print("   root: c_s = %.6f  c_l = %.6f  k = %.6f" % (cs, cl, cs / cl))
    rec('SA-1d corrected f admits a common tangent at the tie line',
        abs(cs / cl - KE) < 2e-3, 'k = %.5f vs target %.4f' % (cs / cl, KE))
else:
    rec('SA-1d corrected f admits a common tangent at the tie line', False, 'no root')

print()
print("SA-1 summary: %s" % ('ALL PASS' if all(ok.values()) else
                            '%d/%d' % (sum(ok.values()), len(ok))))