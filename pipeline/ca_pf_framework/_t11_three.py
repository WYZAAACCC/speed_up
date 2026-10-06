#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_three.py —— 三个臂的**统一快照**：CPU 占用 + 亲和性 + 进度 + 内存。"""
import os
import re
import subprocess
import time

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
OUT = "/mnt/f/speed_up/_w2_three.txt"
NC = os.cpu_count()


def snap():
    d = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            st = open('/proc/%s/stat' % pid).read()
            raw = open('/proc/%s/cmdline' % pid, 'rb').read()
        except OSError:
            continue
        seg = st[st.rfind(')') + 2:].split()
        d[int(pid)] = (int(seg[11]) + int(seg[12]),
                       ' '.join(x.decode('utf-8', 'replace')
                                for x in raw.split(b'\0') if x))
    return d


a = snap()
t0 = time.time()
time.sleep(12)
b = snap()
dt = time.time() - t0
L = ["#### %s   逻辑核 %d" % (time.strftime('%F %T'), NC), ""]
L.append("%-8s %-8s %-9s %-14s %-9s %s"
         % ('PID', 'tag', '核数', '亲和(核)', 'nice', '进度'))
L.append("-" * 104)
tot = 0.0
for pid, (cpu, cmd) in sorted(b.items()):
    if '_bk_exp.py' not in cmd or '--tag' not in cmd:
        continue
    tag = cmd.split('--tag')[1].split()[0]
    c = (cpu - a.get(pid, (cpu, ''))[0]) / 100.0 / dt
    tot += max(c, 0.0)
    try:
        aff = sorted(os.sched_getaffinity(pid))
        ni = os.getpriority(os.PRIO_PROCESS, pid)
    except OSError:
        aff, ni = [], '?'
    # 日志进度
    f = "/mnt/f/speed_up/_w2_%s.log" % tag
    prog = '—'
    if os.path.exists(f):
        txt = open(f, encoding="utf-8", errors="replace").read()
        ds = [int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]', txt, re.M)]
        es = [int(m.group(1)) for m in re.finditer(r'@\s*step\s*(\d+)', txt)]
        best = max(ds + es) if (ds or es) else None
        mt = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))
        prog = 'step≥%s (数据行%s/事件行%s, mtime %s)' % (
            best, ds[-1] if ds else '—', es[-1] if es else '—', mt)
    L.append("%-8d %-8s %-9.2f %-14s %-9s %s"
             % (pid, tag, c, str(aff)[:14], ni, prog))
L.append("-" * 104)
L.append("  合计挤占 = **%.2f 核** / %d 核 ⇒ **空闲 ≈ %.2f 核**" % (tot, NC, NC - tot))
L.append("")
for ln in open('/proc/meminfo'):
    if ln.split(':')[0] in ('MemAvailable', 'SwapTotal', 'SwapFree'):
        L.append("  " + ln.rstrip())
L.append("  loadavg: " + open('/proc/loadavg').read().strip())
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
