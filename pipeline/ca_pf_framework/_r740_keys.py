#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r740_keys.py <root> <tag> —— **把 `nuc_dbg.json` 全部键打出来**（不做筛选）。

`_r739_dbg.py` 只打了 `dbg` 下的键；本脚本连 `nuc_cfg` 与顶层一起打，
用来回答"`stack` 通道为什么一次都没触发"。
"""
import json
import os
import sys

root, tag = sys.argv[1], sys.argv[2]
p = os.path.join(root, 'dry_%s' % tag, 'nuc_dbg.json')
print('=== %s ===' % p)
if not os.path.isfile(p):
    print('  ⚠ 不存在')
    sys.exit(1)
with open(p) as f:
    d = json.load(f)


def dump(prefix, obj, depth=0):
    if isinstance(obj, dict):
        for k in sorted(obj, key=str):
            v = obj[k]
            if isinstance(v, dict) and depth < 2:
                print('%s%s:' % ('  ' * (depth + 1), k))
                dump(prefix + '.' + str(k), v, depth + 1)
            else:
                s = repr(v)
                print('%s%-28s = %s' % ('  ' * (depth + 1), str(k), s[:90]))
    else:
        print('%s%s' % ('  ' * (depth + 1), repr(obj)[:120]))


for top in sorted(d, key=str):
    v = d[top]
    if isinstance(v, dict):
        print('%s:' % top)
        dump(top, v)
    else:
        print('%-28s = %s' % (top, repr(v)[:100]))
