#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_live2.py <tag> [...] —— **按 CPU 时间增量判活**（间隔 60 s 采样两次）。

## 判据（`R628 §13` 的教训）
**不得**只凭日志 mtime 判"卡死"（长跑可能 180 s 内无输出却仍在算）。
本工具读 `/proc/<pid>/stat` 的 `utime+stime`（**CPU 时间**，与墙钟无关），
两次采样做差：**增量 > 0 ⇒ 在算**；增量 = 0 且日志不动 ⇒ 真卡死。
"""
import os
import sys
import time


def pids(tag):
    out = []
    for p in os.listdir('/proc'):
        if not p.isdigit():
            continue
        try:
            raw = open('/proc/%s/cmdline' % p, 'rb').read().decode('utf-8', 'replace')
        except OSError:
            continue
        if '_bk_exp.py' in raw and '--tag' in raw and tag in raw:
            out.append(int(p))
    return out


def cputime(pid):
    try:
        f = open('/proc/%d/stat' % pid).read().split()
        return (int(f[13]) + int(f[14])) / os.sysconf('SC_CLK_TCK')
    except (OSError, IndexError, ValueError):
        return -1.0


def rss(pid):
    try:
        for ln in open('/proc/%d/status' % pid):
            if ln.startswith('VmRSS:'):
                return int(ln.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


tags = sys.argv[1:] or ["M0", "M1"]
a = {}
for t in tags:
    ps = pids(t)
    a[t] = {p: cputime(p) for p in ps}
print("采样 1 完成，等 60 s …", flush=True)
time.sleep(60)
print("=" * 84)
print("按 CPU 时间增量判活（间隔 60 s）")
print("=" * 84)
print("  %-8s %-10s %-14s %-12s %s" % ('tag', 'PID', 'CPU秒增量', 'RSS(MB)', '判读'))
for t in tags:
    ps = pids(t)
    if not ps:
        print("  %-8s %-10s %-14s %-12s ⛔ 进程不存在（已结束或被杀）" % (t, '—', '—', '—'))
        continue
    for p in ps:
        c0 = a[t].get(p)
        c1 = cputime(p)
        d = (c1 - c0) if (c0 is not None and c1 >= 0) else float('nan')
        print("  %-8s %-10d %-14.1f %-12.0f %s"
              % (t, p, d, rss(p),
                 '✅ 在算' if d > 0.5 else ('⚠ 疑停滞' if d >= 0 else '（新进程）')))
