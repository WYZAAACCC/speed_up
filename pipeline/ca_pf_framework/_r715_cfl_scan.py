#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r715_cfl_scan.py —— **只读**：把所有归档 `series.csv` 的 `cfl_used` 列扫一遍。

## 为什么写它
`R712_REPAIR_SPEC.md` §6.3 / `R714_FINAL_PROBLEMS.md` §1.11 说：
> `[推理]` 因 `dt·M·Δf/dx = 0.15` ⇒ `cfl_used = 0.15·(dG_max/Δf)`，
> 按上游记的 `dG_max/Δf ~ 10–100` 应在 **1–10**。
> ⚠ **我未读生产 CSV 核实**（生产 `_exp` 不在本机）⇒ **S1 就是把它接成守卫**。

⇒ **本脚本就是那一步的只读版**：不改任何主代码，直接把 `cfl_used` 的
**峰值 / 分位 / 越限步数** 从**已有归档**里量出来，让 F8 从 `[推理]` 升级为 `[实测]`。

## 用法
    python3 _r715_cfl_scan.py [根目录 ...]
默认扫 `_exp/_bk_t5` 与 `_exp/_bk_block`（本机两个归档根）。

## 口径（写死，与 `series.csv` 同名列同一口径）
    cfl_used = dt·MOB·dG_max/dx        （`_bk_exp.py:88` 列名、`:3589` 计算）
    上限     = 1.0                     （界面每步位移恰为一个 dx）

## 诚实边界
* 只读 `series.csv`；**不读快照、不跑仿真**。
* `cfl_used = nan` 的行（step 0）**计入读数但不计入越限统计**。
"""
import csv
import os
import sys

ROOTS = sys.argv[1:] or ['_exp/_bk_t5', '_exp/_bk_block']
LIMIT = 1.0


def scan(path):
    """返回 (n, n_nan, mx, argmax_step, n_over, first_over, med, p95) 或 None。"""
    try:
        with open(path, newline='') as f:
            rd = csv.DictReader(f)
            if rd.fieldnames is None or 'cfl_used' not in rd.fieldnames:
                return None
            vals = []
            for row in rd:
                s = (row.get('cfl_used') or '').strip()
                try:
                    v = float(s)
                except ValueError:
                    v = float('nan')
                step = (row.get('step') or '').strip()
                vals.append((step, v))
    except OSError:
        return None
    if not vals:
        return None
    good = [(s, v) for s, v in vals if v == v]          # NaN != NaN
    n_nan = len(vals) - len(good)
    if not good:
        return None
    mx = max(v for _, v in good)
    argmax = next(s for s, v in good if v == mx)
    over = [(s, v) for s, v in good if v > LIMIT]
    sv = sorted(v for _, v in good)
    med = sv[len(sv) // 2]
    p95 = sv[min(len(sv) - 1, int(round(0.95 * (len(sv) - 1))))]
    return (len(good), n_nan, mx, argmax, len(over),
            (over[0][0] if over else '-'), med, p95)


def main():
    print('=' * 108)
    print('cfl_used 归档扫描（只读）—— 判据：cfl_used ≤ %.2f' % LIMIT)
    print('口径：cfl_used = dt·MOB·dG_max/dx，与 series.csv 同名列一致（_bk_exp.py:88/:3589）')
    print('=' * 108)
    rows = []
    for root in ROOTS:
        if not os.path.isdir(root):
            print('  ⚠ 目录不存在，跳过：%s' % root)
            continue
        for tag in sorted(os.listdir(root)):
            p = os.path.join(root, tag, 'series.csv')
            if not os.path.isfile(p):
                continue
            r = scan(p)
            if r is None:
                rows.append((root, tag, None))
                continue
            rows.append((root, tag, r))

    ok = [r for r in rows if r[2] is not None]
    no_col = [r for r in rows if r[2] is None]
    print('\n共 %d 个归档有 series.csv；其中有 cfl_used 列的 %d 个，无该列的 %d 个\n'
          % (len(rows), len(ok), len(no_col)))

    print('%-34s %5s %5s %10s %8s %6s %8s %8s' %
          ('tag', 'n', 'nan', 'max', '@step', '>1.0', 'first>1', 'median'))
    print('-' * 108)
    for root, tag, rec in sorted(ok, key=lambda z: -(z[2][2])):
        n, n_nan, mx, am, nov, fo, med, p95 = rec
        flag = '  ⛔越限' if nov else ''
        print('%-34s %5d %5d %10.4f %8s %6d %8s %8.4f%s'
              % (tag[:34], n, n_nan, mx, am, nov, fo, med, flag))

    if ok:
        mx_all = max(z[2][2] for z in ok)
        n_over_all = sum(z[2][4] for z in ok)
        tags_over = [z[1] for z in ok if z[2][4]]
        print('\n' + '=' * 108)
        print('★ 全库峰值 cfl_used = %.4f  （判据 %.2f）' % (mx_all, LIMIT))
        print('★ 越限归档数 = %d / %d' % (len(tags_over), len(ok)))
        if tags_over:
            print('  越限的 tag：%s' % ', '.join(tags_over[:20]))
        else:
            print('  ⇒ **没有任何归档越限** ⇒ `R712 §6.3` 的 [推理] "应在 1–10" **被实测否证**')
        print('=' * 108)

    if no_col:
        print('\n无 cfl_used 列的归档（旧格式，不入统计）：%d 个' % len(no_col))
        for _, t, _ in no_col[:10]:
            print('   ', t)


if __name__ == '__main__':
    main()
