#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_bk67.py --- ★★★★★ **`--stack-pick-dg` 到底生效了吗**（靠两臂分叉判断）

## 为什么这样判
`BK6`（`stack_pick_dg=0`）与 `BK7`（`=1`）**只差这一个开关**，其余逐字相同。
⇒ **若开关真的改了选择逻辑，两臂的 `series.csv` **必然分叉****（**同一 seed、同一构型**）；
⇒ **若前几步**逐位相同** ⇒ **开关**没接上/被静默忽略****（**`:2285` 的 `not hardened` 守卫**）。

⚠ 这比"看 `dg_pick` 计数器"更直接 —— **计数器可能只在收尾时 dump**。
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
A, B = 'BK6', 'BK7'
KEYS = ['nslab_n', 'nslab_n1', 'nf3', 'nf2', 'nblk_sig', 'r_selfac', 'n_habit']


def load(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))


def main():
    ra, rb = load(A), load(B)
    if ra is None or rb is None:
        print('  ⚠ 缺数据（%s=%s, %s=%s）' % (A, ra is not None, B, rb is not None))
        return
    k = list(ra[0].keys())[0]
    da = {r[k]: r for r in ra}
    db = {r[k]: r for r in rb}
    common = sorted(set(da) & set(db), key=lambda x: int(float(x)))
    print('=' * 100)
    print('`--stack-pick-dg` 生效性：%s（=0）vs %s（=1），共同步 %d 个' % (A, B, len(common)))
    print('=' * 100)
    print('  %-6s %s' % ('step', ' '.join('%-13s' % c[:13] for c in KEYS)))
    print('  ' + '-' * 96)
    ndiff = 0
    for s in common:
        row = []
        diff = False
        for c in KEYS:
            va = (da[s].get(c, '') or '').strip()
            vb = (db[s].get(c, '') or '').strip()
            if va != vb:
                diff = True
            row.append('%-13s' % ('%s|%s' % (va[:6], vb[:6]) if diff and va != vb else va[:13]))
        if diff:
            ndiff += 1
        print('  %-6s %s' % (s, ' '.join(row)))
    print()
    print('  ★ **有差异的步数 = %d / %d**' % (ndiff, len(common)))
    print()
    if ndiff == 0:
        print('  ❌ **前 %d 步逐位相同 ⇒ `--stack-pick-dg` **没有生效****' % len(common))
        print('     ⇒ 查 `windowB_surface.py:2285` 的 `not hardened` 守卫（hardened 为真时会静默跳过）')
    else:
        print('  ✅ **两臂分叉 ⇒ 开关**真的生效**** ⇒ 可以等 `r_selfac` 出来做置换检验')
    print('=' * 100)


if __name__ == '__main__':
    main()
