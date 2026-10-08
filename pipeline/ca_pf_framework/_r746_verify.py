#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r746_verify.py —— 独立核对导出的包：**逐件 SHA256 与源目录比对**。

不复用生成器的任何中间结果 —— 重新算一遍，两边独立。
"""
import hashlib
import os
import sys

SRC = '/mnt/f/speed_up/pipeline/ca_pf_framework'
DST = '/mnt/f/speed_up/winb_core'
SKIP = {'_smoke.py', 'MANIFEST.sha256', 'README_BUNDLE.md'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


n_ok = n_bad = n_missing = 0
bad = []
for f in sorted(os.listdir(DST)):
    if f in SKIP:
        continue
    sp, dp = os.path.join(SRC, f), os.path.join(DST, f)
    if not os.path.isfile(sp):
        n_missing += 1
        bad.append('%s  源目录无此文件' % f)
        continue
    a, b = sha(sp), sha(dp)
    if a == b:
        n_ok += 1
    else:
        n_bad += 1
        bad.append('%s  源 %s ≠ 包 %s' % (f, a[:12], b[:12]))

print('=' * 76)
print('独立核对：包 vs 源目录')
print('=' * 76)
print('  ✅ 逐位一致      = %d' % n_ok)
print('  ⛔ 不一致        = %d' % n_bad)
print('  ⛔ 源目录无此文件 = %d' % n_missing)
for b in bad:
    print('     %s' % b)
print()
# MANIFEST 自身自洽
mp = os.path.join(DST, 'MANIFEST.sha256')
if os.path.isfile(mp):
    m_ok = m_bad = 0
    for ln in open(mp):
        p = ln.split()
        if len(p) != 3:
            continue
        h, name, sz = p
        fp = os.path.join(DST, name)
        if os.path.isfile(fp) and sha(fp) == h:
            m_ok += 1
        else:
            m_bad += 1
            print('  ⛔ MANIFEST 对不上： %s' % name)
    print('  MANIFEST.sha256 自洽： %d 通过 / %d 失败' % (m_ok, m_bad))
print()
print('  ⇒ %s' % ('✅ **包是源目录的逐位副本**'
                 if (n_bad == 0 and n_missing == 0) else '⛔ 有问题'))
sys.exit(0 if (n_bad == 0 and n_missing == 0) else 1)
