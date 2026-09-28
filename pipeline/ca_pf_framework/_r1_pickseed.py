#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pickseed.py --- 为实验 7 挑一个**体积分数平衡**的随机初值种子

为什么：实验 7 的 S-2 判据是"各变体体积分数是否向**等分**靠拢"。
若初值本身就是 2/4，那 S-2 的基线就不对称、判据变弱。
⇒ **预先**（在看到任何演化结果之前）挑一个 `{V1,V2}` 各 3 个的种子，并把它写死。
  ⚠ 这是**判据前的选择**，不是"挑好看的结果"：只筛初值，不看任何演化量。
"""
import numpy as np

NVAR, NSEED = 2, 6
best = []
for s in range(200):
    rng = np.random.default_rng(s)
    seq = [int(rng.choice([1, 2])) for _ in range(NSEED)]
    c = [seq.count(1), seq.count(2)]
    if min(c) == 3:
        best.append((s, seq))
print('前 10 个给出 3/3 平衡的种子：')
for s, seq in best[:10]:
    print('   seed=%-4d  %s' % (s, seq))
# 也看 12 变体的情形（e7b）：只要不重复即可
print('\n12 变体臂（e7b）：')
for s in range(8):
    rng = np.random.default_rng(s)
    seq = [int(rng.choice(range(1, 13))) for _ in range(6)]
    print('   seed=%-4d  %s  唯一变体 %d 个' % (s, seq, len(set(seq))))
