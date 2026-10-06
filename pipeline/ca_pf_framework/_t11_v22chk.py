#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_v22chk.py —— 核实**正在跑的算例**用的确实是 v2.2 的配置（1000 步/每 100 步快照）。"""
import os

OUT = "/mnt/f/speed_up/_w2_v22chk.txt"
L = []
# ① 主控日志头
for f in ("/mnt/f/speed_up/_w2_cube2c.log",):
    if os.path.exists(f):
        L.append("=== %s ===" % os.path.basename(f))
        with open(f, encoding="utf-8", errors="replace") as fh:
            for i, ln in enumerate(fh):
                if i >= 3:
                    break
                L.append("  " + ln.rstrip())
# ② 实际进程命令行
L.append("")
L.append("=== 正在跑的 _bk_exp.py 命令行 ===")
found = False
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        raw = open("/proc/%s/cmdline" % pid, "rb").read()
    except OSError:
        continue
    argv = [x.decode("utf-8", "replace") for x in raw.split(b"\0") if x]
    if any("_bk_exp.py" in a for a in argv):
        found = True
        L.append("  PID %s:" % pid)
        for i in range(0, len(argv), 6):
            L.append("    " + " ".join(argv[i:i + 6]))
if not found:
    L.append("  （没有正在跑的 _bk_exp.py）")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
