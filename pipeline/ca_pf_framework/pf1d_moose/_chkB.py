import io, os, re, glob
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
for tag in ("B_1D", "B_3D"):
    fs = glob.glob(os.path.join(HERE, tag, "profile_line_*.csv"))
    if not fs:
        print(tag, "no profile"); continue
    f = max(fs, key=lambda p: int(re.search(r"_(\d+)\.csv$", p).group(1)))
    rows = io.open(f, encoding="utf-8").read().strip().splitlines()
    h = rows[0].split(",")
    ix = {k: i for i, k in enumerate(h)}
    xs = [float(r.split(",")[ix["x"]]) for r in rows[1:]]
    cs = [float(r.split(",")[ix["c"]]) for r in rows[1:]]
    ps = [float(r.split(",")[ix["phi"]]) for r in rows[1:]]
    xint = None
    for i in range(len(xs) - 1):
        if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
            xint = xs[i]; break
    print("%-6s profile=%s  n=%d  phi in [%.3f, %.3f]  phi@x=0: %.4f  x_int=%.4g"
          % (tag, os.path.basename(f), len(rows) - 1, min(ps), max(ps), ps[0], xint if xint else float("nan")))
    print("        c: min %.6f max %.6f   c@x=0 %.6f" % (min(cs), max(cs), cs[0]))