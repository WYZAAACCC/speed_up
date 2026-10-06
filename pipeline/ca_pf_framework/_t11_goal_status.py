#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_goal_status.py —— goal 每轮的**状态板**（一次输出：洁净性 + 进度 + 内存）。"""
import glob
import os
import re
import subprocess
import time

ROOT = "/mnt/f/speed_up"
CF = os.path.join(ROOT, "pipeline/ca_pf_framework")
MAIN = ["_bk_exp.py", "windowB_surface.py", "windowB_pf3d.py", "windowB_km.py",
        "windowB_lath.py", "windowB_closure.py", "_bk_measure.py",
        "windowB_aniso_elastic.py", "windowB_ti64_variants.py"]
L = []
L.append("#### %s" % time.strftime('%F %T'))
# ① 主代码洁净性（R629 E1）
p = subprocess.run(["git", "status", "--porcelain", "--"] +
                   [os.path.join("pipeline/ca_pf_framework", m) for m in MAIN],
                   cwd=ROOT, capture_output=True, text=True)
dirty = [x for x in p.stdout.splitlines() if x.strip()]
L.append("① 主代码洁净性（R629 E1）：%s"
         % ("✅ 未被改动（git status 为空）" if not dirty
            else "❌ **被改动**：%s" % dirty))
p2 = subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=format:%m-%d %H:%M",
                     "--", "pipeline/ca_pf_framework/_bk_exp.py"],
                    cwd=ROOT, capture_output=True, text=True)
L.append("   `_bk_exp.py` 最后提交 = %s" % p2.stdout.strip())
# ② 各臂日志进度
L.append("② 各臂进度：")
for t in ("c2Eq0", "c2B647", "c2B15"):
    f = os.path.join(ROOT, "_w2_%s.log" % t)
    if not os.path.exists(f):
        L.append("   %-8s (未创建)" % t)
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    steps = [int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]', txt, re.M)]
    mt = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))
    L.append("   %-8s %5d 行  最新 step=%-5s mtime=%s"
             % (t, txt.count("\n"), steps[-1] if steps else "—", mt))
# ③ 主控日志（已完成臂的结果表）
f = os.path.join(ROOT, "_w2_cube2b.log")
if os.path.exists(f):
    txt = open(f, encoding="utf-8", errors="replace").read()
    L.append("③ 主控 `_w2_cube2b.log`（%d 行，mtime=%s）："
             % (txt.count("\n"),
                time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))))
    for ln in txt.splitlines()[-14:]:
        L.append("   " + ln[:150])
    if "beta_h" not in txt:
        L.append("   （尚无臂完成）")
else:
    L.append("③ 主控日志尚未创建")
# ④ 内存
L.append("④ 内存：")
L.append("   " + subprocess.run(["bash", "-c", "free -m | sed -n 2,3p"],
                                capture_output=True, text=True).stdout.strip()
         .replace("\n", " | "))
open(os.path.join(ROOT, "_w2_goal_status.txt"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
