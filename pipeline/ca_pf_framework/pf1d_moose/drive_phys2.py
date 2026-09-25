# -*- coding: utf-8 -*-
# Round 2: is the calibrated a universal across W with the CORRECT F shape?
import io, os, sys
import concurrent.futures as cf
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import drive_phys as DP
import mk_phys as MK

CASES = [
    ("W60_a2.0", 1.2e-5, 4000, 1.0e-4, "6.0e-8", "2.0", 800),
    ("W60_a3.0", 1.2e-5, 4000, 1.0e-4, "6.0e-8", "3.0", 800),
    ("W60_a4.0", 1.2e-5, 4000, 1.0e-4, "6.0e-8", "4.0", 800),
    ("W20_a2.0", 1.2e-5, 6000, 9.5e-5, "2.0e-8", "2.0", 2400),
    ("W20_a4.0", 1.2e-5, 6000, 9.5e-5, "2.0e-8", "4.0", 2400),
    ("W20_a6.0", 1.2e-5, 6000, 9.5e-5, "2.0e-8", "6.0", 2400),
    ("W20_a8.0", 1.2e-5, 6000, 9.5e-5, "2.0e-8", "8.0", 2400),
]

if __name__ == "__main__":
    print("target c_int = 0.056664 ; F = a W [c_l(mu)-c_s(mu)] ; W=200 gave a* ~ 2.04")
    print("tag        rc sec  jit zst warn steps | c_int    c_peak   c_s4      c_s6      c_s8")
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        for tag, res in ex.map(DP.run_case, CASES):
            print("%-10s %-2s %-4.0f %-3s %-3s %-4s %-5s | %-8.6f %-8.6f %-9.6f %-9.6f %-9.6f" % (
                tag, res.get("rc", "-"), res.get("sec", 0), res.get("jit", "-"),
                res.get("zstep", "-"), res.get("warn", "-"), res.get("steps", "-"),
                res.get("c_int", float("nan")), res.get("c_peak", float("nan")),
                res.get("c_p0", float("nan")), res.get("c_p1", float("nan")),
                res.get("c_p2", float("nan"))))
            if res.get("err_line"):
                print("     ERR: " + res["err_line"])
            if res.get("err"):
                print("     EXC: " + res["err"])