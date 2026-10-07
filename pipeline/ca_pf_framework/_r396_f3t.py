#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r396_f3t.py —— F3（同变体/块内低角界面）的时间轨迹：**投影 10 vs 投影 0**。

## 为什么查
`series.csv` 的 `nf3` 显示：**t=0 时 1169 个 F3 面，到 step 20 掉到 2–59**
⇒ 播下的"块内两根板条之间的低角界面"**在头 20 步几乎被抹掉**，之后才回升。

`AUDIT_SUMMARY` §142.1 已把这件事记为 **P1-42（`--facet-proj` 抹掉 F3）**：
「F3 从 t=0 的 11.8% 塌到 step 80 的 0.9%，再回升到 3.0%」。

**⇒ 本脚本做的判据：若 `--facet-proj 0` 的臂**不塌**，则归因成立**（单变量对照）。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')

ARMS = [('saSet2', 10), ('saSet2F2', 10),
        ('saSet2P0', 0), ('saSet2F2P0', 0),
        ('saSet2DT200', 10), ('permB1_400', 10)]
COLS = ('nf3', 'f3_faces')


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    R = list(csv.DictReader(io.open(p, encoding='utf-8')))
    col = next((c for c in COLS if c in R[0]), None)
    if col is None:
        return None
    st, v = [], []
    for r in R:
        try:
            st.append(int(float(r['step'])))
            v.append(float(r[col]))
        except (TypeError, ValueError):
            pass
    return col, np.asarray(st), np.asarray(v)


def main():
    print('=' * 92)
    print('F3（同变体 / 块内低角界面）面数时间轨迹')
    print('=' * 92)
    print('  %-14s %-6s %10s %10s %10s %10s %10s' %
          ('臂', 'proj', 't=0', '最低', '最低@步', '末值', '恢复比'))
    for tag, proj in ARMS:
        o = load(tag)
        if o is None:
            print('  %-14s %-6d ⚠ 无 nf3 列' % (tag, proj))
            continue
        col, st, v = o
        i0 = int(np.argmin(v))
        print('  %-14s %-6d %10.0f %10.0f %10d %10.0f %10.2f'
              % (tag, proj, v[0], v[i0], st[i0], v[-1],
                 v[-1] / max(v[0], 1e-9)))
    print()
    print('  ## 判据')
    print('     * 若 **proj=0 的臂不塌、proj=10 的臂塌** ⇒ `--facet-proj` 是元凶（单变量对照）')
    print('     * 若**两者都塌** ⇒ 与投影无关，是别的机制（界面能太弱 / 数值合并）')


if __name__ == '__main__':
    sys.exit(main())
