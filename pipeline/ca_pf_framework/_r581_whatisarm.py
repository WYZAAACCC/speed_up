#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_whatisarm.py --- 用**仓库里的实数**说清"臂"是什么"""
import glob
import json
import os
import re

print('=' * 100)
print('"臂"（arm）= **一条独立跑起来的仿真算例**。它的物理与数字形态如下：')
print('=' * 100)
ds = [d for d in glob.glob('_exp/**/dry_*', recursive=True) if os.path.isdir(d)]
print('  全库共 **%d 条臂**（每个 `dry_*` 目录 = 一条）' % len(ds))
print()
print('  ── 一条臂的完整"身份"（以 `BK6` 为例）──')
d = '_exp/_bk_blk/dry_BK6'
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    print('    %-20s %9d 字节' % (f, os.path.getsize(p)))
print()
print('  ── 判别一条臂靠什么（三样）──')
print('    ① `--tag <名字>`（命令行里）⇒ 决定目录名 `dry_<tag>/` 与日志名')
print('    ② `_exp/<根>/dry_<tag>/meta.json` ⇒ 存**配置指纹**（N/dx/物理参数…）')
print('    ③ `series.csv` ⇒ 逐步落盘的**观测量**（`--every N` 一行）')
print()
print('  ── ★ 为什么叫"臂"：**一次对照里的一个分支****')
print('    对照实验的标准结构：**只差一个变量**，其余逐字相同 ⇒')
print('    每条分支各起一条臂，跑完比 `series.csv` 的共有列 ⇒ 差异就归因到那个变量。')
print()
EX = [
    ('C6 判决', ['BK6', 'BK7'], '`--stack-pick-dg` 0 vs 1'),
    ('A4 判决', ['TUNED', 'ARENA', 'PLAIN'], '三个 MALLOC 环境变量档'),
    ('N=160 形核档', ['p2_b3', 'p2_b5', 'p2_b5ov', 'p2_b5ps'], '`--nuc-block-target` 四档'),
    ('C6 负对照', ['BN1'], '单变体（16 根板条、2 个块）'),
    ('C2 归因', ['BG1', 'BG2'], '两种种子尺寸'),
]
print('  %-14s %-38s %s' % ('用途', '臂（tag）', '它们的区别（唯一变量）'))
print('  ' + '-' * 96)
for use, tags, diff in EX:
    print('  %-14s %-38s %s' % (use, ' · '.join(tags), diff))
print()
print('  ── 一条臂在跑的时候是什么（Linux 进程 + 绑核）──')
print('    一个 python 进程（`_bk_exp.py --tag <名字>`），用 `taskset -c 0-7` 之类绑到**互不相交**的核，')
print('    写自己的 `series.csv` / `snap_*.npz` / 日志 ⇒ **互不干扰、可单独杀、可单独续**。')
print()
print('  ── ⚠ 两个容易混的说法 ──')
print('    · **"同一条臂"的多次重跑**：我会把旧的 `mv` 成 `dry_<tag>_superseded_<时间戳>/`（**绝不删**）')
print('      ⇒ 所以 `%d` 条 `dry_*` 里有**历史留档**，不是 %d 个独立实验。' % (len(ds), len(ds)))
print('    · **arm 与 lane（道）**：goal 里"4 道并行"的"道"是**工作副本/车道**（一个车道可以跑多条臂）。')
print('=' * 100)
