#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c3why.py --- ★★★ 为什么 `p2_b5` 的 C3 掉到 81/121，而 `p2_b3` 是 121/121？

## 背景
`nf3_col == nslab_n − 1` 是 C3 的量化形式。末态：
`p2_b5` **81/121**（67%）❌ ／ `p2_b3` **121/121**（100%）✅。
两臂**碎屑数几乎相同**（17 vs 16，见 `_r581_speck.py`）⇒ **不是碎屑造成的**。

## 本轮要回答的
**逐行**看 `series.csv`：
1. **不成立的行长什么样**？是 `nf3_col < nslab_n−1` 还是 `>`？
2. **是不是集中在某些步**（比如某个形核事件之后）？
3. **与 `nslab_n` 的变化同步吗**？（掉队是"新增了板条但 F3 没跟上"还是"F3 分裂了"？）
4. 与 `nf2`（异变体接触）、`runs`（柱剖面连续段数）有没有同步变化？

## 判据（**预先写死**）
* **若** 不成立的行全都满足 `nf3_col == nslab_n − 2`（恰好差 1）
  ⇒ 是**一根新板条长出但还没和块形成 F3 接触**（**滞后**，不是断裂）。
* **若** 差 ≥2 或出现 `nf3_col > nslab_n − 1`
  ⇒ 是**结构性**问题（板条被切断或 F3 被重复计数）。
"""
import os
import re
import sys

import numpy as np


def load(tag):
    p = os.path.join('_exp/_bk_p2', 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return np.genfromtxt(p, delimiter=',', names=True)


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    print('=' * 100)
    print('R581 —— C3：`nf3_col == nslab_n − 1` 为什么在 b5 上掉队？')
    print('=' * 100)
    for t in tags:
        d = load(t)
        if d is None:
            print('★ %s：没有 series.csv' % t); continue
        ns = np.atleast_1d(d['nslab_n']).astype(float)
        nf = np.atleast_1d(d['nf3_col']).astype(float)
        st = np.atleast_1d(d['step']).astype(int) if 'step' in d.dtype.names \
            else np.arange(len(ns))
        print()
        print('★ %s  共 %d 行' % (t, len(ns)))
        print('   末值：nslab_n=%g  nf3_col=%g' % (ns[-1], nf[-1]))
        diff = nf - (ns - 1)
        ok = (diff == 0)
        print('   `nf3_col − (nslab_n−1)` 的分布：')
        for v in np.unique(diff):
            n = int((diff == v).sum())
            print('      差 %+g ： %4d 行（%.1f%%）%s' % (v, n, 100.0 * n / len(diff),
                                                        '  ← 成立' if v == 0 else ''))
        print('   ⇒ 成立 %d/%d = %.1f%%' % (ok.sum(), len(diff), 100.0 * ok.mean()))
        # 什么时候开始掉的
        first_bad = None
        for i in range(len(diff)):
            if diff[i] != 0:
                first_bad = i; break
        if first_bad is None:
            print('   ⇒ ✅ **全程成立，没有掉队**')
        else:
            print('   ⇒ 第一次掉队在**第 %d 行**（step=%s）' % (first_bad, st[first_bad]))
            print('     掉队前后 6 行（step / nslab_n / nf3_col / 差 / nf2 / runs）：')
            keys = ['step', 'nslab_n', 'nf3_col', 'nf2', 'runs']
            keys = [k for k in keys if k in d.dtype.names]
            print('     ' + ' '.join('%-9s' % k for k in keys) + ' 差')
            lo = max(0, first_bad - 3); hi = min(len(ns), first_bad + 4)
            for i in range(lo, hi):
                vals = ' '.join('%-9g' % np.atleast_1d(d[k])[i] for k in keys)
                mark = '  ← **掉队**' if diff[i] != 0 else ''
                print('     %s %+g%s' % (vals, diff[i], mark))
            # 掉队段
            bad = np.flatnonzero(diff != 0)
            # 连续段
            segs = []
            s0 = bad[0]; prev = bad[0]
            for b in bad[1:]:
                if b == prev + 1:
                    prev = b
                else:
                    segs.append((s0, prev)); s0 = b; prev = b
            segs.append((s0, prev))
            print('   ⇒ 掉队段共 %d 段（最长 %d 行）' % (len(segs), max(e - s + 1 for s, e in segs)))
            print('     前 6 段（行区间 / step 区间 / 差的范围）：')
            for s, e in segs[:6]:
                dd = diff[s:e + 1]
                print('      行 %4d–%-4d  step %5s–%-5s  差 %+g…%+g'
                      % (s, e, st[s], st[e], dd.min(), dd.max()))
        # 与其它列的相关性（谁跟它同步）
        if 'nf2' in d.dtype.names:
            nf2 = np.atleast_1d(d['nf2']).astype(float)
            print('   nf2：起点 %g → 末值 %g；**掉队行**的 nf2 中位 %.1f vs **成立行** %.1f'
                  % (nf2[0], nf2[-1],
                     np.median(nf2[diff != 0]) if (diff != 0).any() else float('nan'),
                     np.median(nf2[diff == 0]) if (diff == 0).any() else float('nan')))
    print()
    print('=' * 100)
    print('★ 判读（**预先写死**）')
    print('   · 若差恒为 −1 ⇒ **滞后**（新板条还没形成 F3 接触），不是断裂')
    print('   · 若差 ≤ −2 或 > 0 ⇒ **结构性**问题（板条切断 / F3 重计）')
    print('=' * 100)


if __name__ == '__main__':
    main()
