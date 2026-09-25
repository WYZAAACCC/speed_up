# -*- coding: utf-8 -*-
# Experiment I: calibrate ALPHA against the RIGHT observable.
# Established this session:
#   * The deposited solid composition is pinned to c_inf by the steady moving-frame flux
#     identity  M mu_xi - V c = const  (checked: c_deep = 0.036000 for every ALPHA),
#     so dev = c_s - c_inf is NOT a usable ALPHA criterion (it is ~0 by construction).
#   * The usable observable is c_int = c at phi = 0.5, the interface liquid composition.
#     Local equilibrium (LKT) requires  c_int = c_inf / k_e(T)  with
#       k_e(1911.1 K) = 0.6356  ->  c_int_target = 0.05664
#     (checked against the model's own f_loc: equilibrium pair for T = 1911.1 K gives
#      c_s = 0.035952 = c_inf when c_l = 0.05664).
#   * ALPHA < 0 LOWERS c_int (worse). So the needed direction is ALPHA > 0.
# (previous run crashed on ALPHA > 0 only because "%+.2f" wrote "+2.00" and MOOSE's parsed
#  constants reject a leading '+' -- formatting bug, not physics.)
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")
KE = 0.6356
CINT_TARGET = 0.036 / KE


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(xmax, nx, tend, Wv, A, probes, lvs_n):
    s = io.open(BASE, encoding="utf-8").read()
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % xmax, 1)
    s = s.replace("nx = 1200", "nx = %d" % nx, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % tend, 1)
    if Wv != "3.0e-8":
        s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + Wv + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(probes) + "\n", s)
    assert out != s
    s = out
    vp = ("[VectorPostprocessors]\n  [line]\n    type = LineValueSampler\n"
          "    variable = 'c phi'\n    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n    num_points = %d\n    sort_by = x\n  []\n[]\n"
          % (xmax, lvs_n))
    return s.replace("[Executioner]", vp + "\n[Executioner]", 1)


def read_rows(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    return [r.split(",") for r in rows]


def profile_last(d):
    fs = [f for f in os.listdir(d) if re.search(r"_line_(\d+)\.csv$", f)]
    if not fs:
        return None
    f = max(fs, key=lambda f: int(re.search(r"_line_(\d+)\.csv$", f).group(1)))
    return os.path.join(d, f)


def run_case(case):
    tag, xmax, nx, tend, Wv, A, probes = case
    d = os.path.join(HERE, "ak2_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_ak2.i"), "w", encoding="utf-8").write(
        make_input(xmax, nx, tend, Wv, A, probes, 500 if xmax > 7e-6 and nx > 2000 else 200))
    p0 = os.path.join(d, "p1c_ak2_out.csv")
    if os.path.exists(p0):
        os.remove(p0)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_ak2.i"], cwd=d, capture_output=True,
                           text=True, timeout=21600, env=ENV)
        rc, out = r.returncode, r.stdout + chr(10) + "--STDERR--" + chr(10) + r.stderr
    except Exception as e:
        return tag, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    res = {"rc": rc, "sec": dt, "jit": out.count("JIT compile failed"),
           "zstep": out.count("\n 0 Nonlinear"), "steps": out.count("Time Step"),
           "err_line": ""}
    for l in out.splitlines():
        if "ERROR" in l:
            res["err_line"] = l.strip()[:170]
            break
    if os.path.exists(p0):
        rows = read_rows(p0)
        hdr, last = rows[0], rows[-1]
        for n in hdr:
            if n.startswith("c_p"):
                res[n] = float(last[hdr.index(n)])
    pf = profile_last(d)
    if pf:
        rows = read_rows(pf)
        if len(rows) > 1:
            hdr = rows[0]
            ix = {h: i for i, h in enumerate(hdr)}
            xs = [float(r[ix["x"]]) for r in rows[1:]]
            cs = [float(r[ix["c"]]) for r in rows[1:]]
            ps = [float(r[ix["phi"]]) for r in rows[1:]]
            for i in range(len(xs) - 1):
                if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
                    res["xint"] = xs[i]
                    res["c_int"] = cs[i]
                    break
            res["c_peak"] = max(cs)
            # deep solid = deepest sample with phi > 0.999
            for j in range(len(xs)):
                if ps[j] > 0.999:
                    res["c_deep"] = cs[j]
                    res["x_deep"] = xs[j]
                    break
    return tag, res


def cases():
    out = []
    for A in (0.0, 1.0, 2.0, 4.0, 8.0):
        out.append(("W200_A%.2f" % A, 8.0e-6, 1600, 4.5e-5, "2.0e-7", "%.2f" % A,
                    [2.5e-6, 3.5e-6]))
    for A in (0.0, 1.0, 2.0, 4.0):
        out.append(("W20_A%.2f" % A, 8.0e-6, 4000, 4.5e-5, "2.0e-8", "%.2f" % A,
                    [2.5e-6, 3.5e-6]))
    return out


if __name__ == "__main__":
    print("target: c_int = c_inf/k_e = %.5f  (k_e = %.4f at T=1911.1 K)" % (CINT_TARGET, KE))
    print("tag          rc sec  jit zst | x_int    c_int    c_peak   c_deep   k_eff=c_deep/c_int")
    with cf.ThreadPoolExecutor(max_workers=9) as ex:
        for tag, res in ex.map(run_case, cases()):
            ci, cd = res.get("c_int"), res.get("c_deep")
            ke = (cd / ci) if (ci and cd) else float("nan")
            print("%-12s %-2s %-4.0f %-3s %-3s | %-8.4g %-8.6f %-8.6f %-8.6f %.4f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("xint", float("nan")),
                ci or float("nan"), res.get("c_peak", float("nan")),
                cd or float("nan"), ke))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])