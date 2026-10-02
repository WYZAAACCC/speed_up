#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ckpt_cmp.py --- ★★★★★ **两份 `series.csv` 的逐位比较**（门 1 的量具）

## 为什么不能用 `pandas.equals` / `np.array_equal`
本仓库的 P16 教训：**`NaN != NaN` 会让"全是 NaN 的两列"被报成"不同"**，
而 `max(0.0, nan) = 0.0` 又会让"真有 NaN 差异"被报成"相同"。
**⇒ 必须 NaN 感知 + 比符号位（+0.0 vs −0.0 也要分清）。**

## 口径（**先写死**）
| 情形 | 判定 |
|---|---|
| 两边都 NaN（且**符号位相同**） | **相同** |
| 一边 NaN、一边有限 | **不同**（记 `nan_mismatch`） |
| 都有限 | **必须 `float64` 逐位相同**（`tobytes()` 相等） |
| 字符串列 | 逐字符相同 |

**⚠ 不比 `wall_s`**（挂钟，本来就该不同）—— **但要比其它所有共有列**。
"""
import csv
import os
import sys

import numpy as np

# 明确**不参与**逐位比较的列（挂钟/吞吐这类天然不同的量）
SKIP = {'wall_s'}


def load(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        rows = list(csv.DictReader(f))
    return rows


def cell_bits(s):
    """把 CSV 里的一个格子转成"可比对象"：'nan' / ('f', float64 字节) / ('s', 串)。"""
    t = (s or '').strip()
    if t == '' or t.lower() in ('nan', 'none', 'null'):
        return ('nan', b'')
    try:
        v = float(t)
    except ValueError:
        return ('s', t)
    if v != v:                                   # NaN
        # ★ 保留**符号位**：'nan' 与 '-nan' 不是同一个东西（P16）
        return ('nan', b'-' if t.startswith('-') else b'+')
    return ('f', np.float64(v).tobytes())


def main():
    pa, pb = sys.argv[1], sys.argv[2]
    ka = sys.argv[3] if len(sys.argv) > 3 else 'step'
    if not (os.path.exists(pa) and os.path.exists(pb)):
        print('  ⚠ 文件不存在：%s / %s' % (pa, pb))
        raise SystemExit(1)
    ra, rb = load(pa), load(pb)
    if not ra or not rb:
        print('  ⚠ 有一边为空')
        raise SystemExit(1)
    cols = [c for c in ra[0] if c in rb[0] and c not in SKIP]
    # 按 key 建索引
    ma = {r[ka]: r for r in ra}
    mb = {r[ka]: r for r in rb}
    common = sorted(set(ma) & set(mb),
                    key=lambda x: (len(x), x))
    print('=' * 100)
    print('逐位比较：A=%s  vs  B=%s' % (os.path.basename(os.path.dirname(pa)), 
                                        os.path.basename(os.path.dirname(pb))))
    print('  A 行数 %d，B 行数 %d；共有 step %d 个；共有列 %d 个（已排除 %s）'
          % (len(ra), len(rb), len(common), len(cols), sorted(SKIP)))
    print('  共有 step：%s' % (', '.join(common[:24]) + ('…' if len(common) > 24 else '')))
    print('=' * 100)
    diff_cols = {}
    nan_mis = 0
    sign_mis = 0
    first = []
    for k in common:
        for c in cols:
            a = cell_bits(ma[k].get(c))
            b = cell_bits(mb[k].get(c))
            ok = (a == b)
            if not ok:
                diff_cols[c] = diff_cols.get(c, 0) + 1
                if a[0] == 'nan' and b[0] == 'nan':
                    sign_mis += 1          # 都是 NaN 但**符号位**不同
                elif a[0] == 'nan' or b[0] == 'nan':
                    nan_mis += 1
                if len(first) < 12:
                    first.append((k, c, ma[k].get(c), mb[k].get(c)))
    print('  ── 结果 ──')
    print('  **差异字段数 = %d**' % sum(diff_cols.values()))
    print('  其中：NaN vs 有限 = %d ；NaN 符号位不同 = %d' % (nan_mis, sign_mis))
    if diff_cols:
        print('  ── 有差异的列（前 15）──')
        for c, n in sorted(diff_cols.items(), key=lambda x: -x[1])[:15]:
            print('    %-22s %d 处' % (c, n))
        print('  ── 前 12 个具体差异 ──')
        for k, c, va, vb in first:
            print('    step=%-6s %-20s A=%-24s B=%s' % (k, c, va, vb))
    else:
        print('  ⇒ ✅✅ **共有列逐位一致**（NaN 感知 + 比符号位）')
    print()
    print('  ── ★ goal 门 1 要求**单独报**的那几个量 ──')
    for c in ('Vt', 'f_var', 'nslab_n1', 'nf3', 'nf2'):
        if c in cols:
            bad = sum(1 for k in common if cell_bits(ma[k].get(c)) != cell_bits(mb[k].get(c)))
            print('    %-12s 差异 %d 处  %s' % (c, bad, '✅' if bad == 0 else '❌'))
        else:
            print('    %-12s （不在共有列里）' % c)
    print('=' * 100)
    return 0 if sum(diff_cols.values()) == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
