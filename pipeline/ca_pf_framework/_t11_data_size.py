#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_data_size.py —— 量本次会话产物的体积，决定哪些该入库。

## 背景
用户要求「将当前的代码 git 到本地」。仓库没有针对 `_exp/` 的忽略规则，
而整个 `_exp/_bk_t5` 是 **19.8 GB / 2252 文件** ⇒ **不可能全提交**。
⇒ 分开量：**本次会话的臂**（体积小，值得入库作可复现凭据）vs **历史臂**（大，不入库）。
"""
import os

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
# 本次会话（2026-10-07）建的臂
MINE = ['B10', 'B40', 'B60', 'L0', 'L1', 'L2', 'M0', 'M1', 'M2',
        'c2Eq0', 'c2B647', 'c2B15', 'c2PosA',
        'fW0', 'fW1', 'fDip4', 'fEll', 'fSh1', 'fSh2', 'fB10', 'gW0', 'gW1', 'gW1b',
        'kP1', 'kP3', 'kW0', 'kW1', 'fDbg']

print("=" * 92)
print("本次会话臂的体积（%d 个）" % len(MINE))
print("=" * 92)
tot_all = 0
tot_csv = 0
rows = []
for t in MINE:
    d = os.path.join(ROOT, "dry_%s" % t)
    if not os.path.isdir(d):
        continue
    n = 0
    sz = 0
    csvsz = 0
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        s = os.path.getsize(p)
        if f.endswith('.npz'):
            n += 1
            sz += s
        elif f.endswith(('.csv', '.json')):
            csvsz += s
    if n or csvsz:
        rows.append((t, n, sz, csvsz))
        tot_all += sz
        tot_csv += csvsz
for t, n, sz, csvsz in sorted(rows, key=lambda r: -r[2]):
    print("  dry_%-10s 快照 %-4d  %8.1f MB   小文件(csv/json) %7.2f MB"
          % (t, n, sz / 1e6, csvsz / 1e6))
print()
print("  ⇒ **快照合计 %.1f MB**；**csv/json 合计 %.2f MB**" % (tot_all / 1e6, tot_csv / 1e6))
print()
# 全目录
g = 0
gn = 0
for r, _d, fs in os.walk(ROOT):
    for f in fs:
        try:
            g += os.path.getsize(os.path.join(r, f))
            gn += 1
        except OSError:
            pass
print("  （参照）整个 `_exp/_bk_t5` = **%.1f MB / %d 文件**" % (g / 1e6, gn))
print("  ⇒ 历史臂占 **%.1f MB** —— 那部分不入库。" % ((g - tot_all) / 1e6))
