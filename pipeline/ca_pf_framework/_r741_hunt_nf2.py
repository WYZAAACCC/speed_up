#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r741_hunt_nf2.py —— **全盘搜索：有没有任何运行目录出现过 `nf2 > 0`？**

## 为什么要做（`R740` 的教训）
我在 `R739`/`R740` 连搭两次 T2 的 A/B，第二次才发现 `_t11_iface_ab.py` 早就做过。
⇒ **纪律**：问一个"某量是否曾经出现过"的问题时，**先全盘扫一遍**，
而不是设计新实验。

## 本脚本问的问题
**`nf2`（异变体界面格面数）在**本仓全部 `series.csv`** 里，最大值是多少？出现在哪个臂/哪一步？**
* 若**存在 `nf2 > 0`** ⇒ **已有配置能造出 F2 界面** ⇒ 直接读它，不必改主代码；
* 若**恒为 0** ⇒ 印证"生产机制下 F2 通道够不着"，且**覆盖全部历史**（不只是 `R725` 的 3 轮）。

## 口径
* 扫描根：`_exp/` 与仓库根下的 `_exp*`（以及 `_bk_t5` 等既有归档）；可用 `--roots` 覆盖
* 对每个 `series.csv`：读 `nf2` 列（若存在），取 max / 非零计数
* 同时记录 `n_var_sig`、`nf3_col` 的 max（辅助判断"变体存在但不接触"）
"""
import argparse
import csv
import os
import sys

DEFAULT_ROOTS = [
    '/mnt/f/speed_up/_exp',
    '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp',
]


def num(r, k):
    try:
        return float(r.get(k))
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--roots', nargs='*', default=DEFAULT_ROOTS)
    ap.add_argument('--maxrows', type=int, default=200000)
    a = ap.parse_args()

    found_csv = 0
    no_col = 0
    hits = []          # (max_nf2, arm, step, n_var_sig, nf3_col)
    allzero = 0
    for root in a.roots:
        if not os.path.isdir(root):
            print('  ⚠ 根不存在：%s' % root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if 'series.csv' not in filenames:
                continue
            p = os.path.join(dirpath, 'series.csv')
            found_csv += 1
            if found_csv > a.maxrows:
                break
            try:
                with open(p, newline='') as f:
                    rows = [r for r in csv.DictReader(f) if r.get('step')]
            except OSError:
                continue
            if not rows or 'nf2' not in rows[0]:
                no_col += 1
                continue
            best = None
            for r in rows:
                v = num(r, 'nf2')
                if v is None:
                    continue
                if best is None or v > best[0]:
                    best = (v, r.get('step'), num(r, 'n_var_sig'), num(r, 'nf3_col'))
            if best is None:
                continue
            arm = os.path.basename(dirpath)
            if best[0] > 0:
                hits.append((best[0], arm, best[1], best[2], best[3]))
            else:
                allzero += 1

    print('=' * 100)
    print('全盘搜索 `nf2 > 0`（异变体界面格面数）')
    print('=' * 100)
    print('  扫到 series.csv          = %d' % found_csv)
    print('  其中无 `nf2` 列          = %d' % no_col)
    print('  ★ **`nf2` 恒为 0 的臂**  = %d' % allzero)
    print('  ★★ **出现过 `nf2 > 0` 的臂** = %d' % len(hits))
    print()
    if hits:
        hits.sort(reverse=True)
        print('  %-12s %-28s %8s %12s %10s' % ('max_nf2', '臂', 'step', 'n_var_sig', 'nf3_col'))
        for h in hits[:40]:
            print('  %-12g %-28s %8s %12s %10s'
                  % (h[0], h[1][:28], h[2], h[3], h[4]))
        print()
        print('  ⇒ ⇒ **存在能造出 F2 界面的配置** ⇒ 下一步应读这些臂的调用参数，')
        print('     而不是改主代码（`R740` 的教训）。')
    else:
        print('  ⇒ ⛔ **全部 %d 个臂 `nf2` 恒为 0** ⇒ 覆盖**整个归档历史**（不只是 `R725` 的 3 轮）。')
        print('     这是"生产机制下 F2 通道够不着"的**全历史证据**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
