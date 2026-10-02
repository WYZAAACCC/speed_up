#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_athseq.py --- 解掉 R41 登记的**数字不自洽**（`成功+被拒 = 25 ≠ 累计 21`）。

## 症状
`p2_b5`：`成功=11`（`athermal 形核`）+ `被拒=14`（`被引擎拒`）= **25**，
而日志里最后一个 `累计 %d/%d` 的分子是 **21**。

## 假设（**可证伪**）
`_bk_exp.py` 两条分支**都**用 `n_ath_tgt` 编号（`:2129` 成功 / `:2135` 被拒）：
* **H-同步**：两条分支的 `#N` 序号连起来**无重复、无跳号** ⇒ 最后一个是 25 ⇒
  「21」是我**读错了行**（读到了较早的一行）；
* **H-不同步**：序号有重复或跳号 ⇒ **真有 bug**（两个计数器不同源）。

## 判据（**预先写死**）
* 把**两条分支的 `#N` 全抽出来排序**，看：
  ① 是否有重复；② 最大值是多少；③ 缺哪些号。
"""
import os
import re
import sys

TAGS = sys.argv[1:] or ['p2_b5', 'p2_b3']


def main():
    print('=' * 96)
    print('R581 —— 解 `成功+被拒` 与 `累计` 的不自洽（`n_ath_tgt` 编号序列）')
    print('=' * 96)
    for tag in TAGS:
        f = '_w2_r581_p2_%s.log' % tag
        if not os.path.exists(f):
            cand = [x for x in os.listdir('.') if x.endswith('.log') and tag in x]
            f = cand[0] if cand else None
        print()
        print('#' * 96)
        print('# %s   ← %s' % (tag, f))
        print('#' * 96)
        if not f or not os.path.exists(f):
            print('  ❌ 无日志'); continue
        txt = open(f, encoding='utf-8', errors='replace').read()
        lines = txt.split('\n')
        ok, rej, cum = [], [], []
        for ln in lines:
            m = re.search(r'athermal 事件 #(\d+) 被引擎拒', ln)
            if m:
                rej.append(int(m.group(1))); continue
            m = re.search(r'athermal 形核.*?（累计 (\d+)/(\d+);?', ln)
            if not m:
                m = re.search(r'athermal 形核.*?（累计 (\d+)/(\d+)', ln)
            if m:
                ok.append(int(m.group(1))); cum.append((int(m.group(1)), int(m.group(2))))
        print('  成功事件的 `累计` 分子序列：%s' % ok)
        print('  被拒事件的 `#N` 序列　　　：%s' % rej)
        alln = ok + rej
        print()
        print('  ① 成功 %d 个 + 被拒 %d 个 = **%d**' % (len(ok), len(rej), len(alln)))
        if cum:
            print('  ② 日志里 `累计` 分母（=`_n_law`）：%s ⇒ %s'
                  % (sorted(set(d for _, d in cum)),
                     '**常数** ✅' if len(set(d for _, d in cum)) == 1 else '⚠ 不是常数'))
        if alln:
            u = sorted(set(alln))
            dup = len(alln) - len(u)
            missing = [i for i in range(min(u), max(u) + 1) if i not in set(u)]
            print('  ③ 编号：min=%d **max=%d**；**重复 %d 个**；缺号 %s'
                  % (min(u), max(u), dup, missing if missing else '（无）'))
            print()
            if dup == 0 and not missing:
                print('  ⇒ **H-同步**：两条分支的编号**连续无重复** ⇒ 同一个计数器 ✅')
                print('     真实事件总数 = **%d**（不是我先前算的 %d，也不是 %d）'
                      % (max(u), len(alln), max(ok) if ok else -1))
                print('     ⇒ **R41 的「25 ≠ 21」是我把「11+14」当成了事件总数** ——')
                print('       其实 `成功=11` 里**含重复编号**（同一事件多行）、或 `grep -c` 数的是**行数**;')
                print('       **以 `max(#N)` 为准**。')
            else:
                print('  ⇒ ⚠ **H-不同步**：有重复或缺号 ⇒ 需要查（两个计数器不同源）')
        print('  ── 原始行样本（各 3 条）──')
        for ln in [l for l in lines if '被引擎拒' in l][:3]:
            print('     %s' % ln.strip()[:110])
        for ln in [l for l in lines if 'athermal 形核' in l][:3]:
            print('     %s' % ln.strip()[:110])
    print()
    print('=' * 96)
    print('★ 判读（**预先写死**）：以 `max(#N)` 为事件总数；若两分支编号连续 ⇒ 同一计数器 ⇒ 无 bug')
    print('=' * 96)


if __name__ == '__main__':
    main()
