# -*- coding: utf-8 -*-
# Experiment J: LONG-TRAVEL ALPHA scan against the correct observable c_int.
# Targets: c_int = c_inf / k_e(T) = 0.056664 (k_e = 0.63532 at T = 1911.1 K).
# Setup: travel 9.8 um (W=200) / 9.5 um (W=20), xmax 12 um, probes at x = 4/6/8 um
#        (deposited at travel 3.8/5.8/7.8 um) to judge whether the run has settled.
# Profile is written ONLY at FINAL ( outputs = lineonly + execute_on = FINAL ) -> 1 file.
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")
PROBES = [4.0e-6, 6.0e-6, 8.0e-6]


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
    s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + Wv + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(PROBES) + "\n", s)
    assert out != s
    s = out
    vp = ("[VectorPostprocessors]\n  [line]\n    type = LineValueSampler\n"
          "    variable = 'c phi'\n    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n    num_points = %d\n    sort_by = x\n"
          "    outputs = lineonly\n  []\n[]\n" % (xmax, lvs_n))
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    s = s.replace("[Outputs]\n  csv = true\n[]",
                  "[Outputs]\n  csv = true\n  [lineonly]\n    type = CSV\n"
                  "    execute_on = FINAL\n    file_base = profile\n  []\n[]", 1)
    return s


def read_rows(path):
    rows = io.open(path, encoding="utf-8").read().strip().splitlines()
    return [r.split(",") for r in rows]


def run_case(case):
    tag, xmax, nx, tend, Wv, A, lvs_n = case
    d = os.path.join(HERE, "ak3_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_ak3.i"), "w", encoding="utf-8").write(
        make_input(xmax, nx, tend, Wv, A, lvs_n))
    for f in ("p1c_ak3_out.csv", "profile_line_0000.csv"):
        p = os.path.join(d, f)
        if os.path.exists(p):
            os.remove(p)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_ak3.i"], cwd=d, capture_output=True,
                           text=True, timeout=72000, env=ENV)
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
    p0 = os.path.join(d, "p1c_ak3_out.csv")
    if os.path.exists(p0):
        rows = read_rows(p0)
        hdr, last = rows[0], rows[-1]
        for n in hdr:
            if n.startswith("c_p"):
                res[n] = float(last[hdr.index(n)])
    fs = [f for f in os.listdir(d) if re.match(r"profile_line_\d+\.csv$", f)]
    if fs:
        f = max(fs, key=lambda f: int(re.search(r"_(\d+)\.csv$", f).group(1)))
        rows = read_rows(os.path.join(d, f))
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
    return tag, res


def cases():
    out = []
    for A in (4.0, 6.0, 8.0, 10.0):
        out.append(("W200_A%.2f" % A, 1.2e-5, 2400, 1.0e-4, "2.0e-7", "%.2f" % A, 400))
    for A in (8.0, 16.0, 24.0, 32.0):
        out.append(("W20_A%.2f" % A, 1.2e-5, 6000, 9.5e-5, "2.0e-8", "%.2f" % A, 2400))
    return out


if __name__ == "__main__":
    print("target c_int = 0.056664 ; probes at x=4/6/8 um = deposited at travel 3.8/5.8/7.8 um")
    print("tag        rc sec   jit zst steps | x_int    c_int    c_peak   c_s4       c_s6       c_s8")
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for tag, res in ex.map(run_case, cases()):
            print("%-10s %-2s %-5.0f %-3s %-3s %-5s | %-8.4g %-8.6f %-8.6f %-9.6f %-9.6f %-9.6f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("steps", "-"), res.get("xint", float("nan")),
                res.get("c_int", float("nan")), res.get("c_peak", float("nan")),
                res.get("c_p0", float("nan")), res.get("c_p1", float("nan")),
                res.get("c_p2", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])