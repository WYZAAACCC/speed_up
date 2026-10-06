#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_v2_status.py —— 立方核实验 v2 的状态（纯 Python，写文件）。"""
OUT = "/mnt/f/speed_up/_w2_v2_status.txt"
import os

lines = []
lines.append("#### %s" % __import__('time').strftime('%F %T'))
for f, nm in (("/mnt/f/speed_up/_w2_cube2.log", "主控"),
              ("/mnt/f/speed_up/_w2_c2Eq0.log", "c2Eq0"),
              ("/mnt/f/speed_up/_w2_c2B647.log", "c2B647"),
              ("/mnt/f/speed_up/_w2_c2B15.log", "c2B15")):
    if os.path.exists(f):
        txt = open(f, encoding='utf-8', errors='replace').read()
        lines.append("  %-8s %7d 字节  %5d 行  mtime=%s"
                     % (nm, len(txt), txt.count('\n'),
                        __import__('time').strftime(
                            '%H:%M:%S', __import__('time').localtime(os.path.getmtime(f)))))
    else:
        lines.append("  %-8s (未创建)" % nm)
# 进程
import subprocess
p = subprocess.run(['pgrep', '-x', 'python'], capture_output=True, text=True)
lines.append("python 进程: %s" % (p.stdout.split() or '无'))
open(OUT, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
