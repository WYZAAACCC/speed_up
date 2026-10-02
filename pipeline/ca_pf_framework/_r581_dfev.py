#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_dfev.py --- ★★★★★ **判据⑪ 后半的判决**：`df` 是不是**真的随步数/温度变**？

## goal §(16) ⑥ 逐字
> 「★ "**驱动力随温度变**"要有**实测证据**：**日志里必须能看到 df 随时间变化**
>   （**打印出来，不许只看代码**）」

## 怎么算数
* **在同一份日志里，取"不同 step"下的 `df=` 打印值** ⇒
  * **值**不同** ⇒ ✅ 实测证据成立**；
  * **值**全同** ⇒ ❌ 只打印了常数（**可能只在 step 0 打印过**）** ⇒ 判据不达成。
* **★ 只比"同一步内重复打印的相同值"不算数**（那是同一时刻）。
"""
import re
import sys
from collections import OrderedDict

PATHS = sys.argv[1:] or ['_w2_r581_blk_BK6.log', '_w2_r581_mn64_F.log',
                         '_w2_r581_blk_BG2.log']


def main():
    for p in PATHS:
        try:
            txt = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            print('  %-34s （读不到）' % p)
            continue
        print('=' * 94)
        print('日志 %s' % p)
        print('=' * 94)
        # 抓 "df=<数>" 以及它前面最近的 "step N"
        # 引擎的形核行形如：★★ athermal 形核 @ step 1：T=... ；df=...
        recs = OrderedDict()
        for m in re.finditer(r'@\s*step\s*(\d+)[^\n]*?df\s*=\s*([0-9.eE+-]+)', txt):
            st, v = int(m.group(1)), float(m.group(2))
            recs.setdefault(st, set()).add(v)
        if not recs:
            # 退一步：只要有 df= 就收，按出现顺序
            vals = [float(x) for x in re.findall(r'df\s*=\s*([0-9.eE+-]+)', txt)]
            uniq = sorted(set(vals))
            print('  （没抓到 "step + df" 的组合；只抓到 %d 个 df= 值，其中互异 %d 个）'
                  % (len(vals), len(uniq)))
            if uniq:
                print('  互异值前 6 个：%s' % ', '.join('%.4g' % x for x in uniq[:6]))
            print()
            continue
        print('  抓到 %d 个"不同 step"的 df：' % len(recs))
        show = sorted(recs)[:10]
        for st in show:
            vs = sorted(recs[st])
            print('    step %-6d df = %s' % (st, ', '.join('%.6g' % x for x in vs)))
        allv = set()
        for s in recs.values():
            allv |= s
        print()
        if len(allv) > 1:
            print('  ✅ **%d 个 step 上出现了 %d 个互异的 df** ⇒ **驱动力确实在变**（实测证据成立）'
                  % (len(recs), len(allv)))
            print('     范围：%.6g … %.6g（**比值 %.4g×**）'
                  % (min(allv), max(allv), max(allv) / min(allv)))
        else:
            print('  ❌ **所有 step 上的 df 都是同一个值（%.6g）** ⇒ **只有常数 ⇒ 判据不达成**'
                  % list(allv)[0])
        print()


if __name__ == '__main__':
    main()
