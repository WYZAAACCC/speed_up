# -*- coding: utf-8 -*-
# Round 1: calibrate the physically-correct antitrapping coefficient a (W = 200 nm).
import io, os, re, time, subprocess, sys
import concurrent.futures as cf
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys as MK

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"


def read_rows(p):
    return [r.split(",") for r in io.open(p, encoding="utf-8").read().strip().splitlines()]


def run_case(case):
    tag, xmax, nx, tend, Wv, aform, lvs_n = case
    d = os.path.join(HERE, "phys_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p1c_phys.i"), "w", encoding="utf-8").write(
        MK.make_input(xmax, nx, tend, Wv, aform, lvs_n))
    for f in os.listdir(d):
        if f.startswith("p1c_phys_out.csv") or re.match(r"profile_line_\d+\.csv$", f):
            os.remove(os.path.join(d, f))
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_phys.i"], cwd=d, capture_output=True,
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
    p0 = os.path.join(d, "p1c_phys_out.csv")
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
    ("W200_a_lit", 1.2e-5, 2400, 1.0e-4, "2.0e-7", MK.A_LIT, 400),
    ("W200_a1.0",  1.2e-5, 2400, 1.0e-4, "2.0e-7", "1.0", 400),
    ("W200_a2.0",  1.2e-5, 2400, 1.0e-4, "2.0e-7", "2.0", 400),
    ("W200_a3.0",  1.2e-5, 2400, 1.0e-4, "2.0e-7", "3.0", 400),
    ("W200_aphi",  1.2e-5, 2400, 1.0e-4, "2.0e-7", "aphiform", 400),
]

if __name__ == "__main__":
    print("target c_int = 0.056664 ; F = a W [c_l(mu) - c_s(mu)] ; lit a = 1/(2 sqrt2) = 0.35355")
    print("tag          rc sec  jit zst warn steps | c_int    c_peak   c_s4      c_s6      c_s8")
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for tag, res in ex.map(run_case, CASES):
            print("%-12s %-2s %-4.0f %-3s %-3s %-4s %-5s | %-8.6f %-8.6f %-9.6f %-9.6f %-9.6f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("warn", "-"), res.get("steps", "-"),
                res.get("c_int", float("nan")), res.get("c_peak", float("nan")),
                res.get("c_p0", float("nan")), res.get("c_p1", float("nan")),
                res.get("c_p2", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])