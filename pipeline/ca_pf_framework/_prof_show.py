#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_prof_show.py --- 打印 `_prof.out` 的 top-N（按 tottime 与 cumtime 各一遍）"""
import pstats
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
p = pstats.Stats('_prof.out')
print('=' * 100)
print('按 **tottime**（自身耗时，不含子调用）')
print('=' * 100)
p.sort_stats('tottime').print_stats(n)
print('=' * 100)
print('按 **cumtime**（含子调用）')
print('=' * 100)
p.sort_stats('cumtime').print_stats(n)
