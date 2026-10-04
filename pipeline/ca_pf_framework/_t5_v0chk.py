#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_v0chk.py --- 用物理恒等式判 CSV 两列的刻度谁对：V0 + Vt 应 = L³。

`V0 = mm['vol_0']`（母相 β），`Vt = Σ_{k≥1} vol_k`（马氏体）。
两者由**同一个** `mm` 算出 ⇒ **刻度必须相同**。
若 CSV 里 `V0 + Vt ≠ L³`，就是其中一列的刻度错。
"""
import csv
import os
import subprocess
import sys

BASE = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_%s/series.csv"


def rows_of(p):
    n = int(subprocess.check_output(["wc", "-l", p]).split()[0])
    rr = []
    for _ in range(8):
        with open(p, "r", newline="", encoding="utf-8", errors="replace") as fh:
            r = list(csv.DictReader(fh))
        if len(r) >= len(rr):
            rr = r
        if len(rr) >= n - 1:
            break
    return rr, n


def main():
    for tag in (sys.argv[1:] or ["t5N276F"]):
        p = BASE % tag
        if not os.path.exists(p):
            print("%s 无 CSV" % tag)
            continue
        rs, n = rows_of(p)
        print("══ %s ══ 行=%d (wc -l=%d)" % (tag, len(rs), n))
        for r in rs[-3:]:
            V0 = float(r.get("V0") or 0)
            Vt = float(r.get("Vt") or 0)
            vv = [float(x) for x in (r.get("vols") or "").split("/") if x.strip()]
            sv = sum(v for v in vv if v > 0)
            print("  step=%-6s V0=%-14.6g Vt=%-14.6g  Σvols=%-12.6g  V0+Vt=%-14.6g"
                  % (r.get("step"), V0, Vt, sv, V0 + Vt))
            print("          诊断：若 (V0+Vt) 应 = 125 µm³ ⇒ 现在 = %.4g ⇒ 比值 %.4g"
                  % (V0 + Vt, (V0 + Vt) / 125.0))
            print("          Σvols / Vt = %.6g （若 = 1 则两列刻度一致）" % (sv / Vt if Vt else float("nan")))
        # 常数 L
        print("  %s" % {k: rs[-1].get(k) for k in ("V0", "Vt")})


if __name__ == "__main__":
    main()
