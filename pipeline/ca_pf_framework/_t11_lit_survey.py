#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_lit_survey.py —— 盘点本地文献库：每个候选目录的文件数/体积/类型/是否已有索引。

用途：为阶段 A5 / D1 / D5 的"必须附文献出处"找到本地库的可检索入口。
"""
import os

BASE = "/mnt/f/speed_up"
CAND = ["lit", "lit2", "lit_mech", "lit_search", "lit_tmp", "pdfs",
        "_lit", "_litcheck", "_litidx", "_lit_tmp", ".litsearch"]
print("=" * 96)
print("本地文献库盘点（%s）" % BASE)
print("=" * 96)
print("  %-14s %-8s %-10s %-9s %s" % ('目录', '文件数', '体积(MB)', 'PDF数', '其他类型'))
for c in CAND:
    d = os.path.join(BASE, c)
    if not os.path.isdir(d):
        print("  %-14s （不存在）" % c)
        continue
    n = 0
    npy = 0
    sz = 0
    ext = {}
    for r, _dd, fs in os.walk(d):
        for f in fs:
            n += 1
            try:
                sz += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
            e = os.path.splitext(f)[1].lower() or '(无扩展)'
            ext[e] = ext.get(e, 0) + 1
            if e == '.pdf':
                npy += 1
    top = sorted(ext.items(), key=lambda kv: -kv[1])[:5]
    print("  %-14s %-8d %-10.1f %-9d %s"
          % (c, n, sz / 1e6, npy, ' '.join('%s:%d' % kv for kv in top)))
