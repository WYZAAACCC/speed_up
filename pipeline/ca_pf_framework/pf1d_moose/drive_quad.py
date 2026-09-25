# -*- coding: utf-8 -*-
# Tests A and C: does the calibrated a transfer across (A) the free-energy form
# (ideal solution -> production quadratic) and (C) the front interpolation
# (h = 3phi^2-2phi^3 -> production's h_solid = min(1, 2 S))?
import io, os, re, time, subprocess, sys
import concurrent.futures as cf
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_quad as MQ

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"


def read_rows(p):
    return [r.split(",") for r in io.open(p, encoding="utf-8").read().strip().splitlines()]


def run_case(case):
    tag, xmax, nx, tend, Wv, aform, lvs_n, front = case
    d = os.path.join(HERE, "quad_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_q.i"), "w", encoding="utf-8").write(
        MQ.make_input(xmax, nx, tend, Wv, aform, lvs_n, front))
    for f in os.listdir(d):
        if f.startswith("p1c_q_out.csv") or re.match(r"profile_line_\d+\.csv$", f):
            os.remove(os.path.join(d, f))
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_q.i"], cwd=d, capture_output=True,
                           text=True, timeout=72000, env=ENV)
        rc, out = r.returncode, r.stdout + chr(10) + "--STDERR--" + chr(10) + r.stderr
    except Exception as e:
        return tag, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    res = {"rc": rc, "sec": dt, "jit": out.count("JIT compile failed"),
           "zstep": out.count("\n 0 Nonlinear"), "steps": out.count("Time Step"),
           "warn": out.count("Missing coupled variables"), "err_line": ""}
    for l in out.splitlines():
        if "ERROR" in l:
            res["err_line"] = l.strip()[:170]
            break
    p0 = os.path.join(d, "p1c_q_out.csv")
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
                    res["c_int"] = cs[i]
                    break
            res["c_peak"] = max(cs)
    return tag, res


CASES = [
    ("A_a1.50", 1.2e-5, 2400, 1.0e-4, "2.0e-7", "1.50", 400, "smooth"),
    ("A_a2.04", 1.2e-5, 2400, 1.0e-4, "2.0e-7", "2.04", 400, "smooth"),
    ("A_a3.00", 1.2e-5, 2400, 1.0e-4, "2.0e-7", "3.00", 400, "smooth"),
    ("C_a2.04", 1.2e-5, 2400, 1.0e-4, "2.0e-7", "2.04", 400, "prod"),
    ("C_a3.00", 1.2e-5, 2400, 1.0e-4, "2.0e-7", "3.00", 400, "prod"),
]

if __name__ == "__main__":
    print("target: c_l at the SL front should equal c_inf/k = 0.036/(k_c/(k_c+2A)) = 0.057117")
    print("tag      rc sec  jit zst warn steps | c_int    c_peak   c_s4      c_s6      c_s8")
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for tag, res in ex.map(run_case, CASES):
            print("%-8s %-2s %-4.0f %-3s %-3s %-4s %-5s | %-8.6f %-8.6f %-9.6f %-9.6f %-9.6f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("warn", "-"), res.get("steps", "-"),
                res.get("c_int", float("nan")), res.get("c_peak", float("nan")),
                res.get("c_p0", float("nan")), res.get("c_p1", float("nan")),
                res.get("c_p2", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])