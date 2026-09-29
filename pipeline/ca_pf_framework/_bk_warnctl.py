#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_warnctl.py —— **"归档路径"提示的对照测试**（本项目硬规矩：守卫要反向测一次）。

一个只会在该响的时候响、不该响的时候也响的提示，是噪声；
一个永远不响的提示，等于没写。所以两边都测。

用例（`argv` 用 monkeypatch 控制，不真跑仿真）：
  W-1 正：`--grow-stack`（未传 `--nuc-law`）           ⇒ **应提示**
  W-2 正：`--grow-stack --nuc-every 30`（走驱动层形核）  ⇒ **应提示**
  W-3 负：`--closed ...`                              ⇒ **不应提示**
  W-4 负：显式 `--nuc-law cadence`                    ⇒ **不应提示**（他知道自己在做什么）
  W-5 负：预摆算例（不生长、不形核）                     ⇒ **不应提示**
"""
import argparse
import io
import os
import sys
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _bk_exp as E                                             # noqa: E402


def _ns(**kw):
    base = dict(grow_stack=False, arm='dry', nuc_every=0, nuc_law='cadence',
                closed=False, eng_cadence=30, gamma0=0.15)
    base.update(kw)
    return argparse.Namespace(**base)


def _fire(ns, argv):
    old = sys.argv
    sys.argv = ['_bk_exp.py'] + argv
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            E._warn_archived_path(ns)
    finally:
        sys.argv = old
    return '你正在跑归档路径' in buf.getvalue()


CASES = [
    ('W-1 正：--grow-stack（未传 --nuc-law）', True,
     _ns(grow_stack=True), ['--grow-stack']),
    ('W-2 正：--grow-stack --nuc-every 30', True,
     _ns(grow_stack=True, nuc_every=30), ['--grow-stack', '--nuc-every', '30']),
    ('W-3 负：--closed', False,
     _ns(grow_stack=True, closed=True, nuc_law='athermal'),
     ['--closed', '--grow-stack']),
    ('W-4 负：显式 --nuc-law cadence', False,
     _ns(grow_stack=True), ['--grow-stack', '--nuc-law', 'cadence']),
    ('W-5 负：预摆算例（不生长不形核）', False,
     _ns(grow_stack=False, nuc_every=0), []),
]


def main():
    print('=' * 92)
    print('「归档路径」提示的对照测试（正 2 / 负 3）')
    print('=' * 92)
    bad = 0
    for name, want, ns, argv in CASES:
        got = _fire(ns, argv)
        ok = (got == want)
        if not ok:
            bad += 1
        print('  %-42s 期望=%-5s 实测=%-5s %s'
              % (name, want, got, 'OK' if ok else '**FAIL**'))
    print('-' * 92)
    print('  对照数 = %d   FAIL = %d' % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
