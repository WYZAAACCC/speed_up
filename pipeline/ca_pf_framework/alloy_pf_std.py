#!/usr/bin/env python3
"""alloy_pf_std.py --- standard quantitative alloy PF reference (option (a)), 1D.

Same physics as the reduced MOOSE instrument, but written so every convention is
explicit, in order to (i) cross-check the MOOSE instrument at identical
parameters and (ii) test the THEORETICAL Karma-Rappel coefficient
a_t = 1/(2*sqrt(2)) without any fitting.

Physics (Wheeler-Boettinger-McFadden free energy + Karma-Rappel antitrapping):
  phi(x,t) = 0.5*(1 - tanh(s)),  s = (x - x_if)/(sqrt(2)*W),  x_if = x0 + V*t
  f(phi,c) = RT/Vm*[(1-c)ln(1-c) + c ln c] + h(phi)*A*c/Vm,  h = 3phi^2-2phi^3
  A = dgB + dHf*(1 - T/Tm)     (constants identical to pf1d_moose/p1c_ak3.i)
  => equilibrium partition k_e comes from the COMMON TANGENT (not a parameter)
  dc/dt = d/dx[ D(phi) dc/dx ] + d/dx[ j_at ],   D = D_S + (D_L-D_S)*(1-phi)
  j_at  = a_t * W * (1-k_e) * c * phidot * (dphi/dx)/|dphi/dx|
  for the analytic phi above:  j_at = -(a_t/(2 sqrt2)) (1-k_e) V c sech^2(s)
                               **independent of W**
Theoretical KR/EFKP value: a_t = 1/(2 sqrt 2) = 0.353553.
"""
import numpy as np
from scipy.linalg import solve_banded

R, VM, DGB, DHF, TM = 8.314, 1.1345e-5, 7334.0, 14150.0, 1941.0
C0, DL, DS = 0.036, 9.5e-9, 5.0e-13
A_T_KR = 1.0 / (2.0 * np.sqrt(2.0))


def A_of(T):
    return DGB + DHF * (1.0 - T / TM)


def _fl(c, rt):
    c = np.clip(c, 1e-15, 1 - 1e-15)
    return rt * ((1 - c) * np.log1p(-c) + c * np.log(c))


def _flp(c, rt):
    c = np.clip(c, 1e-15, 1 - 1e-15)
    return rt * np.log(c / (1 - c))


def _ct_roots(T):
    """All sign changes of the tangent-intercept condition, parametrised by the
    common slope m.  c_l = sigmoid(m/rt), c_s = sigmoid((m - A/Vm)/rt)."""
    from scipy.optimize import brentq
    rt, A = R * T / VM, A_of(T)

    def c_of(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x / rt, -700, 700)))

    def g(m):
        cl, cs = c_of(m), c_of(m - A / VM)
        return (_fl(cs, rt) + A * cs / VM - m * cs) - (_fl(cl, rt) - m * cl)

    # scan m over c in [1e-9, 1-1e-9]; the degenerate c->0 root sits at the
    # very cold end and is rejected by the physical-range filter below.
    ms = np.linspace(rt * np.log(1e-9), rt * np.log(1 - 1e-9), 20001)
    gg = np.array([g(x) for x in ms])
    out = []
    for k in np.where(np.sign(gg[:-1]) * np.sign(gg[1:]) < 0)[0]:
        r = brentq(g, ms[k], ms[k + 1], xtol=1e-3, rtol=1e-15)
        out.append((r, c_of(r - A / VM), c_of(r)))
    return out


def common_tangent(T, cmin=1e-4):
    """Common tangent of f_s = f_l + A*c/Vm  ->  (c_s, c_l, k_e)."""
    roots = _ct_roots(T)
    phys = [r for r in roots if r[2] > cmin]
    if not phys:
        raise RuntimeError("no physical common tangent; roots=%s" % roots)
    m, cs, cl = max(phys, key=lambda r: r[2])
    return cs, cl, cs / cl


def sech2(x):
    return 1.0 / np.cosh(x) ** 2


