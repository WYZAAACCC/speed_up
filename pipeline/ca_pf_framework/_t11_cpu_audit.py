#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cpu_audit.py —— 看整机 CPU 占用：谁在用、各占多少核、负载情况。"""
import os
import time

OUT = "/mnt/f/speed_up/_w2_cpu_audit.txt"
NC = os.cpu_count()
L = ["#### %s   逻辑核数 = %d" % (time.strftime('%F %T'), NC), ""]


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
        # 字段 14/15 = utime/stime
        seg = st[st.rfind(')') + 2:].split()
        d[int(pid)] = (int(seg[11]) + int(seg[12]),
                       ' '.join(x.decode('utf-8', 'replace')
                                for x in raw.split(b'\0') if x))
    return d


a = snap()
t0 = time.time()
time.sleep(10)
b = snap()
dt = time.time() - t0
L.append("=== 各进程 CPU 占用（近 %.0f s，单位：核）===" % dt)
L.append("%-8s %-9s %s" % ('PID', '核数', '命令行'))
rows = []
for pid, (cpu, cmd) in b.items():
    d = cpu - a.get(pid, (cpu, ''))[0]
    c = d / 100.0 / dt          # jiffies(100/s) → cores
    if c > 0.05:
        rows.append((c, pid, cmd))
for c, pid, cmd in sorted(rows, reverse=True):
    L.append("%-8d %-9.2f %s" % (pid, c, cmd[:88]))
tot = sum(c for c, _, _ in rows)
L.append("-" * 100)
L.append("  合计占用 = **%.2f 核** / %d 核  ⇒ 空闲 ≈ %.2f 核"
         % (tot, NC, NC - tot))
L.append("")
L.append("=== /proc/loadavg ===")
L.append("  " + open('/proc/loadavg').read().strip())
# 各进程的 CPU 亲和性
L.append("")
L.append("=== 亲和性（允许的核）===")
for c, pid, cmd in sorted(rows, reverse=True)[:6]:
    try:
        aff = os.sched_getaffinity(pid)
        L.append("  PID %-7d 亲和 = %s  (共 %d 核)  %s"
                 % (pid, sorted(aff), len(aff), cmd[:60]))
    except OSError as e:
        L.append("  PID %-7d 读取失败：%s" % (pid, e))
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
