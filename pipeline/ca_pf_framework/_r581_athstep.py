#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_athstep.py --- ★★★ 按 **step** 分档统计形核事件（**同 step 才可比**）。

## 为什么要这个
R43 发现一件很可疑的事：**修复臂（`p2_b5ov`/`p2_b5ps`，都是 B=5）的形核编号序列
与 `p2_b3`（B=3）逐位相同**（成功 `[2,3,4,11,12]`、被拒 `[5..10,13,14,15]`、max `#15`），
而**和 `p2_b5`（B=5）不同**（max `#25`）。

⇒ 两个可能：
* **H-step**：只是**采样 step 不同**（修复臂在 ~step 300，`p2_b5` 跑到 600）⇒ 无可比性；
* **H-sched**：**事件排程由准静态温度梯级决定**（5 档 × 100 步），与 `B` 无关
  ⇒ 同 step 下**本来就该一样**，`p2_b5` 多出来的事件是**后段**才发生的。

## 判据（**预先写死**）
把每个臂的**每个事件**按 `@ step N` 归档，算：
* **每档（step 1/101/201/301/401）的成功数、被拒数、拒绝率**；
* **同档之间**才比。
* 若 `p2_b5ov`/`p2_b5ps` 在**每一档**上都与 `p2_b5` 相同 ⇒ H-step（只是没跑到）；
  若在**有数据的档上**就不同 ⇒ H-sched 被否，S4/N13 真的改变了形核行为。
"""
import os
import re
import sys
from collections import defaultdict

TAGS = sys.argv[1:] or ['p2_b5', 'p2_b3', 'p2_b5ov', 'p2_b5ps']


def log_of(tag):
    f = '_w2_r581_p2_%s.log' % tag
    if os.path.exists(f):
        return f
    cand = [x for x in os.listdir('.') if x.endswith('.log') and tag in x]
    return cand[0] if cand else None


def main():
    print('=' * 104)
    print('R581 —— 形核事件**按 step 分档**（同 step 才可比）')
    print('=' * 104)
    data = {}
    for tag in TAGS:
        f = log_of(tag)
        if not f or not os.path.exists(f):
            print('  %-9s ❌ 无日志' % tag); continue
        txt = open(f, encoding='utf-8', errors='replace').read()
        ok = defaultdict(int); rej = defaultdict(int); modes = defaultdict(int)
        last_step = 0
        for ln in txt.split('\n'):
            m = re.search(r'被引擎拒.*?@ step (\d+)', ln)
            if m:
                rej[int(m.group(1))] += 1
                last_step = max(last_step, int(m.group(1)))
                continue
            # ★ 只认**事件行**：必须以 `★ **athermal 形核** @ step` 开头，
            #   排除横幅 `athermal 形核律`（R42 的 grep 坑）
            m = re.search(r'\*\*athermal 形核\*\* @ step (\d+)', ln)
            if m:
                ok[int(m.group(1))] += 1
                last_step = max(last_step, int(m.group(1)))
                mm = re.search(r'模式 \*\*(\w+)\*\*', ln)
                if mm:
                    modes[mm.group(1)] += 1
        data[tag] = (ok, rej, modes, last_step)
    # ── 表 ──
    steps = sorted(set(s for ok, rej, _, _ in data.values() for s in list(ok) + list(rej)))
    print()
    print(' %-9s %-8s' % ('臂', '末step') + ''.join('%14s' % ('@step %d' % s) for s in steps))
    print(' ' + '-' * 100)
    for tag, (ok, rej, modes, ls) in data.items():
        row = ' %-9s %-8d' % (tag, ls)
        for s in steps:
            o, r = ok.get(s, 0), rej.get(s, 0)
            tot = o + r
            row += '%14s' % (('%d/%d' % (o, tot)) if tot else '·')
        print(row)
    print('   （单元格 = **成功/合计**；`·` = 该档没有事件）')
    print()
    print(' %-9s %-8s' % ('臂', '总') + ''.join('%14s' % ('拒绝率@%d' % s) for s in steps))
    print(' ' + '-' * 100)
    for tag, (ok, rej, modes, ls) in data.items():
        row = ' %-9s %-8d' % (tag, sum(ok.values()) + sum(rej.values()))
        for s in steps:
            o, r = ok.get(s, 0), rej.get(s, 0)
            tot = o + r
            row += '%14s' % (('%.1f%%' % (100.0 * r / tot)) if tot else '·')
        print(row)
    print()
    print(' %-9s 模式分布：%s' % ('臂', 'attach / fresh / stack'))
    for tag, (ok, rej, modes, ls) in data.items():
        print('   %-9s attach=%-3d fresh=%-3d stack=%-3d'
              % (tag, modes.get('attach', 0), modes.get('fresh', 0), modes.get('stack', 0)))
    print()
    print('=' * 104)
    print('★ 判读（**预先写死**）')
    print('  · **只在有共同事件的档上比**；`·` 的档不算。')
    print('  · 若修复臂在每个共同档上都与 `p2_b5` 相同 ⇒ **H-step**（只是没跑到）⇒ 判决要等跑完。')
    print('  · 若在共同档上就不同 ⇒ **S4/N13 真的改变了形核行为**。')
    print('=' * 104)


if __name__ == '__main__':
    main()
