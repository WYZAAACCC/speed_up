#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_dfchk.py --- ★★ 判据⑪ 后半句的取证：**"驱动力随温度变"有没有实测证据？**

## 判据原话（goal §16⑥ / 成功判据⑪）
> **"驱动力随温度变"要有实测证据：日志里必须能看到 df 随时间变化
> （打印出来，不许只看代码）。**

## 本量具查三件事（不猜）
1. **stdout 日志**里有没有 `df` / 驱动力 / 温度 的逐行打印？
2. **`series.csv`** 里有哪些"温度 / 驱动力"相关的列？
3. 若有 ⇒ **把那条列随 step 的轨迹打出来**，看它**是不是真的在变**（不是常数）。

## 判据（**预先写死**）
* 若三处都找不到 ⇒ **判据⑪ 后半句 ❌ 未取证**（如实登记，不辩解说"代码里肯定在变"）
* 若找到 ⇒ 打印**首/中/末值 + 变化倍数 + 单调性**，作为落盘证据。
"""
import os
import re
import sys

import numpy as np

ROOT = '_exp/_bk_p2'
PAT_TEMP = re.compile(r'(T_?K|temp|T=|Tend|T_end|dT|df|drive|driv)', re.I)


def main():
    tags = sys.argv[1:] or ['p2_b5']
    print('=' * 96)
    print('R581 —— 判据⑪："驱动力随温度变"的实测取证')
    print('=' * 96)
    for tag in tags:
        print()
        print('#' * 96)
        print('# %s' % tag)
        print('#' * 96)
        # ── 1. stdout 日志 ──
        log = None
        for cand in ('_w2_r581_p2_%s.log' % tag, '_w2_r581_p2_%s.log' % tag):
            if os.path.exists(cand):
                log = cand
                break
        if log is None:
            # 找任何含该 tag 的日志
            for f in sorted(os.listdir('.')):
                if f.endswith('.log') and tag in f:
                    log = f
                    break
        if log and os.path.exists(log):
            txt = open(log, encoding='utf-8', errors='replace').read()
            hits = {}
            for m in re.finditer(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*([-+0-9.eE]+)', txt):
                k = m.group(1)
                if PAT_TEMP.search(k):
                    hits.setdefault(k, []).append(m.group(2))
            print('  ── ① stdout 日志 `%s`（%d 行）──' % (log, txt.count('\n')))
            if hits:
                for k, v in sorted(hits.items()):
                    print('     `%s`：%d 次出现，前 3 = %s' % (k, len(v), v[:3]))
            else:
                print('     ❌ **没有任何** 匹配 `T/df/drive` 的 `键=值` 打印')
        else:
            print('  ── ① stdout：**找不到日志文件**（tag=%s）──' % tag)
        # ── 2. series.csv 的列 ──
        p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('  ── ② %s 不存在 ──' % p); continue
        with open(p) as fh:
            cols = fh.readline().strip().split(',')
        cand = [c for c in cols if PAT_TEMP.search(c)]
        print('  ── ② `series.csv` 共 %d 列；与 T/df/drive 相关的列：**%s** ──'
              % (len(cols), cand if cand else '（一个都没有）'))
        dd = np.genfromtxt(p, delimiter=',', names=True)
        # ── 3. 轨迹 ──
        if cand:
            print('  ── ③ 这些列随 step 的轨迹（判"是不是常数"）──')
            st = np.atleast_1d(dd['step']).astype(int)
            for c in cand:
                v = np.atleast_1d(dd[c]).astype(float)
                fin = v[np.isfinite(v)]
                if fin.size == 0:
                    print('     `%s`：全 NaN' % c); continue
                nz = int((np.diff(fin) != 0).sum())
                print('     `%s`：首 %.6g → 末 %.6g ；**变化步数 %d/%d** ；min %.6g max %.6g %s'
                      % (c, fin[0], fin[-1], nz, max(len(fin) - 1, 1),
                         fin.min(), fin.max(),
                         '✅ **在变**' if nz > 0 else '❌ **恒为常数**'))
            print('     对应 step：首 %d → 末 %d' % (st[0], st[-1]))
        else:
            print('  ── ③ 无从画轨迹（没有相关列）──')
    print()
    print('=' * 96)
    print('★ 判读（**预先写死**）')
    print('  · 若 stdout **与** series.csv 都没有逐行的温度/驱动力 ⇒')
    print('    ⇒ **判据⑪ 后半句「日志里必须能看到 df 随时间变化」= ❌ 未取证**')
    print('       （不许用"代码里 `set_T` 每步都在调"来替代 —— goal 明说"不许只看代码"）')
    print('  · 修正路径（保守、可回退）：给 `_bk_exp.py` 加一个**默认关**的')
    print('    `--log-df 1`，把每步的 `T` 与 `df`（或 `Δf`）打进 stdout / series；')
    print('    **不改任何数值路径**，然后重跑一个短程取证。')
    print('=' * 96)


if __name__ == '__main__':
    main()
