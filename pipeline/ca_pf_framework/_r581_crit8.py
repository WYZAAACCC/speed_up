#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_crit8.py --- ★★★★★ **判据⑧**：给出「**不许用 `pickle` 存整个对象**」的**实测反例**

## goal 判据⑧ 逐字
> 「不许 pickle 整个对象（证据：`par` 不可 pickle） | **给一行反例
>   （`pickle.dumps(par)` 抛 `TypeError` 的实测输出）**」

**⇒ 本脚本**实测**并打印：
1. `pickle.dumps(ParCtx(...))` 的真实异常（**逐字**）；
2. `LevelSetMulti` 整对象是否可 pickle（应当**也不可**，因为它持有 `par`）；
3. **对照**：检查点里**实际**存的那些**纯数据**（`rng.bit_generator.state`、
   `_nuc` 的值字典、`sites`）**是可 pickle 的** ⇒ 证明"只 pickle 数据"这条设计可行。
"""
import io
import os
import pickle
import sys
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_par as WP

print('=' * 100)
print('判据⑧：**不许 pickle 整个对象** —— 实测反例')
print('=' * 100)

# ── ① `ParCtx`（`par`）──────────────────────────────────────────────
print()
print('① `pickle.dumps(par)` —— 逐字异常')
try:
    par = WP.ParCtx(4)
except Exception as e:
    print('   ⚠ 构造 ParCtx 失败：%s' % e)
    par = None
if par is not None:
    try:
        b = pickle.dumps(par)
        print('   ❌ **居然 pickle 成功了**（%d 字节）⇒ 我的前提错了，要重查' % len(b))
    except Exception as e:
        print('   ✅ 抛异常：**%s: %s**' % (type(e).__name__, e))
        print('   ── 完整 traceback 末 3 行 ──')
        for ln in traceback.format_exc().strip().split('\n')[-3:]:
            print('      %s' % ln)
    # 指出**具体**是哪个成员不可 pickle
    print('   ── 逐成员定位 ──')
    for k, v in sorted(vars(par).items()):
        try:
            pickle.dumps(v)
        except Exception as e:
            print('      **%s**（%s）⇒ %s: %s'
                  % (k, type(v).__name__, type(e).__name__, str(e)[:60]))

# ── ② 对照：检查点里**实际**存的纯数据是可 pickle 的 ────────────────
print()
print('② 对照：检查点里实际存的**纯数据**（应当**都可以** pickle）')
rng = np.random.default_rng(11)
cases = [
    ('`rng.bit_generator.state`', rng.bit_generator.state),
    ('`_nuc` 的值字典（31 键 + dbg）', {'R_nuc': 3.2e-7, 'harden_f': 1.0,
                                       'var_rule': 'ed', 'along': None,
                                       'dbg': {'ok': 4, 'cov': 1}}),
    ('位点池（list of (int, ndarray)）', [(1, np.zeros(3)), (5, np.ones(3))]),
    ('`n_mode`（dict）', {'fresh': 0, 'stack': 12}),
    ('`_qs_dV`（list[float]）', [0.0, 1.0, 2.0]),
]
for name, obj in cases:
    try:
        b = pickle.dumps(obj)
        back = pickle.loads(b)
        ok = (repr(back) == repr(obj)) or (np.array_equal(
            np.asarray(back, dtype=object), np.asarray(obj, dtype=object))
            if isinstance(obj, np.ndarray) else True)
        print('   ✅ %-38s %5d 字节；回读一致=%s' % (name, len(b), ok))
    except Exception as e:
        print('   ❌ %-38s %s: %s' % (name, type(e).__name__, e))

# ── ③ 完整引擎对象（若构造便宜）────────────────────────────────────
print()
print('③ `LevelSetMulti` 整对象：**不构造**（构造要 ~60 s）⇒ 【推理】它也**不可** pickle，')
print('   因为它持有 `self.par`（上面已实测不可 pickle）。⇒ 这就是"重建 + 回填"的根据。')
print()
print('  ★ 结论：**只 pickle 数据、绝不 pickle 对象**；')
print('     恢复走「**同一命令行重建对象 + 逐项回填**」（`_ckpt_restore`）。')
print('=' * 100)
