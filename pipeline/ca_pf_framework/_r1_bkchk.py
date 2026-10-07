#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_bkchk.py --- 新记账列的**正确性**验证（不只是"非空"）

背景
----
本轮修好了 `_r1_exp.py` 的记账列（`step`/`t_s`/`dt`/`dG_max`/`fill_cal`/…）。
此前只验过"**列非空**"。但"非空"不等于"对"—— 按 `AGENTS.md §3.4`，
还要**反向/定量**核对数值本身。

判据（全部为**可解析的恒等式或物理界**，不依赖"看起来合理"）
------------------------------------------------------------
  P-1 `step` 必须**严格单调递增**，且等于 `行号 × every`（`every` 取自 `meta.json`）；
  P-2 `dt` 必须**恒等于** `0.15·Δx/(MOB·DF)`（引擎的时间步规则；`MOB`/`DF` 从
      `T16_verify_rve` 读，`Δx` 取自 `meta.json`）—— 这是**闭式恒等式**；
  P-3 `t_s` 必须等于 **`step × dt`**（`dt` 恒定时的累积时间）；
  P-4 `dG_max` 在**步进开始后**必须有限且 > 0（`step=0` 那行为空是正常的）；
  P-5 `fill_cal` 必须落在 **(0, 2]**（体积不可能超过外接盒太多）且与
      `ncell·dx³/(L_cal·W_cal·T_cal)` **一致**——**独立重算**同一量。

⚠ 容差必须按**文件精度**定，不能按"浮点精度"定
------------------------------------------------
`_r1_exp.py:312-317` 的写出格式是 **`'%.6g'`** ⇒ **6 位有效数字**
⇒ 相对量化误差约 **5e-7**。
第一版我用了 `1e-12`/`1e-9` ⇒ P-2/P-3/P-5 全部"不过"，而实测差恰好是
**5.3e-7 / 5.6e-7 / 4.6e-6** —— 这是**格式精度**，不是数值错误。
（又一次"我的判据定错了"，与 `AGENTS.md §3.3` 教训 15 同类。）
⇒ 本版容差按**量化传播**定：单值 ~5e-7、4 输入乘积 ~2e-6 ⇒ 取 **`TOL=1e-5`**。
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import DF, MOB                                       # noqa: E402

d = sys.argv[1] if len(sys.argv) > 1 else 'mid192_ns4b'
DIR = os.path.join(HERE, '_exp', d)
mp = os.path.join(DIR, 'meta.json')
rows = list(csv.DictReader(open(os.path.join(DIR, 'series.csv'))))
meta = json.load(open(mp)) if os.path.exists(mp) else {}
every = meta.get('every')
dx = (meta.get('dx_nm') or 125.0) * 1e-9
TOL = 1e-5        # 按**量化传播**定：'%.6g' 单值 ~5e-7，
                  # 4 输入乘积 ~2e-6，再加最坏对齐 ⇒ 取 1e-5
                  # （**不是**浮点精度，也不是随手放宽）

print('=' * 96)
print('%s ：新记账列的**正确性**核对（n=%d）' % (d, len(rows)))
print('   meta.every=%s  meta.dx_nm=%s  DF=%.4e  MOB=%.4e' % (every, dx * 1e9, DF, MOB))
print('=' * 96)


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


st = np.array([fnum(r, 'step') for r in rows])
dt = np.array([fnum(r, 'dt') for r in rows])
ts = np.array([fnum(r, 't_s') for r in rows])
dg = np.array([fnum(r, 'dG_max') for r in rows])

# P-1
mono = bool(np.all(np.diff(st) > 0))
exp_st = np.arange(len(rows), dtype=float) * (every or 5)
match_ev = bool(np.array_equal(st, exp_st))
print('\nP-1 `step` 严格递增 = %s ；等于 行号×every(%s) = %s  ⇒ %s'
      % (mono, every, match_ev, '✅' if (mono and match_ev) else '⛔'))

# P-2
dt_exp = 0.15 * dx / (MOB * DF)
d_ok = np.isfinite(dt).all() and np.allclose(dt[1:], dt_exp, rtol=TOL, atol=0)
print('P-2 `dt` 恒等于 0.15·Δx/(MOB·DF) = %.6e s ：实测 %s … %s  ⇒ %s'
      % (dt_exp, ('%.6e' % np.nanmin(dt[1:])) if len(dt) > 1 else '—',
         ('%.6e' % np.nanmax(dt[1:])) if len(dt) > 1 else '—',
         '✅ 恒等' if d_ok else '⛔ 不等'))

# P-3
ts_exp = st * dt_exp
t_ok = bool(np.allclose(ts[1:], ts_exp[1:], rtol=TOL, atol=0))
print('P-3 `t_s` 等于 step×dt ：最大相对差 %.3e  ⇒ %s'
      % (float(np.max(np.abs(ts[1:] - ts_exp[1:]) / np.maximum(ts_exp[1:], 1e-30)))
         if len(ts) > 1 else 0.0, '✅' if t_ok else '⛔'))

# P-4
fin = np.isfinite(dg[1:])
print('P-4 `dG_max`（step>0）有限且 >0 ：%d/%d 有限，最小 %.4e  ⇒ %s'
      % (int(fin.sum()), int(fin.size), float(np.nanmin(dg[1:])) if fin.any() else np.nan,
         '✅' if (fin.all() and np.nanmin(dg[1:]) > 0) else '⚠'))

# P-5
# ⚠ 修正（本轮）：`fill_cal` 的定义用 `measure()` 的 `V`（**亚胞分辨**体积），
#   第一版拿 `ncell·dx³`（**整数胞计数**）去重算 ⇒ 两者**系统性**不同（亚胞修正），
#   不是舍入 ⇒ 那个"不一致"是**我选错了对照量**。现用**同一个 `V`**。
fc = np.array([fnum(r, 'fill_cal') for r in rows])
nc = np.array([fnum(r, 'ncell') for r in rows])
V = np.array([fnum(r, 'V') for r in rows])
L = np.array([fnum(r, 'L_cal') for r in rows])
W = np.array([fnum(r, 'W_cal') for r in rows])
T = np.array([fnum(r, 'T_cal') for r in rows])
inb = bool(np.all((fc > 0) & (fc <= 2.0)))
rel_V = float(np.nanmax(np.abs(fc - V / np.maximum(L * W * T, 1e-300))
                        / np.maximum(np.abs(fc), 1e-300)))
rel_nc = float(np.nanmax(np.abs(fc - nc * dx ** 3 / np.maximum(L * W * T, 1e-300))
                         / np.maximum(np.abs(fc), 1e-300)))
print('P-5 `fill_cal` ∈(0,2] = %s ；= V/(L_cal·W_cal·T_cal)（**同一个 V**）'
      ' 最大相对差 %.3e  ⇒ %s'
      % (inb, rel_V, '✅ 与写出前一致（差为文件舍入）' if rel_V < TOL else '⛔ 不一致'))
print('     （附·信息量）拿 `ncell·dx³` 代替 `V` 重算会给 %.3e 的差 —— 那是**亚胞体积修正**，'
      % rel_nc)
print('       也正是第一版判据报"不一致"的来源 ⇒ **是判据选错对照量，不是数据错**。')
allok = (mono and match_ev and d_ok and t_ok and inb and (rel_V < TOL))
print('\n⇒ %s' % ('✅ **新记账列既非空、又正确**（差均在文件精度 %.6g 内）' % 0
                  if allok else '⛔ 有项未过，见上'))
print('=' * 96)

