# -*- coding: utf-8 -*-
# Experiment K: same as drive_ak3 but W = 60 nm (V W/D_L = 0.632), ALPHA in {8,12,16}.
# Purpose: make ALPHA*(W) a 3-point law (200 / 60 / 20 nm) to test universality.
import io, os, re, time, subprocess
import concurrent.futures as cf
import drive_ak3 as D

CASES = [("W60_A%.2f" % A, 1.2e-5, 4000, 1.0e-4, "6.0e-8", "%.2f" % A, 800)
         for A in (8.0, 12.0, 16.0)]

if __name__ == "__main__":
    print("W=60nm (VW/D_L=0.632); target c_int = 0.056664")
    print("tag        rc sec   jit zst steps | x_int    c_int    c_peak   c_s4       c_s6       c_s8")
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for tag, res in ex.map(D.run_case, CASES):
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