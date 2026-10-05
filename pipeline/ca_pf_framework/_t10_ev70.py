#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_ev70.py --- 分辨「70 个形核事件 vs 38 个有带内胞的场」。

三种可能：
 (a) 70 个核里有**重复场号**（同一场被播多次）⇒ 调度问题；
 (b) 70 个场号互不相同、但只有 38 个长出带内胞 ⇒ 32 个核未发育（被抑制/溶解）；
 (c) 我的量具阈值滤掉了小场。
本脚本给出 (a)/(b) 的判别，并把每个事件的步号/温度/模式列出来。
"""
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
L = os.path.join(HERE, "_w2_t5_short_t10CL2.log")
with open(L, "r", encoding="utf-8", errors="replace") as fh:
    txt = fh.read()

# 形核事件行：抓 步号 / 温度 / 场号 / 累计 / 模式
pat = re.compile(r"athermal 形核\*{0,2} @ step (\d+)：T=([\d.]+) K.{0,200}?"
                 r"场 (\d+)（累计 [\d/]+[^）]*）", re.S)
ev = pat.findall(txt)
if not ev:
    ev2 = re.findall(r"@ step (\d+)：T=([\d.]+) K", txt)
    print("⚠ 主正则未匹配；退一步只抓到 %d 个 (step,T)" % len(ev2))
    fields = [int(x) for x in re.findall(r"，场 (\d+)（累计", txt)]
    steps = [int(a) for a, _b in ev2]
    Ts = [float(b) for _a, b in ev2]
else:
    steps = [int(a) for a, _b, _c in ev]
    Ts = [float(b) for _a, b, _c in ev]
    fields = [int(c) for _a, _b, c in ev]

print("解析出形核事件 = %d" % len(fields))
print("  步分布 =", sorted(set(steps)))
print("  T 分布 =", sorted(set(Ts)))

# 模式（attach/stack/fresh）
modes = re.findall(r"模式 \*\*(\w+)\*\*", txt)
print("  模式分布 =", dict(Counter(modes)))

c = Counter(fields)
dup = {k: v for k, v in c.items() if v > 1}
print()
print("  事件数 = %d ；不同场号 = %d ；唯一性 = %.3f"
      % (len(fields), len(c), len(c) / max(len(fields), 1)))
if dup:
    print("  ★ **重复场号**（场: 次数）= %s" % dict(sorted(dup.items())))
    print("     ⇒ (a) 成立：存在同一场被播多次（注意：占用守卫只加在 fresh 通道，")
    print("        stack/attach 是否也遵守守卫，需另查）")
else:
    print("  ⇒ **70 个场号互不相同** ⇒ (a) 否证 ⇒ 数量差来自 (b) 未发育 或 (c) 阈值")

print()
print("  场号全表 =", sorted(c))

# 与有带内胞的场对比
try:
    import numpy as np
    sn = os.path.join(HERE, "_exp/_bk_t5/dry_t10CL2/snap_00200.npz")
    with np.load(sn, allow_pickle=False) as z:
        N = int(np.asarray(z["N"]))
        bv = np.asarray(z["band_val"]).ravel()
        bf = np.asarray(z["band_fld"]).ravel()
    have = set()
    for k in np.unique(bf[bv < 0]):
        if int(k) == 0:
            continue
        if int(((bf == k) & (bv < 0)).sum()) >= 30:
            have.add(int(k))
    print()
    print("  step200 有带内胞(>=30)的场 = %d 个" % len(have))
    miss = sorted(set(c) - have)
    print("  ★ 形核过但 step200 查无此场（或 <30 胞）的 = %d 个：" % len(miss))
    print("     ", miss)
    extra = sorted(have - set(c))
    print("  有场但无对应形核事件的 = %d 个：%s" % (len(extra), extra))
except Exception as e:
    print("  ⚠ 快照对比失败：%s" % e)
