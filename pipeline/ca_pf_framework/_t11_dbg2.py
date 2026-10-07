#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbg2.py —— 直接打印 `_t11_C1_facets.fibonacci_sphere` 的真实输出形状。"""
import importlib.util
import sys
import numpy as np

spec = importlib.util.spec_from_file_location(
    "c1", "/mnt/f/speed_up/pipeline/ca_pf_framework/_t11_C1_facets.py")
mod = importlib.util.module_from_spec(spec)
# 只导入函数，不跑主程序：把 __name__ 设为非 __main__
src = open(spec.origin, encoding="utf-8").read()
src = src.split("M = 20000")[0]          # 截掉主程序
g = {}
exec(compile(src, spec.origin, "exec"), g)
f = g["fibonacci_sphere"]
for M in (10, 20000):
    a = f(M)
    print("M=%-6d  shape=%s  dtype=%s" % (M, a.shape, a.dtype))
    if a.ndim == 3:
        print("   ⚠ 3 维！第一轴=%d 第二轴=%d 第三轴=%d" % a.shape)
