#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r548_colcmp.py —— **逐列**比较 `fr_reg`（新代码·默认开关）与归档 `b4`（旧代码·同配置），
找出**第一个开始不同的列**。

## 为什么必须逐列
`diff` 只告诉我"32 行全变了"，**不告诉我变的是哪个物理量**。
本仓的做法是：**先定位到列，再回代码找那一列是谁写的**（§3.3 教训 13：
"验证失败先 diff 输入文件，别急着归因到刚改的参数"）。

## 判据
* 打印每一列在两条 CSV 里是否逐位相同；
* 第一处不同的列名 + 该列在第 1 个不同行上的两个值。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '_exp/_bk_par/fr_reg/dry_fr_reg/series.csv')
B = os.path.join(HERE, '_exp/_bk_par/b4/dry_b4/series.csv')


def load(p):
    rows = [r for r in open(p, errors='replace').read().splitlines() if r.strip()]
    hdr = rows[0].split(',')
    return hdr, [r.split(',') for r in rows[1:]]


def main():
    if not (os.path.exists(A) and os.path.exists(B)):
        print('❌ 缺文件：\n  A=%s\n  B=%s' % (A, B))
        return 1
    ha, ra = load(A)
    hb, rb = load(B)
    print('=' * 96)
    print('R548 —— 逐列比较：`fr_reg`（新代码·默认） vs `b4`（旧代码·同配置）')
    print('=' * 96)
    print('  行数：fr_reg=%d  b4=%d ；列数：%d vs %d' % (len(ra), len(rb), len(ha), len(hb)))
    if ha != hb:
        print('  ⚠ **表头都不同** ⇒ 列集合变了')
        print('    fr_reg 独有：%s' % sorted(set(ha) - set(hb)))
        print('    b4     独有：%s' % sorted(set(hb) - set(ha)))
    n = min(len(ra), len(rb))
    diff_cols = []
    for i in range(min(len(ha), len(hb))):
        col = ha[i]
        if i >= len(ra[0]) or i >= len(rb[0]):
            continue
        for r in range(n):
            if ra[r][i] != rb[r][i]:
                diff_cols.append((col, r, ra[r][i], rb[r][i]))
                break
    print()
    print('  ── **有差异的列**（按首次出现差异的行号排序） ──')
    if not diff_cols:
        print('     （无）⇒ **逐位相同** ✅')
    for col, r, va, vb in sorted(diff_cols, key=lambda x: x[1]):
        print('     %-16s 第 %2d 行：fr_reg=%-24s b4=%s'
              % (col, r + 1, va[:24], vb[:24]))
    print()
    print('  ── 完全相同的前 12 列（对照：说明大部分列没动） ──')
    same = [ha[i] for i in range(min(len(ha), len(hb)))
            if ha[i] not in [c for c, _, _, _ in diff_cols]]
    print('     %s' % ', '.join(same[:12]))
    print()
    print('★ 汇总：有差异的列 = **%d / %d**；第一处差异在第 %s 行、列 `%s`'
          % (len(diff_cols), len(ha),
             (min(d[1] for d in diff_cols) + 1) if diff_cols else '—',
             (min(diff_cols, key=lambda x: x[1])[0]) if diff_cols else '—'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
