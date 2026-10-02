#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_dftraj.py --- 把 `df` 的**完整轨迹**抽出来（判据⑪ 后半句的落盘证据）。

`_r581_dfchk.py` 已查明：**stdout 日志里确实有 `df`，而且它在变**
（`p2_b3`：`1.5050e+08 → 1.8820e+08`）。本量具把它**逐条**抽出来，
带上**上下文**（哪一行、附近的 step / T），做成可核对的表。

判据（**预先写死**）：
* **df 出现次数 ≥ 3 且取值不全同** ⇒ 判据⑪ 后半句 ✅ **取证通过**；
* 恒为常数 ⇒ ❌；只出现 1 次 ⇒ ⚠ **样本不足**（如实登记）。
"""
import os
import re
import sys

import numpy as np

TAGS = sys.argv[1:] or ['p2_b5', 'p2_b3']


def main():
    print('=' * 100)
    print('R581 —— `df` 完整轨迹（判据⑪："日志里必须能看到 df 随时间变化"）')
    print('=' * 100)
    for tag in TAGS:
        log = '_w2_r581_p2_%s.log' % tag
        if not os.path.exists(log):
            cand = [f for f in os.listdir('.') if f.endswith('.log') and tag in f]
            log = cand[0] if cand else None
        print()
        print('#' * 100)
        print('# %s  ←  %s' % (tag, log))
        print('#' * 100)
        if log is None or not os.path.exists(log):
            print('  ❌ 找不到日志'); continue
        lines = open(log, encoding='utf-8', errors='replace').read().split('\n')
        rows = []
        for i, ln in enumerate(lines):
            for m in re.finditer(r'\bdf\s*=\s*([-+0-9.eE]+)', ln):
                # 往上找最近的、含 step 标记的行
                step = None
                for j in range(i, max(-1, i - 12), -1):
                    s = re.search(r'\[\s*(\d+)\]', lines[j])
                    if s:
                        step = int(s.group(1)); break
                # 找同一行的 T（若有）
                t = re.search(r'\bT\s*=\s*([-+0-9.eE]+)', ln)
                rows.append((step, float(m.group(1)), t.group(1) if t else '', ln.strip()[:110]))
        if not rows:
            print('  ❌ 日志里**没有** `df=`'); continue
        print('  `df` 共出现 **%d** 次：' % len(rows))
        print('  %-8s %-16s %-12s %s' % ('step', 'df', 'T', '所在行（截断）'))
        for st, v, t, ln in rows:
            print('  %-8s %-16.6g %-12s %s' % (st if st is not None else '?', v, t or '—', ln))
        vals = np.array([r[1] for r in rows])
        print()
        nz = int((np.diff(vals) != 0).sum())
        print('  ⇒ 取值：min %.6g  max %.6g  **变化次数 %d/%d**'
              % (vals.min(), vals.max(), nz, max(len(vals) - 1, 1)))
        ratio = vals.max() / vals.min() if vals.min() != 0 else float('inf')
        print('  ⇒ max/min = **%.3f×**' % ratio)
        if len(rows) >= 3 and nz > 0:
            print('  ⇒ 判据⑪ 后半句（"日志里能看到 df 随时间变"）：✅ **取证通过**')
            if len(rows) < 20:
                print('     ⚠ **但样本只有 %d 个点** —— 只能证明"在变"，**画不出完整曲线**；'
                      % len(rows))
                print('       如实登记，不夸大成"驱动力-温度关系已标定"。')
        elif len(rows) < 3:
            print('  ⇒ ⚠ **样本不足**（%d 个点）⇒ 不算取证通过，如实登记' % len(rows))
        else:
            print('  ⇒ ❌ **恒为常数** ⇒ 判据⑪ 后半句不通过')
    print()
    print('=' * 100)
    print('★ 另外：准静态钟的 `dt` 逐行在 `series.csv` 里（97 列之一）')
    print('  ⇒ 那 5 次变化对应 5 个温度档 ⇒ **"驱动力随温度变"的间接旁证**')
    print('  ⚠ 但 goal 要的是 **`df` 本身**，所以上表才是主证据。')
    print('=' * 100)


if __name__ == '__main__':
    main()
