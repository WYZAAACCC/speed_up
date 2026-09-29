#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30：检查 `_r30_*` 命名空间里有没有别的 agent 并发写入（防"我的脚本被别人覆盖"）。"""
import os
import glob
import hashlib
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

MINE = ['_r30_rs.py', '_r30_gk.py', '_r30_psi.py', '_r30_scanphi.py',
        '_r30_scan2.py', '_r30_meta.py', '_r30_closed.py', '_r30_dt.py',
        '_r30_auto.py', '_r30_probe1.py']
print('--- 我建的脚本 ---')
for f in MINE:
    if os.path.exists(f):
        st = os.stat(f)
        h = hashlib.sha256(open(f, 'rb').read()).hexdigest()[:12]
        print('  %-20s %7d B  %s  %s' % (f, st.st_size,
                                        time.strftime('%H:%M:%S', time.localtime(st.st_mtime)), h))
    else:
        print('  %-20s **不存在**' % f)
print('--- 同前缀但不是我建的 ---')
allf = sorted(glob.glob('_r30_*'))
for f in allf:
    if f not in MINE and os.path.isfile(f):
        st = os.stat(f)
        print('  %-24s %7d B  %s' % (f, st.st_size,
                                     time.strftime('%H:%M:%S', time.localtime(st.st_mtime))))
