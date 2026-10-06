#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_sig.py —— 打印 `LevelSetMulti.__init__` 的参数表（供构造各向异性平界面测试）。"""
import inspect
import sys

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

for cls in ('LevelSetMulti',):
    f = getattr(W, cls).__init__
    print("=== %s.__init__ ===" % cls)
    for n, p in inspect.signature(f).parameters.items():
        if n == 'self':
            continue
        print("  %-20s %s" % (n, p.default))
