#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_paramdiff.py --- ★★★★★ 比 F 与 L 的**实际**命令行参数（从**日志横幅**取，权威）

## 为什么
R161 实测：F 与 L 在 **step 5** 就分叉（`nf2`：0 vs 477）⇒ **L 不是 F 的复制**。
**⇒ 必须查出**哪个参数不同**** —— 否则 L 不能当"同构型的第三个样本"。
**按 P31**：先查"它是谁构造的" ⇒ **查它的实际参数**（日志横幅比脚本更权威）。
"""
import os
import re
import sys
from collections import OrderedDict

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
LOGS = OrderedDict([('F', '_w2_r581_mn64_F.log'),
                    ('G', '_w2_r581_mn64_G.log'),
                    ('L', '_w2_r581_mn64_L.log')])


def opts(path):
    """从日志里抓 `--xxx val` 形式的参数（出现过的都算）。"""
    if not os.path.exists(path):
        return None
    d = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            for m in re.finditer(r'--([a-zA-Z0-9][a-zA-Z0-9-]*)(?:[ =]+([^\s,;\]]+))?', line):
                k, v = m.group(1), m.group(2)
                if k not in d:
                    d[k] = v if v is not None else '(flag)'
    return d


def main():
    ds = {}
    for t, p in LOGS.items():
        d = opts(os.path.join(ROOT, p))
        if d is None:
            print('  %s: 无日志' % t)
            continue
        ds[t] = d
        print('  %s: 抓到 %d 个 `--` 参数' % (t, len(d)))
    if len(ds) < 2:
        return
    print()
    print('=' * 96)
    print('F / G / L 的参数对照（只列**出现过的**；`—` = 该臂日志里没出现）')
    print('=' * 96)
    keys = sorted(set().union(*[set(d) for d in ds.values()]))
    print(' %-24s %-16s %-16s %-16s %s' % ('参数', 'F', 'G', 'L', '一致？'))
    print(' ' + '-' * 88)
    ndiff = 0
    for k in keys:
        vs = [ds.get(t, {}).get(k, '—') for t in ('F', 'G', 'L')]
        same = (vs[0] == vs[2])   # 重点比 F vs L
        if not same:
            ndiff += 1
        mark = '✅' if same else '★ 差'
        print(' %-24s %-16s %-16s %-16s %s' % ('--' + k, vs[0][:15], vs[1][:15], vs[2][:15], mark))
    print()
    print('  ★ F 与 L 有 %d 个参数不同' % ndiff)
    print('  ★ 判读：**`--eng-seed` / `--block-seed` / `--nuc-*` 的差异会直接改前几步**')
    print('=' * 96)


if __name__ == '__main__':
    main()
