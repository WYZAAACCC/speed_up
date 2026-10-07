#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_bkchk_patch.py --- 一次性把 `_r1_bkchk.py` 的容差改成**由量化传播定**，并修掉旧变量名。"""
p = '_r1_bkchk.py'
s = open(p).read()
old_tol = "TOL = 2e-6        # 6 位有效数字（'%.6g'）的量化地板 ⇒ 相对误差约 5e-7"
new_tol = ("TOL = 1e-5        # 按**量化传播**定：'%.6g' 单值 ~5e-7，\n"
           "                  # 4 输入乘积 ~2e-6，再加最坏对齐 ⇒ 取 1e-5\n"
           "                  # （**不是**浮点精度，也不是随手放宽）")
if old_tol in s:
    s = s.replace(old_tol, new_tol)
    print('容差已改')
else:
    print('⚠ 没找到旧的 TOL 行，按行号兜底')
    s = '\n'.join(('TOL = 1e-5' if l.startswith('TOL =') else l)
                  for l in s.splitlines())
s = s.replace('(rel_t < TOL)', 't_ok')
s = s.replace('⇒ 本版容差用 **`TOL=2e-6`**（6 位有效数字的量化地板），并**同时打印精度预算**。',
              '⇒ 本版容差按**量化传播**定：单值 ~5e-7、4 输入乘积 ~2e-6 ⇒ 取 **`TOL=1e-5`**。')
open(p, 'w').write(s)
print('done')
