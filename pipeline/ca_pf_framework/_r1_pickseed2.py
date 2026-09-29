#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pickseed2.py --- 为实验 7 的**负对照臂 e7c**（packet-3 的 {V5,V6}）挑平衡种子"""
import numpy as np

VAR = [5, 6]
NSEED = 6
print('为 {V5,V6} 找 3/3 平衡的随机种子：')
ok = []
for s in range(200):
    rng = np.random.default_rng(s)
    seq = [int(rng.choice(VAR)) for _ in range(NSEED)]
    c = [seq.count(v) for v in VAR]
    if min(c) == 3:
        ok.append((s, seq))
for s, seq in ok[:10]:
    print('   seed=%-4d %s' % (s, seq))
print('\n选中：seed=%d → %s' % (ok[0][0], ok[0][1]) if ok else '（没有 3/3 的）')
