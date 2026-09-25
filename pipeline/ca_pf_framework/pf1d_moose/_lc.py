# L_c = width over which the c-profile is distorted behind the phi=0.5 interface
import io, os, re
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"


def load(d, base):
    fs = [f for f in os.listdir(os.path.join(HERE, d)) if re.search(r"_line_(\d+)\.csv$", f)]
    if not fs:
        return None
    f = max(fs, key=lambda f: int(re.search(r"_line_(\d+)\.csv$", f).group(1)))
    rows = io.open(os.path.join(HERE, d, f), encoding="utf-8").read().strip().splitlines()
    h = rows[0].split(",")
    ix = {k: i for i, k in enumerate(h)}
    xs, cs, ps = [], [], []
    for r in rows[1:]:
        v = r.split(",")
        xs.append(float(v[ix["x"]])); cs.append(float(v[ix["c"]])); ps.append(float(v[ix["phi"]]))
    return xs, cs, ps


print("%-14s %-8s %-10s %-10s %-10s %-8s" % ("tag", "W(nm)", "x_int(um)", "c_int", "c_plateau", "L_c(um)"))
for d, Wn in (("var_W200_ref", 200), ("var_W60_ref", 60), ("var_W20_ref", 20)):
    xs, cs, ps = load(d, d)
    xint = None
    for i in range(len(xs) - 1):
        if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
            xint = xs[i]; j = i
            break
    cin = cs[j]
    # plateau = max depth where phi>0.999
    k = 0
    while k < len(xs) and ps[k] < 0.999:
        k += 1
    cpl = cs[k]
    # L_c = distance behind xint at which |c - cpl| <= 1% of |c_int - cpl|
    amp = abs(cin - cpl)
    Lc = float("nan")
    for i in range(j, -1, -1):
        if abs(cs[i] - cpl) <= 0.01 * amp:
            Lc = xint - xs[i]
            break
    print("%-14s %-8d %-10.4g %-10.6f %-10.6f %-8.4g" % (d, Wn, xint, cin, cpl, Lc * 1e6))