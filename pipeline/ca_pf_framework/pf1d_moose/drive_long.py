# -*- coding: utf-8 -*-
# Experiment D: long-travel ALPHA scan.
# Rationale (found 2026-09-23, this session):
#   * Domain length does NOT matter for the deposited solid composition (A vs B identical
#     to 6 digits) => the far-field Dirichlet truncation is NOT the bias.
#   * The bias decays with interface TRAVEL (time): travel 0.8um -> dev -2.14e-4,
#     travel 1.8um -> -3.47e-5, travel 2.6um -> -1.68e-5 (deep solid, W=200nm).
#     => it is a start-up transient with decay length ~1um (>> l_D = 95nm).
#   * Therefore the clean ALPHA criterion is the ASYMPTOTIC (steady) deposition
#     composition: run a long travel and read dev at several deposit times.
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")

XMAX = 1.2e-5
NX = 2400
TEND = 1.0e-4
DT = 5.0e-8
PROBES = [2.0e-6, 4.0e-6, 6.0e-6, 8.0e-6, 1.0e-5]
X0 = 2.0e-7
V = 0.1


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(Wv, A, probes=PROBES):
    s = io.open(BASE, encoding="utf-8").read()
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % XMAX, 1)
    s = s.replace("nx = 1200", "nx = %d" % NX, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % TEND, 1)
    s = s.replace("dt = 5.0e-8", "dt = %.4e" % DT, 1)
    if Wv != "3.0e-8":
        s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + Wv + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(probes) + "\n", s)
    assert out != s
    s = out
    vp = ("[VectorPostprocessors]\n"
          "  [line]\n"
          "    type = LineValueSampler\n"
          "    variable = 'c phi'\n"
          "    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n"
          "    num_points = 240\n"
          "    sort_by = x\n"
          "    execute_on = FINAL\n"
          "  []\n"
          "[]\n" % XMAX)
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    return s


def parse_csv(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(",")
    return hdr, rows[-1].split(",")


def run_case(case):
    tag, Wv, A = case
    d = os.path.join(HERE, "long_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_long.i"), "w", encoding="utf-8").write(make_input(Wv, A))
    p0 = os.path.join(d, "p1c_long_out.csv")
    if os.path.exists(p0):
        os.remove(p0)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_long.i"], cwd=d, capture_output=True,
                           text=True, timeout=21600, env=ENV)
        rc, out = r.returncode, r.stdout
    except Exception as e:
        return tag, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    nz = out.count("\n 0 Nonlinear") + (1 if out.startswith(" 0 Nonlinear") else 0)
    res = {"rc": rc, "sec": dt, "jit": out.count("JIT compile failed"), "zstep": nz,
           "steps": out.count("Time Step"), "err_line": ""}
    for l in out.splitlines():
        if "ERROR" in l:
            res["err_line"] = l.strip()[:160]
            break
    if os.path.exists(p0):
        hdr, last = parse_csv(p0)
        for n in hdr:
            if n.startswith("c_p"):
                res[n] = float(last[hdr.index(n)])
    return tag, res


def cases():
    out = []
    for A in (0.0, -0.5, -1.0, -2.0, 2.0):
        out.append(("W200_A%+.2f" % A, "2.0e-7", "%.2f" % A))
    for A in (0.0, -0.5, -1.0, -2.0):
        out.append(("W400_A%+.2f" % A, "4.0e-7", "%.2f" % A))
    return out


if __name__ == "__main__":
    print("travel(x) [um]: " + "  ".join("%.1f" % ((x - X0) * 1e6) for x in PROBES))
    print("tag              rc sec    jit zst steps | " +
          "  ".join("dev@%.1fum" % (x * 1e6) for x in PROBES))
    cs = cases()
    res_all = {}
    with cf.ThreadPoolExecutor(max_workers=len(cs)) as ex:
        for tag, res in ex.map(run_case, cs):
            res_all[tag] = res
            keys = sorted([k for k in res if k.startswith("c_p")], key=lambda k: int(k[3:]))
            pv = "  ".join("%+.3e" % (res[k] - 0.036) for k in keys)
            print("%-16s %-2s %-6.0f %-3s %-3s %-5s | %s" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("steps", "-"), pv))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])
    io.open(os.path.join(HERE, "long_results.json"), "w", encoding="utf-8").write(
        repr(res_all))