#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_whichcols.py --- ★★★★★★ **哪些列确定、哪些不确定**（这才是关键区分）

## 为什么要分清
R163 查出：同参数、不同进程的两条臂，有 **8 个**列不同 —— 但**它们是不是"主状态"**？
* 若**主状态**（`Vt`/`nslab_n`/`nf3_col`/`nf3`/`nf2`/`vol_*`）**确定** ⇒ **物理确定，只有诊断噪声** ⇒ 影响可控；
* 若**主状态**也变 ⇒ **两次运行是两条不同的轨迹** ⇒ **跨臂比较全不可用** ⇒ 影响巨大。
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_det'
PAIRS = [('S1', 'S2', '都 1 线程'),
         ('D1', 'D2', '都 2 线程')]
PRIMARY_HINT = ('Vt', 'nslab', 'nf3', 'nf2', 'nf1', 'vol_', 'M', 'runs',
                'box_touch', 'f_var', 'nreg_used', 'V0')


def load(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))


def main():
    for a, b, label in PAIRS:
        ra, rb = load(a), load(b)
        if ra is None or rb is None:
            print('  %s vs %s：（缺数据）' % (a, b))
            continue
        hdr = list(ra[0].keys())
        diff, same = {}, []
        mx = {}
        for x, y in zip(ra, rb):
            for k in hdr:
                va, vb = x.get(k, ''), y.get(k, '')
                try:
                    fa, fb = float(va), float(vb)
                    if fa != fb:
                        diff[k] = diff.get(k, 0) + 1
                        rel = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
                        mx[k] = max(mx.get(k, 0.0), rel)
                except Exception:
                    if va != vb:
                        diff[k] = diff.get(k, 0) + 1
        same = [k for k in hdr if k not in diff]
        print('=' * 96)
        print('%s（%s vs %s）：共 %d 列，**不同 %d 列、相同 %d 列**'
              % (label, a, b, len(hdr), len(diff), len(same)))
        print('=' * 96)
        print('  ★ **不同的列**（按最大相对差降序）：')
        for k in sorted(diff, key=lambda z: -mx.get(z, 0)):
            isp = any(h in k for h in PRIMARY_HINT)
            print('     %-18s %d 行   最大相对差=%.3e   %s'
                  % (k, diff[k], mx.get(k, 0), '★ **主状态**' if isp else '（诊断）'))
        print()
        print('  ★ **相同的列**里，**主状态**有哪些：')
        prim_same = [k for k in same if any(h in k for h in PRIMARY_HINT)]
        print('     %s' % (', '.join(prim_same) if prim_same else '（无）'))
        print()
        # 结论
        prim_diff = [k for k in diff if any(h in k for h in PRIMARY_HINT)]
        if prim_diff:
            print('  ❌ **主状态也变**（%s）⇒ **两次运行是两条不同轨迹**' % ', '.join(prim_diff))
        else:
            print('  ✅ **主状态全同** ⇒ **物理确定；只有若干**派生诊断**不确定**')
        print()


if __name__ == '__main__':
    main()
