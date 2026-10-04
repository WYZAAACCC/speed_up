#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_burstcnt.py --- 每档核数分布（burst 修复的核心判据）"""
import collections
import os
import re

for tag, lab in (('t5BK1', 'KM 分数律（新，--burst-km 1）'),
                 ('t5N276F', '线性律（旧，对照）')):
    P = '_w2_t5_short_%s.log' % tag
    if not os.path.exists(P):
        print('  %s （无日志）' % lab)
        continue
    s = open(P, errors='ignore').read()
    Ts = re.findall(r'T=([0-9.]+) K', s)
    c = collections.Counter(Ts)
    print('  ── %s：事件总数 %d ──' % (lab, sum(c.values())))
    for T, n in sorted(c.items(), key=lambda kv: -float(kv[0]))[:12]:
        print('     T = %8s K ： **%3d 个**' % (T, n))
    print()

print('  ── 理论预期（KM 分数律：N_end = 23 每块、B = 3 ⇒ 全盒）──')
print('     第 1 档（T=849.0 K）：**~44 个**（63.2%）')
print('     第 2 档（T=825.0 K）：**~16 个**（23.3%）')
print('     第 3 档（T=801.1 K）：**~6 个**（8.6%）')
print('     第 4 档（T=777.1 K）：**~2 个**（3.1%）')
print('  ── 线性律（旧）预期：**每档恒定 1 个** ──')
