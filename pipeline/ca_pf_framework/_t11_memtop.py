#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_memtop.py —— 内存 TOP：谁在吃内存（RSS 排序）+ 内存/swap 总览。"""
import os
import time

OUT = "/mnt/f/speed_up/_w2_memtop.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
rows = []
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        rss = 0
        for ln in open('/proc/%s/status' % pid):
            if ln.startswith('VmRSS:'):
                rss = int(ln.split()[1]); break
        raw = open('/proc/%s/cmdline' % pid, 'rb').read()
    except OSError:
        continue
    cmd = ' '.join(x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x)
    if rss > 20000:
        rows.append((rss, int(pid), cmd))
rows.sort(reverse=True)
L.append("RSS > 20 MB 的进程（共 %d 个）:" % len(rows))
for rss, pid, cmd in rows[:20]:
    L.append("  %-8d %8.1f MB  %s" % (pid, rss / 1024.0, cmd[:96]))
L.append("")
L.append("=== /proc/meminfo 关键项 ===")
for ln in open('/proc/meminfo'):
    if ln.split(':')[0] in ('MemTotal', 'MemFree', 'MemAvailable', 'Cached',
                            'SwapTotal', 'SwapFree', 'SwapCached', 'Shmem',
                            'Slab', 'PageTables', 'Committed_AS'):
        L.append("  " + ln.rstrip())
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
