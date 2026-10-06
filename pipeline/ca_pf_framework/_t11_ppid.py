#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ppid.py —— 查 `_bk_exp.py` 进程的**父进程链**（谁在起它们）。"""
import os
import time


def info(pid):
    try:
        st = open('/proc/%d/stat' % pid).read()
        raw = open('/proc/%d/cmdline' % pid, 'rb').read()
    except OSError:
        return None
    seg = st[st.rfind(')') + 2:].split()
    return dict(ppid=int(seg[1]), state=seg[0],
                start=int(seg[19]),
                cmd=' '.join(x.decode('utf-8', 'replace')
                             for x in raw.split(b'\0') if x))


uptime = float(open('/proc/uptime').read().split()[0])
print("uptime = %.0f s" % uptime)
print("=" * 100)
for pid in sorted(os.listdir('/proc'), key=lambda x: int(x) if x.isdigit() else 0):
    if not pid.isdigit():
        continue
    v = info(int(pid))
    if not v or '_bk_exp.py' not in v['cmd']:
        continue
    tag = v['cmd'].split('--tag')[1].split()[0] if '--tag' in v['cmd'] else '?'
    # 父进程链
    chain = []
    p = v['ppid']
    for _ in range(6):
        if p in (0, 1):
            chain.append('PID %d' % p)
            break
        pv = info(p)
        if pv is None:
            chain.append('PID %d(?)' % p)
            break
        chain.append('PID %d[%s]' % (p, pv['cmd'][:40] or '?'))
        p = pv['ppid']
    age = (uptime - v['start'] / 100.0) / 60.0
    print("PID %-7d tag=%-8s 年龄=%.1f min  链: %s"
          % (int(pid), tag, age, ' ← '.join(chain)))
