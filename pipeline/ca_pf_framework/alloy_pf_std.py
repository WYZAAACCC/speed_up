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
            main[1:-1] += r * (Df[:-1] + Df[1:])      # nodes 1..N-2 interior
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

# ===========================================================================
# 三元（Al+V 双溶质）扩展 —— 2026-09-25
# ===========================================================================
# 动机：MATH_FRAMEWORK.md §5.1 的状态量是 c_i (i in {Al,V})，但仪器 StdFront
# 只有标量 c。三元闭合见 ternary_thermo.py（单一参数来源）。
#
# 必须如实记的一条结构性结论：在
#     (i) 理想置换溶液闭合（L = 0），且
#     (ii) 扩散为对角（D_ij = D_i delta_ij）
# 两个前提下，这套方程**逐溶质完全解耦** —— 每个溶质各自跑一个与 StdFront
# 同形的方程，只共享解析前沿 phi(x,t) 与 k_i^e = exp(-dg_i/RT)。
# 所以三元在前沿这一层的价值是：
#   (a) 参数被 (star) 液相线恒等式自洽锁定（见 _chk_ternary.py T-A7/T-A8）；
#   (b) 给出 Al / V 两条**正交**通道（两者的 k 分居 1 的两侧），
#       使"溶质分配"的符号错误无处藏身（老的标量 k=0.6303 就是被 V 用了）；
# 真正的**耦合**来自 L != 0（热力学）与 D 的非对角项（动力学），两者都必须
# 由 CALPHAD 给（CALPHAD_REQUEST.md B4/C）。本类为它们留了 D_offdiag 接口。
# ===========================================================================

class StdFrontMulti:
    """三元（n_solute >= 1）等温定向凝固前沿仪器。

    与 StdFront 逐条对应，只是每个溶质一套 c / D / k / j_at。
    n_solute = 1 时数值上与 StdFront 同（但**不是**同一份代码，不做逐位保证）。
    """

    def __init__(self, W, V, dx, L, closure, c0, D_L, D_S,
                 x0=0.2e-6, T=1911.1, dt=None, D_offdiag=None, jat_sign=-1.0):
        # jat_sign: 抗截留项的符号。**默认 -1.0 是经判据定出来的正确符号**
        #（+1 会让两个溶质同时往错误方向走；推导与数值见 _chk_ternary.py T-A11）。
        # 注意 StdFront._j_at_faces 用的是 +1 的写法（且那条 run() 路径从未被执行过，
        # 见 T-A11 的记账）—— A1 修自由能时必须一并判决标量版的符号。
        # 移动坐标系里质量守恒强制 c_s(deep) = c0（已实测），所以正确的判据是
        # c_int = c0/k_i：k_i < 1（Al）要 c_int > c0、k_i > 1（V）要 c_int < c0。
        # 见 _chk_ternary.py T-A11 的符号判决。
        self.jat_sign = float(jat_sign)
        self.W, self.V, self.dx, self.L = W, V, dx, L
        self.x0, self.T = x0, T
        self.cl = closure
        self.names = list(closure.names)
        self.ns = len(self.names)
        self.N = int(round(L / dx))
        self.x = (np.arange(self.N) + 0.5) * dx
        self.c0 = np.array([float(c0[n]) for n in self.names])
        self.DL = np.array([float(D_L[n]) for n in self.names])
        self.DS = np.array([float(D_S[n]) for n in self.names])
        self.D_offdiag = D_offdiag          # None => 对角（理想闭合）
        self.ke = np.array([closure.k(T)[n] for n in self.names])
        self.cs_e = self.ke * self.c0
        self.ld = self.DL / V               # 每溶质的边界层厚度 l_D,i
        self.c = np.tile(self.c0[:, None], (1, self.N))
        if dt is None:
            # 取最严的那个溶质（l_D^2/D 最小者）—— 与 StdFront 同一条规则
            dt = 0.05 * float(np.min(self.ld ** 2 / self.DL))
        self.dt = dt

    def phi(self, t):
        s = (self.x - (self.x0 + self.V * t)) / (np.sqrt(2) * self.W)
        return 0.5 * (1 - np.tanh(s)), s

    def _j_at_faces(self, t, a_t, c_face):
        """逐溶质抗截留通量（R4 的向量化形式）。c_face: (ns, N+1)。"""
        xf = np.arange(self.N + 1) * self.dx
        s_f = (xf - (self.x0 + self.V * t)) / (np.sqrt(2) * self.W)
        amp = (self.jat_sign * -(a_t / (2 * np.sqrt(2))) * (1.0 - self.ke) * self.V)
        return amp[:, None] * c_face * sech2(s_f)[None, :]

    def run(self, a_t, tend, dt=None, nsteps=None):
        dt = dt if dt is not None else self.dt
        N, dx, ns = self.N, self.dx, self.ns
        nsteps = nsteps if nsteps is not None else int(round(tend / dt))
        for n in range(nsteps):
            t = (n + 1) * dt
            phi, _ = self.phi(t)
            phif = 0.5 * (phi[:-1] + phi[1:])
            cnew = np.empty_like(self.c)
            for i in range(ns):
                Df = self.DS[i] + (self.DL[i] - self.DS[i]) * (1.0 - phif)
                r = dt / dx ** 2
                main = np.ones(N)
                main[1:-1] += r * (Df[:-1] + Df[1:])
                main[0] = 1.0 + r * Df[0]
                up = -r * Df.copy()
                lo = -r * Df.copy()
                main[-1], lo[-1] = 1.0, 0.0
                ci = self.c[i]
                cf = np.concatenate([[ci[0]], 0.5 * (ci[:-1] + ci[1:]), [ci[-1]]])
                jf = self._j_at_faces(t, a_t, cf[None, :])[i]
                rhs = ci + dt * (-(jf[1:] - jf[:-1]) / dx)
                rhs[-1] = self.c0[i]
                ab = np.zeros((3, N))
                ab[0, 1:] = up
                ab[1, :] = main
                ab[2, :-1] = lo
                cnew[i] = solve_banded((1, 1), ab, rhs)
            self.c = cnew
        return self.profile(tend)

    def profile(self, t):
        phi, _ = self.phi(t)
        return dict(x=self.x, c=self.c, phi=phi, x_if=self.x0 + self.V * t,
                    ke=self.ke.copy(), names=list(self.names), T=self.T)

    def stats(self, t, i):
        """第 i 个溶质的统计量（定义与 StdFront.stats 逐条一致）。"""
        p = self.profile(t)
        x, c, x_if = p['x'], p['c'][i], p['x_if']
        xi = x - x_if
        c_int = float(np.interp(0.0, xi, c))
        deep = c[xi < -6 * self.ld[i]]
        c_s_deep = float(np.median(deep)) if deep.size else np.nan
        k_eff = c_s_deep / c_int
        tgt = self.c0[i] / self.ke[i]
        ana = self.c0[i] + (tgt - self.c0[i]) * np.exp(-np.maximum(xi, 0) / self.ld[i])
        mw = (xi > 0) & (xi < 3 * self.ld[i])
        spike = (float(np.max((c[mw] - ana[mw]) / (tgt - self.c0[i])))
                 if mw.sum() else np.nan)
        return dict(name=self.names[i], c_int=c_int, c_s_deep=c_s_deep,
                    k_eff=k_eff, ke=float(self.ke[i]), tgt=tgt,
                    dev=c_int / tgt - 1.0, c_min=float(c.min()),
                    spike=spike)

    def stats_all(self, t):
        return {n: self.stats(t, i) for i, n in enumerate(self.names)}
