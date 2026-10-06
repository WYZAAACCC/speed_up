#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_kill.py <子串> [...] —— 按**命令行子串**杀 python 进程（纯 Python，不用 pkill -f）。

⚠ 安全：先打印将被杀的 PID+命令行，再杀；**排除自己**。
"""
import os
import signal
import sys
import time

pats = sys.argv[1:]
if not pats:
    sys.exit("用法: _t11_kill.py <子串> [...]")
me = os.getpid()
victims = []
for pid in os.listdir('/proc'):
    if not pid.isdigit() or int(pid) == me:
        continue
    try:
        raw = open('/proc/%s/cmdline' % pid, 'rb').read()
    except OSError:
        continue
    argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
    if not any(x.endswith('python') or 'python' in x for x in argv[:1]):
        continue
    line = ' '.join(argv)
    if any(p in line for p in pats):
        victims.append((int(pid), line))
for pid, line in victims:
    print("  → 杀 PID %d：%s" % (pid, line[:120]))
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as e:
        print("     失败：%s" % e)
if not victims:
    print("  （没有匹配的进程）")
time.sleep(2)
n = 0
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        raw = open('/proc/%s/cmdline' % pid, 'rb').read()
    except OSError:
        continue
    if b'python' in raw:
        n += 1
        print("  剩余 python：PID %s  %s" % (pid, raw.decode('utf-8', 'replace')
                                            .replace('\0', ' ')[:90]))
print("  剩余 python 数 = %d" % n)
