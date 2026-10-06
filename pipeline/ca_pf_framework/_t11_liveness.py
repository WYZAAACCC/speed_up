#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_liveness.py [秒] —— **判活**：CPU 时间增量 + 进程状态 + cwd 僵尸检查。

判据（`R625 §13.3`）：
  · **CPU 增量 > 0** ⇒ 在算（哪怕日志一动不动）；
  · CPU 增量 = 0 且状态 `R` 持续 ⇒ 可疑（可能在 syscall/IO 等待）；
  · `cwd` 带 `(deleted)` ⇒ 僵尸（`AGENTS.md §3.11`）；
  · 状态 `T` ⇒ 被我 `SIGSTOP` 冻结了。
"""
import os
import sys
import time

sec = int(sys.argv[1]) if len(sys.argv) > 1 else 20


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
        cmd = ' '.join(x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x)
        if '_bk_exp.py' not in cmd or '--tag' not in cmd:
            continue
        seg = st[st.rfind(')') + 2:].split()
        d[int(pid)] = dict(cpu=int(seg[11]) + int(seg[12]), cmd=cmd,
                           state=seg[0])
    return d


a = snap()
t0 = time.time()
time.sleep(sec)
b = snap()
dt = time.time() - t0
print("=" * 96)
print("判活（间隔 %.0f s）" % dt)
print("=" * 96)
for pid, v in sorted(b.items()):
    tag = v['cmd'].split('--tag')[1].split()[0]
    d = v['cpu'] - a.get(pid, v)['cpu']
    try:
        cwd = os.readlink('/proc/%d/cwd' % pid)
    except OSError:
        cwd = '?'
    zombie = '(deleted)' in cwd
    cores = d / 100.0 / dt
    if v['state'] == 'T':
        verdict = '⏸ **已冻结**（SIGSTOP）'
    elif d > 0:
        verdict = '✅ **在算**（%.2f 核）' % cores
    else:
        verdict = '⚠⚠ **CPU 零增量** ⇒ 需查（syscall 等待？死锁？）'
    print("  PID %-7d tag=%-8s 状态=%-2s %-28s cwd%s"
          % (pid, tag, v['state'], verdict, ' ⚠(deleted)' if zombie else ''))
print("\n判读：**日志不动 ≠ 卡死**；只有 `CPU 增量 = 0` 才可疑。")
