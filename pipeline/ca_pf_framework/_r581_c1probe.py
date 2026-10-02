#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c1probe.py --- 探针：`nuc_dbg.json` 里到底有什么键（C1 需要位点坐标做均匀性检验）。"""
import json
import os
import sys

import numpy as np

p = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_p2/dry_smoke_n160m4/nuc_dbg.json'
print('=' * 92)
print('探针：%s（%d 字节）' % (p, os.path.getsize(p)))
print('=' * 92)
d = json.load(open(p, encoding='utf-8'))
print('顶层键 %d 个：' % len(d))
for k, v in d.items():
    if isinstance(v, dict):
        print('  %-24s dict(%d)：%s' % (k, len(v), list(v.keys())[:8]))
    elif isinstance(v, list):
        print('  %-24s list(%d)：%s' % (k, len(v), v[:4]))
    else:
        print('  %-24s %r' % (k, v))
