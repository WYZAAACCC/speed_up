# -*- coding: utf-8 -*-
# Experiment F: isolate the universal residual dev = -2.78e-5 found in drive_long.py
#   (independent of ALPHA and of W at V*W/D_L = 2.1 .. 4.2).
# Factors tested, one at a time:
#   W        : 200 / 60 / 20 nm  -> V*W/D_L = 2.10 / 0.63 / 0.21 (thin-interface limit)
#   xmax     : 5.6 / 8 / 16 um   -> far-field Dirichlet truncation N_BC = 11.6 / 36.8 / 121
#   dx       : 10 / 5 / 2.5 nm   -> discretisation
# Fixed: V = 0.1 m/s, D_L = 9.5e-9, l_D = 95 nm, travel = 4.3 um (t_end = 4.5e-5 s),
#        interface 0.2 -> 4.5 um, probes 1.0 and 2.0 um behind the final interface.
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")
PROBES = [2.5e-6, 3.5e-6]


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(xmax, nx, tend, Wv, A, lvs_n):
    s = io.open(BASE, encoding="utf-8").read()
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % xmax, 1)
    s = s.replace("nx = 1200", "nx = %d" % nx, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % tend, 1)
    if Wv != "3.0e-8":
        s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + Wv + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(PROBES) + "\n", s)
    assert out != s
    s = out
    vp = ("[VectorPostprocessors]\n"
          "  [line]\n"
          "    type = LineValueSampler\n"
          "    variable = 'c phi'\n"
          "    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n"
          "    num_points = %d\n"
          "    sort_by = x\n"
          "  []\n"
          "[]\n" % (xmax, lvs_n))
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    s = s.replace("__NOMATCH_keep_default_csv__",
                  "[Outputs]\n  [csv]\n    type = CSV\n    interval = 50\n  []\n[]", 1)
    return s


def parse_csv(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(",")
    return hdr, rows[-1].split(",")


def run_case(case):
    tag, xmax, nx, tend, Wv, A, lvs_n = case
    d = os.path.join(HERE, "var_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_var.i"), "w", encoding="utf-8").write(
        make_input(xmax, nx, tend, Wv, A, lvs_n))
    p0 = os.path.join(d, "p1c_var_out.csv")
    if os.path.exists(p0):
        os.remove(p0)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_var.i"], cwd=d, capture_output=True,
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
            res["err_line"] = l.strip()[:160]
            break
    if os.path.exists(p0):
        hdr, last = parse_csv(p0)
        for n in hdr:
            if n.startswith("c_p"):
                res[n] = float(last[hdr.index(n)])
    return tag, res


CASES = [
    ("W200_ref",    8.0e-6, 1600, 4.5e-5, "2.0e-7", "0.0", 200),
    ("W200_xmax5.6",  5.6e-6, 1120, 4.5e-5, "2.0e-7", "0.0", 200),
    ("W200_xmax16", 1.6e-5, 3200, 4.5e-5, "2.0e-7", "0.0", 200),
    ("W200_dx2.5",  8.0e-6, 3200, 4.5e-5, "2.0e-7", "0.0", 300),
    ("W200_dx10",   8.0e-6, 800, 4.5e-5, "2.0e-7", "0.0", 200),
    ("W20_ref",     8.0e-6, 4000, 4.5e-5, "2.0e-8", "0.0", 500),
    ("W20_A-1",     8.0e-6, 4000, 4.5e-5, "2.0e-8", "-1.0", 500),
    ("W60_ref",     8.0e-6, 4000, 4.5e-5, "6.0e-8", "0.0", 500),
]

if __name__ == "__main__":
    print("probes at x=2.5um (travel 2.3um) and 3.5um (travel 3.3um); c_inf = 0.036")
    print("tag            rc sec   jit zst steps | c@2.5um       dev          c@3.5um       dev")
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for tag, res in ex.map(run_case, CASES):
            if "c_p0" in res:
                print("%-14s %-2s %-5.0f %-3s %-3s %-5s | %.8f %+.3e  %.8f %+.3e" % (
                    tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                    res.get("zstep", "-"), res.get("steps", "-"),
                    res["c_p0"], res["c_p0"] - 0.036, res["c_p1"], res["c_p1"] - 0.036))
            else:
                print("%-14s %-2s %-5.0f %-3s %-3s %-5s | (no csv)" % (
                    tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                    res.get("zstep", "-"), res.get("steps", "-")))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])