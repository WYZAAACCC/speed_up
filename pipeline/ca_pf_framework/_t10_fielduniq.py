#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_fielduniq.py --- 形核事件的**场号唯一性**（判"一场多核"是不是真因）。

依据：N=80 时曾实测「29 个事件 → 28 个不同场（场 95 用过两次）」⇒ **引擎确实会复用场号**。
若本次 45 个事件里出现重复场号 ⇒ 「一个场里多个板条」= **一场被写了两个核**（真因）；
若 45 个场号全不同 ⇒ 卫星另有来源。
"""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
L = os.path.join(HERE, "_w2_t5_short_t10N160.log")

with open(L, "r", encoding="utf-8", errors="replace") as fh:
    txt = fh.read()

ev = re.findall(r"athermal 形核\*?\*? @ step (\d+)：T=([\d.]+) K.{0,80}?场 (\d+)", txt)
print("解析出形核事件 = %d 条" % len(ev))
if not ev:
    # 退一步：只抓「，场 N（累计」
    ev2 = re.findall(r"，场 (\d+)（累计", txt)
    print("  退一步只抓到场号 = %d 个" % len(ev2))
    fields = [int(x) for x in ev2]
    steps = []
    Ts = []
else:
    fields = [int(e[2]) for e in ev]
    steps = [int(e[0]) for e in ev]
    Ts = [float(e[1]) for e in ev]

print("  步分布:", sorted(set(steps))[:6], "…" if len(set(steps)) > 6 else "")
print("  T 分布:", sorted(set(Ts))[:6])
print()
from collections import Counter
c = Counter(fields)
dup = {k: v for k, v in c.items() if v > 1}
print("事件数 = %d ；**不同场号 = %d** ；唯一性 = %.3f"
      % (len(fields), len(c), len(c) / max(len(fields), 1)))
print("排除场 0（母相）后：", len([f for f in fields if f != 0]),
      "个事件，", len(set(f for f in fields if f != 0)), "个不同场")
if dup:
    print("★ **重复场号**（场: 次数）:", dict(sorted(dup.items())))
    print("  ⇒ 这些场被写了多个核 ⇒ **「一个场里多个板条」= 一场多核（真因）**")
else:
    print("⇒ **45 个场号全不同** ⇒ 卫星**不是**一场多核 ⇒ 另有来源")
print()
print("场号列表:", sorted(set(fields)))
