#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_lvf.py --- ★★★★★ **L 与 F 的前几步对账**（同参数 ⇒ 前几步应**逐位一致**）

## 为什么要查
L 在第 5 步就有 `nslab_n`=12、`nf2`=477 —— 而 F 到第 200 步 `nf2` 才 128。
**若两者参数逐字相同、`--eng-seed` 也相同 ⇒ 前几步应当**完全一样****。
**⇒ 不一致就说明"L 不是 F 的复制"** ⇒ **L 作为"第三个样本"的资格要打问号**（P31：先查它是谁构造的）。
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['F', 'L']
KEYS = ['nslab_n', 'nf3_col', 'nf3', 'nf2', 'Vt']


def load(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    return rows


def main():
    data = {}
    for t in TAGS:
        rows = load(t)
        if rows is None:
            print('  %-3s （无 series.csv）' % t)
            continue
        data[t] = {r[list(r.keys())[0]]: r for r in rows}
    print('=' * 100)
    print('L 与 F 的逐步对账（同参数 ⇒ 同一步应当一致）')
    print('=' * 100)
    for t in TAGS:
        if t not in data:
            continue
        ks = sorted(data[t].keys(), key=lambda x: int(float(x)))[:8]
        print()
        print('  ── 臂 %s 的前 %d 步 ──' % (t, len(ks)))
        print('   %-6s %s' % ('step', ' '.join('%-12s' % k for k in KEYS)))
        for k in ks:
            r = data[t][k]
            vals = []
            for kk in KEYS:
                v = r.get(kk, '—')
                try:
                    vals.append('%-12.6g' % float(v))
                except Exception:
                    vals.append('%-12s' % str(v)[:12])
            print('   %-6s %s' % (k, ' '.join(vals)))
    # 对账
    if len(data) == 2:
        a, b = TAGS[0], TAGS[1]
        common = sorted(set(data[a]) & set(data[b]), key=lambda x: int(float(x)))[:8]
        print()
        print('  ── ★ 共同步的对账 ──')
        if not common:
            print('   （没有共同步）')
        for k in common:
            diffs = []
            for kk in KEYS:
                va, vb = data[a][k].get(kk), data[b][k].get(kk)
                try:
                    if abs(float(va) - float(vb)) > 0:
                        diffs.append('%s: %s vs %s' % (kk, va, vb))
                except Exception:
                    if va != vb:
                        diffs.append('%s: %s vs %s' % (kk, va, vb))
            print('   step %-5s %s' % (k, '✅ 一致' if not diffs else '⚠ ' + '; '.join(diffs)))
    print()
    print('  ★ 判读：**前几步一致** ⇒ L 是 F 的忠实复制 ⇒ **可作第三个样本**；')
    print('          **不一致** ⇒ L 与 F **不是同一构型** ⇒ 必须查参数/seed（P31）')
    print('=' * 100)


if __name__ == '__main__':
    main()