class StdFront:
    def __init__(self, W, V, dx, L, x0=0.2e-6, T=1911.1, c0=C0, dt=None):
        self.W, self.V, self.dx, self.L, self.x0, self.c0 = W, V, dx, L, x0, c0
        self.N = int(round(L / dx))
        self.x = (np.arange(self.N) + 0.5) * dx
        self.T = T
        self.cs_e, self.cl_e, self.ke = common_tangent(T)
        self.c = np.full(self.N, c0)
        self.ld = DL / V
        if dt is None:
            # ACCURACY-limited, not the explicit dx^2/D stability limit: the
            # scheme is implicit.  The physical scale is the relaxation time of
            # the solute boundary layer, l_D^2/D_L.
            dt = 0.05 * self.ld ** 2 / DL
        self.dt = dt

    def phi(self, t):
        s = (self.x - (self.x0 + self.V * t)) / (np.sqrt(2) * self.W)
        return 0.5 * (1 - np.tanh(s)), s

    def _j_at_faces(self, t, a_t, c_face):
        xf = np.arange(self.N + 1) * self.dx
        s_f = (xf - (self.x0 + self.V * t)) / (np.sqrt(2) * self.W)
        return -(a_t / (2 * np.sqrt(2))) * (1 - self.ke) * self.V * c_face * sech2(s_f)

    def run(self, a_t, tend, dt=None, nsteps=None):
        dt = dt if dt is not None else self.dt
        N, dx = self.N, self.dx
        nsteps = nsteps if nsteps is not None else int(round(tend / dt))
        for n in range(nsteps):
            t = (n + 1) * dt
            phi, _ = self.phi(t)
            Df = DS + (DL - DS) * (1 - 0.5 * (phi[:-1] + phi[1:]))   # (N-1,)
            r = dt / dx ** 2
            main = np.ones(N)
            main[1:] += r * (Df[:-1] + Df[1:])      # nodes 1..N-2 interior (last overwritten)
            main[0] = 1.0 + r * Df[0]
            up = -r * Df.copy()                     # upper[k] couples (k, k+1), k=0..N-2
            lo = -r * Df.copy()                     # lower[k] couples (k+1, k)
            main[-1], lo[-1] = 1.0, 0.0
            cf = np.concatenate([[self.c[0]], 0.5 * (self.c[:-1] + self.c[1:]), [self.c[-1]]])
            jf = self._j_at_faces(t, a_t, cf)
            rhs = self.c + dt * (-(jf[1:] - jf[:-1]) / dx)
            rhs[-1] = self.c0
            ab = np.zeros((3, N))
            ab[0, 1:] = up
            ab[1, :] = main
            ab[2, :-1] = lo
            self.c = solve_banded((1, 1), ab, rhs)
        return self.profile(tend)

    def profile(self, t):
        phi, _ = self.phi(t)
        return dict(x=self.x, c=self.c, phi=phi, x_if=self.x0 + self.V * t,
                    ke=self.ke, cs_e=self.cs_e, cl_e=self.cl_e, T=self.T)

    # ---- 判据用的量 ----
    def stats(self, t):
        p = self.profile(t)
        x, c, x_if = p['x'], p['c'], p['x_if']
        xi = x - x_if
        ic = int(np.searchsorted(xi, 0.0))
        c_int = np.interp(0.0, xi, c)
        deep = c[xi < -6 * self.ld]
        c_s_deep = float(np.median(deep)) if deep.size else np.nan
        k_eff = c_s_deep / c_int
        tgt = self.c0 / self.ke
        m = (xi > 0.3 * self.ld) & (xi < 3 * self.ld) & (c > self.c0)
        ld_m = np.nan
        if m.sum() >= 5:
            ld_m = -1.0 / np.polyfit(xi[m], np.log(c[m] - self.c0), 1)[0]
        ana = self.c0 + (tgt - self.c0) * np.exp(-np.maximum(xi, 0) / self.ld)
        mw = (xi > 0) & (xi < 3 * self.ld)
        spike = float(np.max((c[mw] - ana[mw]) / (tgt - self.c0))) if mw.sum() else np.nan
        return dict(c_int=c_int, c_s_deep=c_s_deep, k_eff=k_eff, ke=self.ke,
                    tgt=tgt, dev=c_int / tgt - 1.0, c_min=float(c.min()),
                    ld_m=ld_m, ld_dev=ld_m / self.ld - 1.0, spike=spike)