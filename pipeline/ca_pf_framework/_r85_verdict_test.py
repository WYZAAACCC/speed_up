#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r85_verdict_test.py —— **判决层的单元测试**（`_bk_exp._blk_verdict`）。

## 为什么必须单独测

判决行**一次长跑只执行一次**（在最后）。它出错的话：
  * CSV 已经写完 ⇒ `_r30_regress.sh` 的**逐位比较仍然 PASS**；
  * `_bk_exp.py` 也不会非零退出（异常被上层吞掉或只留一行 Traceback）；
  * ⇒ **只有翻日志才发现**。

【实测】R76 第一版就是这么炸的：
```
File ".../_bk_exp.py", line 1442, in _blk_verdict
    have_new = ('blk_nprof' in s and s['blk_nprof']
ValueError: The truth value of an array with more than one element is ambiguous
```
根因：`read_series()` 返回 **`{列: np.ndarray}`**，而我对数组做了真值判断。
⇒ **T9 就是复刻这个 bug**（回归用例必须先失败过，见 `AGENTS.md §3.4`）。

## 用法

    python _r85_verdict_test.py      # 期望 FAIL = 0
"""
from __future__ import annotations

import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_exp as BX                                        # noqa: E402

F = []
OUT = []


def ck(tag, ok, det=''):
    print('  %-62s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def _a(v):
    return np.asarray(v)


def series(**kw):
    """造一个**与 `read_series` 同型**的表：`{列: np.ndarray}`。"""
    return {k: _a(v) for k, v in kw.items()}


class A:
    multi_block = False
    arm = 'dry'


def call(s, M=6, multi=False):
    """跑一次 `_blk_verdict`，把打印内容收进 `OUT`。"""
    OUT.clear()
    a = A()
    a.multi_block = multi
    BX._blk_verdict(s, M, a, lambda *x: OUT.append(' '.join(str(y) for y in x)))
    return '\n'.join(OUT)


def main():
    print('=' * 100)
    print('_r85_verdict_test —— `_blk_verdict` 的单元测试（判决行只在长跑末尾跑一次）')
    print('=' * 100)

    # ---- T1/T2 单块（走原判据，**必须逐字保持**）----
    s1 = series(nslab_n=[3, 3], nf3_col=[2, 2], nblk_sig=[1, 1])
    o = call(s1, M=3, multi=False)
    ck('T1 单块 nslab_n==M 且 nf3_col==M-1 ⇒ 原判据打 ✓', '✓' in o, o.splitlines()[-1][:60])
    ck('T1b 单块**不**打印多块告警（不误报）', '多块构型' not in o)
    s2 = series(nslab_n=[3, 1], nf3_col=[2, 0], nblk_sig=[1, 1])
    o = call(s2, M=3, multi=False)
    ck('T2 单块判据不满足 ⇒ ✗', '✗' in o)

    # ---- T3~T5 多块（走逐块判据）----
    s3 = series(nslab_n=[1, 1], nf3_col=[0, 0], nblk_sig=[2, 2],
                blk_laths=['3/3', '3/3'], blk_nprof=['3/3', '3/3'],
                blk_nruns=['3/3', '3/3'], blk_nlath=['3/3', '3/3'],
                blk_vars=['1/3', '1/3'])
    o = call(s3, M=6, multi=True)
    ck('T3 多块 blk_nprof==blk_laths 且 nruns==nprof ⇒ ✓', '✓' in o and '✗' not in o,
       o.splitlines()[-1][:70])
    ck('T3b 多块**显式声明**全局 nslab_n 不作判据',
       '结构性无效' in o and '不作判据' in o)
    s4 = series(nslab_n=[1, 1], nf3_col=[0, 0], nblk_sig=[2, 2],
                blk_laths=['3/3', '3/3'], blk_nprof=['3/1', '3/2'],
                blk_nruns=['3/1', '3/1'], blk_nlath=['3/3', '3/3'],
                blk_vars=['1/3', '1/3'])
    o = call(s4, M=6, multi=True)
    ck('T4 多块 blk_nprof != blk_laths ⇒ ✗', '✗' in o, o.splitlines()[-1][:70])
    s5 = series(nslab_n=[1, 1], nf3_col=[0, 0], nblk_sig=[2, 2],
                blk_laths=['3/3', '3/3'], blk_nprof=['3/3', '3/3'],
                blk_nruns=['3/3', '3/6'], blk_nlath=['3/3', '3/3'])
    o = call(s5, M=6, multi=True)
    ck('T5 多块 nprof 对但**末行** nruns 有噪声 ⇒ 明示"剖面有噪声"',
       '有噪声' in o, o.splitlines()[-1][:70])

    # ---- T6 多块但没有新列（老算例）----
    s6 = series(nslab_n=[1, 1], nf3_col=[0, 0], nblk_sig=[2, 2],
                blk_laths=['3/3', '3/3'])
    o = call(s6, M=6, multi=True)
    ck('T6 多块但无 blk_nprof 列 ⇒ 指向离线重测（不静默走原判据）',
       '_r76_remeasure' in o, o.splitlines()[-1][:70])
    ck('T6b 多块且无新列 ⇒ **不给判据**（不得用无效口径打出 ✓/✗）',
       '不给判据' in o and '主判据：**nslab_n' not in o,
       '（否则就会重演 R75 把"通过"读成"失败"）')

    # ---- T7/T8 退化输入：不许抛 ----
    for tag, s, multi in (('T7 空数组', series(nslab_n=[], nf3_col=[], nblk_sig=[],
                                             blk_nprof=[], blk_laths=[]), True),
                          ('T8 缺列', series(nslab_n=[3]), False)):
        try:
            call(s, M=6, multi=multi)
            ck(tag + ' ⇒ 不抛异常', True)
        except Exception:
            ck(tag + ' ⇒ 不抛异常', False, traceback.format_exc().splitlines()[-1])

    # ---- T9 ★ 复刻 R76 第一版那个 bug（数组真值判断）----
    s9 = series(nslab_n=[1, 1], nf3_col=[0, 0], nblk_sig=[2, 2],
                blk_laths=['3/3', '3/3'], blk_nprof=['3/3', '3/3'],
                blk_nruns=['3/3', '3/3'], blk_nlath=['3/3', '3/3'])
    try:
        o = call(s9, M=6, multi=True)
        ck('T9 ★回归：ndarray 列**不再**触发 ambiguous ValueError', True,
           o.splitlines()[-1][:60])
    except ValueError as e:
        ck('T9 ★回归：ndarray 列**不再**触发 ambiguous ValueError', False, str(e))
    ck('T9b 那一列确实是 ndarray（复刻前提成立）',
       isinstance(s9['blk_nprof'], np.ndarray))

    print('-' * 100)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 100)
    return 1 if F else 0


if __name__ == '__main__':
    sys.exit(main())
