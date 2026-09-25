# -*- coding: utf-8 -*-
# Experiment H: does ALPHA change the INTERFACE partition k_eff = c_s(deep)/c_int ?
# The deposited solid composition (dev) is insensitive to ALPHA (drive_long/var), so the
# right calibratable observable is the interface partition / liquid-side amplitude.
# Setup: W = 200 nm, V W / D_L = 2.1, travel 4.3 um, xmax 8 um, dx 5 nm.
import io, os, re, time, subprocess
import concurrent.futures as cf

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "p1c_alpha2.i")
PROBES = [2.5e-6, 3.5e-6]
XMAX, NX, TEND, WV = 8.0e-6, 1600, 4.5e-5, "2.0e-7"


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(A):
    s = io.open(BASE, encoding="utf-8").read()
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % XMAX, 1)
    s = s.replace("nx = 1200", "nx = %d" % NX, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % TEND, 1)
    s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + WV, 1)
    s = s.replace('constant_expressions = "-1.0 3.0e-8 0.6303"',
                  'constant_expressions = "' + A + " " + WV + ' 0.6303"', 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(PROBES) + "\n", s)
    assert out != s
    s = out
    vp = ("[VectorPostprocessors]\n  [line]\n    type = LineValueSampler\n"
          "    variable = 'c phi'\n    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n    num_points = 200\n    sort_by = x\n  []\n[]\n"
          % XMAX)
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


def run_case(A):
    tag = "A%+.2f" % float(A)
    d = os.path.join(HERE, "ak_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_ak.i"), "w", encoding="utf-8").write(make_input(A))
    p0 = os.path.join(d, "p1c_ak_out.csv")
    if os.path.exists(p0):
        os.remove(p0)
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_ak.i"], cwd=d, capture_output=True,
                           text=True, timeout=21600, env=ENV)
        rc, out = r.returncode, r.stdout + chr(10) + "--STDERR--" + chr(10) + r.stderr
    except Exception as e:
        return tag, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    res = {"rc": rc, "sec": dt, "jit": out.count("JIT compile failed"),
           "zstep": out.count("\n 0 Nonlinear"), "steps": out.count("Time Step"), "err_line": ""}
    for l in out.splitlines():
        if "*** ERROR" in l or "ERROR" in l:
            res["err_line"] = l.strip()[:170]
            break
    if os.path.exists(p0):
        rows = read_rows(p0)
        hdr = rows[0]
        last = rows[-1]
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
            xint = None
            for i in range(len(xs) - 1):
                if (ps[i] - 0.5) * (ps[i + 1] - 0.5) <= 0:
                    xint = xs[i]
                    break
            if xint is not None:
                res["xint"] = xint
                res["c_int"] = cs[xs.index(xint)]
                # liquid peak
                res["c_peak"] = max(cs)
            res["c_deep"] = float(rows[-1][ix["c"]])
    return tag, res


CASES = ["+4.00", "+2.00", "+1.00", "0.00", "-1.00", "-2.00", "-3.00"]

if __name__ == "__main__":
    print("W=200nm, VW/D_L=2.1, k_e(1911K)=0.6356, c_inf=0.036, interlace at x=4.7um")
    print("ALPHA   rc sec  jit zst | x_int      c_int      c_peak     c_deep     k_eff=c_deep/c_int")
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        for tag, res in ex.map(run_case, CASES):
            ci = res.get("c_int")
            cd = res.get("c_deep")
            ke = (cd / ci) if (ci and cd) else float("nan")
            print("%-6s  %-2s %-4.0f %-3s %-3s | %-10.4g %-10.6f %-10.6f %-10.6f %.4f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("xint", float("nan")), ci or float("nan"),
                res.get("c_peak", float("nan")), cd or float("nan"), ke))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])