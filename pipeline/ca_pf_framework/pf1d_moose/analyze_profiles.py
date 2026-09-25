# -*- coding: utf-8 -*-
# Local flux accounting on the final-time profile written by LineValueSampler.
# Columns: x y z id c phi
# Checks (all exact in the steady moving frame):
#   liquid (phi~0):  D_L dc/dx = V (c_inf - c)
#   interface:       D_L dc/dx|_+ + V (c_l - c_s) = 0
import io, os, re, sys, math

DL = 9.5e-9
V = 0.1
C0 = 0.036
K = 0.6303
LD = DL / V          # 95 nm


def last_line_csv(d):
    fs = [f for f in os.listdir(d) if re.search(r"_line_(\d+)\.csv$", f)]
    if not fs:
        return None
    f = max(fs, key=lambda f: int(re.search(r"_line_(\d+)\.csv$", f).group(1)))
    return os.path.join(d, f)


def load(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    hdr = [h.strip() for h in rows[0].split(",")]
    ix = {h: i for i, h in enumerate(hdr)}
    x, c, p = [], [], []
    for r in rows[1:]:
        v = r.split(",")
        x.append(float(v[ix["x"]]))
        c.append(float(v[ix["c"]]))
        p.append(float(v[ix["phi"]]))
    return x, c, p


def xint_of(x, p):
    for i in range(len(x) - 1):
        if (p[i] - 0.5) * (p[i + 1] - 0.5) <= 0 and p[i] != p[i + 1]:
            t = (0.5 - p[i]) / (p[i + 1] - p[i])
            return x[i] + t * (x[i + 1] - x[i])
    return None


def dc(frac, x, y, xi):
    # central difference at the sample nearest xi
    j = min(range(len(x)), key=lambda i: abs(x[i] - xi))
    j = max(1, min(len(x) - 2, j))
    return (y[j + 1] - y[j - 1]) / (x[j + 1] - x[j - 1]), x[j]


def main(d):
    path = last_line_csv(d)
    x, c, p = load(path)
    xi = xint_of(x, p)
    print("== %s   (%s)" % (d, os.path.basename(path)))
    print("   points=%d  xmax=%.4g  x_int(phi=0.5)=%.5g" % (len(x), x[-1], xi))
    # interface velocity from phi: fit phi=0.5 travel vs t is imposed => V=0.1
    print("   l_D = %.1f nm" % (LD * 1e9))
    # ---- liquid side: fit B in c = c_inf + B exp(-xi/l_D)
    print("   --- liquid side (phi<0.02): xi[um]  c  c_an(analytic b.l.)  D_L dc/dx  V(c0-c) ---")
    num, den = 0.0, 0.0
    for i in range(len(x)):
        if p[i] < 0.02 and x[i] > xi:
            s = x[i] - xi
            w = math.exp(-s / LD)
            num += w * (c[i] - C0)
            den += w * w
    B = num / den if den else float("nan")
    cl_int = C0 + B
    print("   fitted B = %.6e   => c_l_int = c_inf + B = %.6f   (1/k_e*c0 = %.6f)"
          % (B, cl_int, C0 / K))
    for s_nm in (0, 20, 50, 100, 200, 400, 800):
        s = s_nm * 1e-9
        if xi + s > x[-1]:
            continue
        g, xa = dc(1, x, c, xi + s)
        ca = C0 + B * math.exp(-s / LD)
        print("   s=%6.0f nm  x=%.4g  c=%.6f  c_an=%.6f  D_L c'=%.4e  V(c0-c)=%.4e  ratio=%.3f"
              % (s_nm, xa, c[min(range(len(x)), key=lambda i: abs(x[i] - xa))], ca,
                 DL * g, V * (C0 - ca), DL * g / (V * (C0 - ca)) if ca != C0 else float("nan")))
    # ---- solid side
    print("   --- solid side (phi>0.98) ---")
    for s_nm in (0, 50, 100, 200, 400, 600, 800, 1200):
        if xi - s_nm * 1e-9 < x[0]:
            continue
        j = min(range(len(x)), key=lambda i: abs(x[i] - (xi - s_nm * 1e-9)))
        print("   s=%6.0f nm  x=%.4g  phi=%.4f  c=%.8f  dev=%+.3e" % (s_nm, x[j], p[j], c[j], c[j] - C0))
    # ---- interface jump from the analytic continuation
    cs = None
    for i in range(len(x) - 1, -1, -1):
        if p[i] > 0.98 and x[i] < xi:
            cs = c[i]
            break
    if cs is not None:
        print("   k_eff(int) = c_s/c_l_int = %.6f   (k_e = %.4f)" % (cs / cl_int, K))
    # ---- integral excess
    ex = 0.0
    for i in range(len(x) - 1):
        s = 0.5 * (x[i] + x[i + 1]) - xi
        ca = C0 + (B * math.exp(-s / LD) if s > 0 else 0.0)
        ex += 0.5 * ((c[i] - ca) + (c[i + 1] - ca)) * (x[i + 1] - x[i])
    print("   interface excess  int(c - c_an) dx = %.4e  (per unit area)" % ex)


if __name__ == "__main__":
    for d in sys.argv[1:]:
        main(d)
        print("")