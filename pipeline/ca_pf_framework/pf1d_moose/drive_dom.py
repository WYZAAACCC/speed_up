# -*- coding: utf-8 -*-
# Domain-length / run-length separation experiment  (P11_SPEC 18.3)
# Hypothesis: the W-independent -2e-4 bias at ALPHA=0 is
#   (i)  far-field Dirichlet truncation   ~ ((1-k)/k) * exp(-N_BC)
#   (ii) boundary-layer build-up transient ~ exp(-N_tr)
# with N = distance/l_D, l_D = D_L/V = 95 nm (V = 0.1 m/s, D_L = 9.5e-9).
# Baseline case: interface 0.2 -> 1.6 um, xmax 2.4 um =>
#   N_BC = 800/95 = 8.42 ; N_tr at the 1.00 um probe = 800/95 = 8.42.
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i,
              "    type = PointValue",
              "    variable = c",
              "    point = \"%.6e 0 0\"" % x,
              "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(xmax, nx, tend, Wv, A, probes, lvs_n=400):
    s = io.open(BASE, encoding="utf-8").read()
    assert "xmax = 2.4e-6" in s
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % xmax, 1)
    s = s.replace("nx = 1200", "nx = %d" % nx, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % tend, 1)
    if Wv != "3.0e-8":
        s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + Wv + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(probes) + "\n", s)
    assert out != s, "Postprocessors block not replaced"
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
    assert "[Executioner]" in s
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    return s


def parse_csv(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(",")
    return hdr, rows[-1].split(",")


def run_case(case):
    name, xmax, nx, tend, Wv, A, probes = case
    d = os.path.join(HERE, "dom_" + name)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_dom.i"), "w", encoding="utf-8").write(
        make_input(xmax, nx, tend, Wv, A, probes))
    p0 = os.path.join(d, "p1c_dom_out.csv")
    if os.path.exists(p0):
        os.remove(p0)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_dom.i"], cwd=d, capture_output=True,
                           text=True, timeout=10800, env=ENV)
        rc, out = r.returncode, r.stdout
    except Exception as e:
        return name, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    nz = out.count("\n 0 Nonlinear") + (1 if out.startswith(" 0 Nonlinear") else 0)
    res = {"rc": rc, "sec": dt,
           "jit_fail": out.count("JIT compile failed"),
           "zerostep": nz,
           "steps": out.count("Time Step"),
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
    return name, res


CASES = [
    ("A_base",     2.4e-6, 1200, 1.4e-5, "2.0e-7", "0.0", [1.0e-6]),
    ("B_longdom",  4.8e-6, 2400, 1.4e-5, "2.0e-7", "0.0", [1.0e-6, 1.3e-6]),
    ("C_longboth", 4.8e-6, 2400, 3.0e-5, "2.0e-7", "0.0", [2.0e-6, 2.6e-6]),
]

if __name__ == "__main__":
    print("case        rc  sec     jit  zstep  steps | probes")
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for name, res in ex.map(run_case, CASES):
            keys = sorted([k for k in res if k.startswith("c_p")],
                          key=lambda k: int(k[3:]))
            pv = "  ".join("%s=%.8f dev=%+.3e" % (k, res[k], res[k] - 0.036) for k in keys)
            print("%-11s %-3s %-7.1f %-4s %-6s %-6s | %s" % (
                name, res.get("rc", "-"), res.get("sec", 0), res.get("jit_fail", "-"),
                res.get("zerostep", "-"), res.get("steps", "-"), pv))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])