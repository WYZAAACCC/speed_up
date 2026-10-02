#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nanscan.py --- ★★★★★★ **哪些列在**真臂**里是 NaN/空**？

## 为什么要查
R163b 查出：S1/S2 与 D1/D2 的"9 个不同列"里，**8 个的最大相对差 = 0.000e+00** ⇒ **两边都是 NaN**。
**⇒ 若那些列在**生产臂**（F/G/L/E/p2_*）里**也是 NaN** ⇒ **它们本来就不携带信息** ⇒
   * **对"逐位比较"无害**（**两边都 NaN**）—— **但**必须 NaN 感知**，否则假报不一致（P16）；
   * **★ 更重要的：若 `psi_mean` / `dG_*` 这类**应该有意义**的量是 NaN ⇒ 那是**真的诊断缺失**，
     要单独登记（**不能拿"它总是 NaN"当正常**）。
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['E', 'F', 'G', 'L']


def isnan_str(s):
    s = (s or '').strip()
    if s == '':
        return True
    try:
        v = float(s)
        return v != v          # NaN
    except Exception:
        return False


def main():
    allcols = None
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
        if not os.path.exists(p):
            print('  %-4s （无 series.csv）' % t)
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        if not rows:
            continue
        hdr = list(rows[0].keys())
        nan_cols, ok_cols = [], []
        for k in hdr:
            n = sum(1 for r in rows if isnan_str(r.get(k)))
            if n == len(rows):
                nan_cols.append(k)
            elif n > 0:
                nan_cols.append('%s(%d/%d)' % (k, n, len(rows)))
            else:
                ok_cols.append(k)
        print('=' * 96)
        print('臂 %s：%d 行 / %d 列；**全 NaN 或部分 NaN 的列有 %d 个**' % (t, len(rows), len(hdr), len(nan_cols)))
        print('=' * 96)
        if nan_cols:
            for k in nan_cols:
                print('   ★ %s' % k)
        else:
            print('   ✅ 没有 NaN 列')
        print()
        if allcols is None:
            allcols = set(hdr)
        else:
            allcols &= set(hdr)
    print('=' * 96)
    print('★ 判读：')
    print(' · **全 NaN 的列** ⇒ 它们**不携带信息** ⇒ 逐位比较必须**跳过**（P16）')
    print(' · **部分 NaN 的列** ⇒ 要看是"前几步还没算"还是"真的缺"（**后者要单独登记**）')
    print(' · 若 `psi_mean`/`dG_*` 在**所有**臂里都全 NaN ⇒ 那是**诊断缺失**，不是比较问题')
    print('=' * 96)


if __name__ == '__main__':
    main()
