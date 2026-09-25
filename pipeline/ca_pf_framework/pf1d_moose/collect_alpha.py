# -*- coding: utf-8 -*-
# Unified report of every ALPHA scan in pf1d_moose.
import io, os, re, json

HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
KE = 0.63532
CINF = 0.036
TGT = CINF / KE
WV = {"200": 2.0e-7, "60": 6.0e-8, "20": 2.0e-8}
DL, V = 9.5e-9, 0.1


def read_rows(p):
    return [r.split(",") for r in io.open(p, encoding="utf-8").read().strip().splitlines()]


def cint(d):
    fs = [f for f in os.listdir(d) if re.search(r"_line_(\d+)\.csv$", f)]
    if not fs:
        return None, None
    f = max(fs, key=lambda f: int(re.search(r"_line_(\d+)\.csv$", f).group(1)))
    rows = read_rows(os.path.join(d, f))
    if len(rows) < 2:
        return None, None
    h = rows[0]
    ix = {k: i for i, k in enumerate(h)}
    xs = [float(r[ix["x"]]) for r in rows[1:]]
    cs = [float(r[ix["c"]]) for r in rows[1:]]
    ps = [float(r[ix["phi"]]) for r in rows[1:]]
    for i in range(len(xs) - 1):
        if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
            return cs[i], max(cs)
    return None, None


rows_out = []
for d in sorted(os.listdir(HERE)):
    if not re.match(r"(ak2_|ak3_|ak4_)W", d):
        continue
    m = re.match(r"(ak\d)_W(\d+)_A([-\d.]+)$", d)
    if not m:
        continue
    src, Wn, A = m.group(1), m.group(2), float(m.group(3))
    dd = os.path.join(HERE, d)
    pp = [f for f in os.listdir(dd) if re.match(r"p1c_ak\d_out\.csv$", f)]
    probe = {}
    if pp:
        rows = read_rows(os.path.join(dd, pp[0]))
        h, last = rows[0], rows[-1]
        for n in h:
            if n.startswith("c_p"):
                probe[n] = float(last[h.index(n)])
    ci, cpk = cint(dd)
    if ci is None:
        continue
    rows_out.append(dict(src=src, W=float(Wn), A=A, c_int=ci, c_peak=cpk,
                         target=TGT, probes=probe))

print("target c_int = %.6f   (k_e(T=1911.1K) = %.5f)" % (TGT, KE))
print("%-6s %-5s %-6s %-6s %-9s %-9s | %s" % (
    "src", "W(nm)", "ALPHA", "VW/DL", "c_int", "vs target", "c_s probes [um:c]"))
for r in sorted(rows_out, key=lambda r: (r["W"], r["A"])):
    pv = "  ".join("%s" % ("%.6f" % v) for k, v in sorted(r["probes"].items()))
    print("%-6s %-5.0f %-6.2f %-6.3f %-9.6f %+8.2f%% | %s" % (
        r["src"], r["W"], r["A"], V * WV[str(int(r["W"]))] / DL, r["c_int"],
        100 * (r["c_int"] - TGT) / TGT, pv))
io.open(os.path.join(HERE, "alpha_summary.json"), "w", encoding="utf-8").write(
    json.dumps(rows_out, indent=1))