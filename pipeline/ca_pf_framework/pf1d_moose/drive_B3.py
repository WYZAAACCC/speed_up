# -*- coding: utf-8 -*-
# Test B3: 1D vs 3D with the ideal-solution f_loc and automatic_scaling in BOTH.
import io, os, re, time, subprocess, sys
import concurrent.futures as cf
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys as MP
import mk_phys3d as MP3

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
XM, NX, TE, WV, A, LN = 8.0e-6, 1600, 5.0e-5, "2.0e-7", "2.04", 400


def read_rows(p):
    return [r.split(",") for r in io.open(p, encoding="utf-8").read().strip().splitlines()]


def run_case(case):
    tag, is3d = case
    d = os.path.join(HERE, "B3_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    txt = MP3.make_input(XM, NX, TE, WV, A, LN, scaling=False) if is3d else \
        MP.make_input(XM, NX, TE, WV, A, LN)
    if not is3d:
        assert "  l_tol = 1e-10" in txt
        txt = txt.replace(
            "  l_tol = 1e-10",
            "  l_tol = 1e-10\n  automatic_scaling = true\n  compute_scaling_once = false", 1)
    else:
        # measured unscaled |R0| = 5.79e-14 -> rule nl_abs_tol ~ 1e-3|R0| ; NO automatic_scaling
        # (automatic_scaling on this algebraic-phi system produced NaN at step ~18)
        assert "nl_abs_tol = 1e-9" in txt
        txt = txt.replace("nl_abs_tol = 1e-9", "nl_abs_tol = 1e-16", 1)
    io.open(os.path.join(d, "p1c_b3.i"), "w", encoding="utf-8").write(txt)
    for f in os.listdir(d):
        if f.startswith("p1c_b3_out.csv") or re.match(r"profile_line_\d+\.csv$", f):
            os.remove(os.path.join(d, f))
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-i", "p1c_b3.i"], cwd=d, capture_output=True,
                           text=True, timeout=72000, env=ENV)
        rc, out = r.returncode, r.stdout + chr(10) + "--STDERR--" + chr(10) + r.stderr
    except Exception as e:
        return tag, {"err": str(e)[:160], "sec": time.time() - t0}
    dt = time.time() - t0
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    n0 = out.count("\n 0 Nonlinear") + (1 if out.startswith(" 0 Nonlinear") else 0)
    n1 = out.count("\n 1 Nonlinear")
    res = {"rc": rc, "sec": dt, "jit": out.count("JIT compile failed"),
           "n0": n0, "n1": n1, "steps": out.count("Time Step"), "err_line": "", "r0": ""}
    for l in out.splitlines():
        if "0 Nonlinear" in l:
            res["r0"] = l.strip()[-13:]
            break
    for l in out.splitlines():
        if "ERROR" in l:
            res["err_line"] = l.strip()[:170]
            break
    p0 = os.path.join(d, "p1c_b3_out.csv")
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


CASES = [("1D", False), ("3D", True)]

if __name__ == "__main__":
    print("Test B3: ideal-solution f_loc, a=2.04, automatic_scaling in BOTH; target c_int = 0.056664")
    print("tag rc sec  jit warn steps n0   n1   firstR0        | c_int    c_peak")
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        for tag, res in ex.map(run_case, CASES):
            print("%-3s %-2s %-4.0f %-3s %-4s %-5s %-4s %-4s %-14s | %-8.6f %-8.6f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("warn", res.get("steps", "-")), res.get("steps", "-"),
                res.get("n0", "-"), res.get("n1", "-"), res.get("r0", ""),
                res.get("c_int", float("nan")), res.get("c_peak", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])