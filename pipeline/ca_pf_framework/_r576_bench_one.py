#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r576_bench_one.py --- **单臂**单步墙钟 + 钩子执行计数（供 `_r576_acct_cost.sh` 交错配对）。

## 两臂是什么，为什么这样设计

* 臂 **HOOKED**：正常导入（钩子代码在），`acct.enable()` 打开 ⇒ 既计时又计数。
* 臂 **STRIPPED**：在导入 `windowB_surface` / `windowB_par` / `windowB_pf3d` 之前装一个
  **元路径导入钩子**，把源码里的钩子点**在编译前**改写掉：
      `with acct.mark('x'):`  ->  `if True:`      （**不需要重排缩进**）
      `acct.span_begin('x')`  ->  `pass`
      `acct.span_end('x')`    ->  `pass`
      `acct.tick('x')` / `acct.bmem(...)` -> `pass`
  ⇒ STRIPPED 臂里**一次钩子调用都不发生**，这才是"完全没有钩子"的真基线。

## 为什么不做"关闭钩子"当基线

关闭时 `mark()` 仍会**被调用**（只是立刻返回单例）⇒ 基线里仍含那 3 次 Python 调用。
拿它当基线会把钩子代价**系统性低报**。这正是本仓库"量具必须先自证"的纪律：
**能不用近似就不用近似**。

## 判据（写死）

* 对每一轮 `r`：`overhead_r = t_hooked_r / t_stripped_r - 1`
* 交错 4 轮（A/B/A/B/…）取中位 ⇒ 报**区间**，不报单点。
* 硬判据：中位 overhead ≤ **1%** 才允许把记账版当"不引入性能回归"。
"""
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STRIP = os.environ.get('R576_STRIP', '0') == '1'

_TARGETS = ('windowB_surface', 'windowB_par', 'windowB_pf3d')

_R_CTX = re.compile(r'^(\s*)with (?:acct|_acct)\.(?:mark|mark_in|bcost)\([^)]*\):\s*$')
_R_STMT = re.compile(r'^(\s*)(?:acct|_acct)\.(?:span_begin|span_end|tick|bmem)\(.*\)\s*$')


def _strip_src(src):
    out = []
    n_ctx = n_stmt = 0
    for line in src.splitlines(True):
        m = _R_CTX.match(line)
        if m:
            out.append('%sif True:   # R576 stripped hook\n' % m.group(1))
            n_ctx += 1
            continue
        m = _R_STMT.match(line)
        if m:
            out.append('%spass       # R576 stripped hook\n' % m.group(1))
            n_stmt += 1
            continue
        out.append(line)
    return ''.join(out), n_ctx, n_stmt


if STRIP:
    import importlib.abc
    import importlib.machinery
    import importlib.util

    _STAT = {}

    class _StripLoader(importlib.abc.Loader):
        def __init__(self, name, path):
            self.name, self.path = name, path

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            with open(self.path, encoding='utf-8') as fh:
                src = fh.read()
            new, nc, ns = _strip_src(src)
            _STAT[self.name] = (nc, ns)
            code = compile(new, self.path, 'exec')
            exec(code, module.__dict__)

    class _StripFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name not in _TARGETS:
                return None
            p = os.path.join(HERE, name + '.py')
            if not os.path.exists(p):
                return None
            return importlib.util.spec_from_loader(
                name, _StripLoader(name, p), origin=p)

    sys.meta_path.insert(0, _StripFinder())

import numpy as np                                              # noqa: E402

import windowB_acct as acct                                     # noqa: E402
import _r561_opfacct as AC                                      # noqa: E402

N = int(os.environ.get('R576_N', '64'))
NV = int(os.environ.get('R576_NV', '24'))
WORK = int(os.environ.get('R576_WORKERS', '4'))
STEPS = int(os.environ.get('R576_STEPS', '4'))
os.environ['R561_N'] = str(N)
os.environ['R561_NV'] = str(NV)
os.environ['R561_WORKERS'] = str(WORK)
# `_r561_opfacct` 的模块级常量在 import 时就定了 ⇒ 必须**先**设环境变量再 import。
# （上面那行 import 已经发生了 —— 所以这里显式覆盖它读到的三个常量。）
AC.N, AC.NV, AC.WORKERS = N, NV, WORK


def main():
    if not STRIP:
        acct.enable()
    t0 = time.perf_counter()
    g = AC.build()
    t_build = time.perf_counter() - t0
    g.advance(dt=1e-8)                       # 预热（P0：走完 soft 路径）
    dt_ref = g.pf.phi.dtype
    acct.reset()
    ts = []
    for _ in range(STEPS):
        t0 = time.perf_counter()
        g.advance(dt=1e-8)
        ts.append(time.perf_counter() - t0)
    T, C = acct.totals()
    nhooks = sum(C.values())
    med = statistics.median(ts)
    print('ARM=%s N=%d NV=%d W=%d STEPS=%d' % ('STRIPPED' if STRIP else 'HOOKED',
                                               N, NV, WORK, STEPS))
    print('BUILD=%.4f' % t_build)
    print('MEDIAN=%.6f' % med)
    print('MIN=%.6f MAX=%.6f' % (min(ts), max(ts)))
    print('PFDTYPE=%s' % dt_ref)
    print('HOOKEXEC=%d' % nhooks)
    if STRIP:
        print('STRIPSTAT=%r' % (_STAT,))
    print('CORRUPT=%r' % (acct.corrupt(),))
    return 0


if __name__ == '__main__':
    sys.exit(main())
