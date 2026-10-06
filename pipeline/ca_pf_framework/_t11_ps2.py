#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ps2.py —— 当前**所有** python / 重进程清单 + CPU 增量（判活）+ 内存。

判活判据（`R625 §13.3`）：**CPU 时间增量 > 0 才算在算**；只看日志 mtime 不得判卡死。
"""
import os
import time

OUT = "/mnt/f/speed_up/_w2_ps2.txt"
L = []


def snap():
    d = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            st = open('/proc/%s/stat' % pid).read().split()
            raw = open('/proc/%s/cmdline' % pid, 'rb').read()
            rss = 0
            for ln in open('/proc/%s/status' % pid):
                if ln.startswith('VmRSS:'):
                    rss = int(ln.split()[1])
                    break
        except (OSError, IndexError, ValueError):
            continue
        argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
        d[int(pid)] = dict(cpu=int(st[13]) + int(st[14]), rss=rss, argv=argv)
    return d


a = snap()
L.append("#### 采样 1：%s" % time.strftime('%H:%M:%S'))
time.sleep(10)
b = snap()
L.append("#### 采样 2：%s（间隔 10 s）" % time.strftime('%H:%M:%S'))
L.append("")
L.append("%-8s %-10s %-8s %-11s %s" % ('PID', 'CPU增/10s', 'RSS_MB', '状态', '命令行'))
L.append("-" * 112)
for pid in sorted(b):
    argv = b[pid]['argv']
    line = ' '.join(argv)
    if 'python' not in (argv[0] if argv else '') and '_bk_exp' not in line \
            and '_t11_' not in line:
        continue
    d = b[pid]['cpu'] - a.get(pid, {}).get('cpu', b[pid]['cpu'])
    rss = b[pid]['rss'] / 1024.0
    tag = ''
    if '--tag' in argv:
        tag = argv[argv.index('--tag') + 1]
    state = '★在算' if d > 0 else ('空闲/等待' if rss < 100 else '**⚠疑似卡死**')
    L.append("%-8d %-10d %-8.1f %-11s %s%s"
             % (pid, d, rss, state, line[:74], ('  [tag=%s]' % tag) if tag else ''))
L.append("")
L.append("=== 内存 ===")
for ln in open('/proc/meminfo'):
    if ln.split(':')[0] in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree',
                            'SwapCached'):
        L.append("  " + ln.rstrip())
L.append("")
L.append("=== 日志 mtime ===")
for f, nm in (("/mnt/f/speed_up/_w2_c2Eq0.log", "c2Eq0"),
              ("/mnt/f/speed_up/_w2_c2B647.log", "c2B647"),
              ("/mnt/f/speed_up/_w2_c2B15.log", "c2B15"),
              ("/mnt/f/speed_up/_w2_c2PosA.log", "c2PosA"),
              ("/mnt/f/speed_up/_w2_c2Arch3.log", "c2Arch3"),
              ("/mnt/f/speed_up/_w2_cube2c.log", "主控 cube2c"),
              ("/mnt/f/speed_up/_w2_goal_watch.txt", "(监控快照)")):
    if os.path.exists(f):
        n = sum(1 for _ in open(f, encoding='utf-8', errors='replace'))
        L.append("  %-14s %5d 行  mtime=%s" % (
            nm, n, time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))))
    else:
        L.append("  %-14s (未创建)" % nm)
open(OUT, 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
