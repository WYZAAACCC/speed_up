import io, os, re
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
KE = 0.63532
CINF = 0.036
TGT = CINF / KE
print("target c_int = %.6f ; analytic b.l. amplitude = %.6f" % (TGT, TGT - CINF))
print("%-14s %-9s %-9s %-9s %-9s" % ("tag", "c_int", "amp=c_int-c0", "c_s@2.5um", "c_s@3.5um"))
for d in sorted(os.listdir(HERE)):
    if not (d.startswith("ak2_")) and not d.startswith("var_"):
        continue
    p = os.path.join(HERE, d, "p1c_ak2_out.csv" if d.startswith("ak2_") else "p1c_var_out.csv")
    if not os.path.exists(p):
        continue
    rows = io.open(p, encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(","); last = rows[-1].split(",")
    if "c_p0" not in hdr:
        continue
    p0 = float(last[hdr.index("c_p0")]); p1 = float(last[hdr.index("c_p1")])
    # c_int from the last profile
    fs = [f for f in os.listdir(os.path.join(HERE, d)) if re.search(r"_line_(\d+)\.csv$", f)]
    ci = float("nan")
    if fs:
        f = max(fs, key=lambda f: int(re.search(r"_line_(\d+)\.csv$", f).group(1)))
        pr = io.open(os.path.join(HERE, d, f), encoding="utf-8").read().strip().splitlines()
        if len(pr) > 1:
            h = pr[0].split(",")
            ix = {k: i for i, k in enumerate(h)}
            xs = [float(r.split(",")[ix["x"]]) for r in pr[1:]]
            cs = [float(r.split(",")[ix["c"]]) for r in pr[1:]]
            ps = [float(r.split(",")[ix["phi"]]) for r in pr[1:]]
            for i in range(len(xs) - 1):
                if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
                    ci = cs[i]
                    break
    print("%-14s %-9.6f %-+9.3e %-9.6f %-9.6f" % (d, ci, ci - CINF, p0, p1))