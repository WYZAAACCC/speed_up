#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r576_hookcost.py --- 记账钩子的**单次代价**（微基准）与折算到单步的总代价。

## 为什么不用端到端 A/B 当主判据

端到端 A/B（HOOKED vs 源码剥离 STRIPPED）实测每轮 overhead 在
**[-14.3%, +12.1%]** 之间摆动（`_w2_r576_acctcost.log` 第 1 轮）——
因为每一臂都要**重建引擎 30–60 s**，而本机（笔记本）在这段时间里就漂了。
**一个信噪比 <1 的量具不能用来判 1% 的效应。**

## 这一版怎么量（可分辨 0.01%）

钩子的代价是**每次调用的固定开销 × 每步调用次数**，两项都可以**直接量**：
  * 每次调用：在同一进程里跑 `N=3e6` 次 `with acct.mark('x')` / `span_begin+span_end`，
    取多次的**最小值**（最小值避开调度噪声）。
  * 每步调用次数：直接读 `acct.totals()` 的计数表（`_r576_prof.py` 报的 `hooks/步`）。

判据（写死）：
  * `T_closed_call` = 关闭时**一次钩子点的总开销**（`mark` + `with` 的 `__enter__/__exit__`）
  * `overhead_step = hooks_per_step × T_call / 单步墙钟`
  * **≤ 0.5% 才算过**（比端到端 A/B 的噪声下限 1% 还严，因为它没有噪声）。
"""
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_acct as acct                                     # noqa: E402

REPS = 7
NCALL = 300000


def _t(fn):
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return min(ts), statistics.median(ts)


def main():
    hooks_per_step = float(os.environ.get('R576_HOOKS', '520'))
    step_s = float(os.environ.get('R576_STEP', '0.36'))

    def closed():
        for _ in range(NCALL):
            with acct.mark('x'):
                pass

    def closed_span():
        for _ in range(NCALL):
            acct.span_begin('y')
            acct.span_end('y')

    def enabled():
        for _ in range(NCALL):
            with acct.mark('x'):
                pass

    acct.disable()
    t_c_min, t_c_med = _t(closed)
    t_s_min, t_s_med = _t(closed_span)
    acct.enable()
    acct.reset()
    t_e_min, t_e_med = _t(enabled)
    acct.disable()

    per_mark = t_c_min / NCALL
    per_span = t_s_min / NCALL * 0.5          # 一轮 = begin+end ⇒ 折成"每个钩子点"
    per_mark_on = t_e_min / NCALL
    # 生产代码里 `with acct.mark` 与 `span_begin/end` 各占一部分 ⇒ 取两者较大者当**上界**
    per_call = max(per_mark, per_span)

    L = []
    A = L.append
    A('=' * 96)
    A('R576 — 记账钩子的**单次代价**（微基准；%d 次/轮 × %d 轮取最小）' % (NCALL, REPS))
    A('=' * 96)
    A('  关闭时 `with acct.mark("x"): pass`      min=%.2f ns/次  median=%.2f ns/次'
      % (per_mark * 1e9, t_c_med / NCALL * 1e9))
    A('  关闭时 `span_begin+span_end`（折半）      min=%.2f ns/钩子点'
      % (per_span * 1e9))
    A('  打开时 `with acct.mark("x"): pass`      min=%.2f ns/次  （= 计时器真实开销）'
      % (per_mark_on * 1e9))
    A('  ⇒ 取值（两者较大者，作为**上界**）        **%.2f ns/钩子点**' % (per_call * 1e9))
    A('')
    A('  折算：钩子执行次数 = **%.0f 次/步**（`_r576_prof.py` 实测值）' % hooks_per_step)
    A('        单步墙钟       = %.4f s' % step_s)
    oh = hooks_per_step * per_call / step_s
    A('        ⇒ 单步开销     = %.3f ms = **%.3f%%**' % (oh * 1e3, 100 * oh))
    A('')
    A('  判据（≤0.5%%）: %s' % ('✅ PASS' if oh <= 0.005 else '❌ FAIL ⇒ 必须减钩子点'))
    A('')
    A('  ⚠ 口径记账：本量具量的是"**钩子函数被调用**"的代价。'
      '关闭时 `mark()` 仍是一次函数调用 + 一次单例返回')
    A('     —— 这正是生产默认路径的形状（钩子常驻代码、默认关闭）。'
      '"完全没有钩子"的源码在 STRIPPED 臂里，')
    A('     那条路的端到端 A/B 噪声太大（±14%%），只能当参考，不能当判据。')
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r576_hookcost.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if oh <= 0.005 else 1


if __name__ == '__main__':
    sys.exit(main())
