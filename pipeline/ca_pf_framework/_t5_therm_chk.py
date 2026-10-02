#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_therm_chk.py --- 适配层 `lpbf_like_linear` 的自检（**签名与 `linear_cool` 一致**）"""
import sys

sys.path.insert(0, '.')
from _t5_therm import check_assertions, lpbf_like_linear      # noqa: E402

# 用**引擎实际会传的三参数**（`t5H3` 启动横幅里的：T_start=849.04 K、T_end=298、t_cool=2.3425e-4）
f = lpbf_like_linear(849.04, 298.0, 2.3425e-04)
print('=' * 88)
print('适配层自检：`lpbf_like_linear(T_start, T_end, t_cool)`')
print('=' * 88)
print('  签名兼容（调用点读的 4 个属性）：')
print('     T_start = %.2f   T_end = %.1f   t_cool = %.4g   band = %s'
      % (f.T_start, f.T_end, f.t_cool, f.band))
print('  可调用 = %s    纯函数 = %s' % (callable(f), f(0.001) == f(0.001)))
print('  映射记账：')
for k, v in f.mapping_note.items():
    print('     %-18s = %s' % (k, v))
print()
check_assertions(f, verbose=False)
print('  ✅ 适配层的两条断言也 PASS（与 `lpbf_thermal` 同）')
print('  ⚠ **仍未做门 0/门 4 回归** ⇒ 不得在长跑上启用（复核清单第 6 条）')
print('=' * 88)
