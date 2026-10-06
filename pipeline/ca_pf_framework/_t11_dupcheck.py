#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dupcheck.py —— 查**同一 tag 是否有多个 _bk_exp.py 进程**（会互相覆盖产物）。"""
import glob
import os
import time

by_tag = {}
for pid in sorted(os.listdir('/proc'), key=lambda x: int(x) if x.isdigit() else 0):
    if not pid.isdigit():
        continue
    try:
        raw = open('/proc/%s/cmdline' % pid, 'rb').read()
        st = open('/proc/%s/stat' % pid).read()
    except OSError:
        continue
    line = ' '.join(x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x)
    if '_bk_exp.py' not in line or '--tag' not in line:
        continue
    tag = line.split('--tag')[1].split()[0]
    seg = st[st.rfind(')') + 2:].split()
    et = int(seg[19]) / 100.0            # starttime (jiffies since boot)
    by_tag.setdefault(tag, []).append((int(pid), et, line))
print("=" * 100)
for tag, lst in by_tag.items():
    print("【%s】%d 个进程%s" % (tag, len(lst), '  ⚠⚠ **重复！**' if len(lst) > 1 else ''))
    for pid, et, line in lst:
        print("   PID %-7d starttime=%.0f s  %s" % (pid, et, line[:100]))
    if len(lst) > 1:
        print("   → 早的那条是原进程，晚的是**重复实例**；两者写**同一个 --out 目录** ⇒ 产物会互相覆盖")
print()
print("=== c2B647 目录里的产物 mtime ===")
ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_c2B647"
for f in sorted(glob.glob(os.path.join(ROOT, "**", "*"), recursive=True)):
    if os.path.isfile(f):
        print("   %-24s %9d B  %s" % (os.path.relpath(f, ROOT), os.path.getsize(f),
                                      time.strftime('%H:%M:%S',
                                                    time.localtime(os.path.getmtime(f)))))
