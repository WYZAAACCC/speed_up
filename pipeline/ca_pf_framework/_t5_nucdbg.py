#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nucdbg.py --- 读两臂的 `nuc_dbg.json`（形核计数器）——**判定碎片化的真正原因**
"""
import glob
import json
import os

for TAG in ('t5N276', 't5NR'):
    print('=' * 90)
    print('★ %s' % TAG)
    print('=' * 90)
    d = '_exp/_bk_t5/dry_%s' % TAG
    fs = sorted(glob.glob(os.path.join(d, '*.json')))
    if not fs:
        print('  （目录下没有 json）')
        continue
    for F in fs:
        print('  ── %s ──' % os.path.basename(F))
        try:
            j = json.load(open(F))
        except Exception as e:
            print('     读失败：%s' % e); continue
        if isinstance(j, dict):
            for k, v in j.items():
                if isinstance(v, dict):
                    print('     %s:' % k)
                    for k2, v2 in v.items():
                        print('        %-16s %s' % (k2, v2))
                else:
                    print('     %-20s %s' % (k, v))
        else:
            print('     %s' % j)
    print()
print('═' * 90)
print('★ 判据（**看哪个计数非零**）')
print('  * `nfsv_nofield` > 0  ⇒ "找不到同变体空场 ⇒ 退回用 k" 被触发 ⇒ **碎片化的直接原因**;')
print('  * `nfsv_ok`            ⇒ 成功播进新场的次数;')
print('  * `att` / `ok` / `oob` ⇒ attach 通道的候选/成功/越界;')
print('  * `cov` / `exc`        ⇒ 覆盖/排除计数。')
