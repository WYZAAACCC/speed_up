#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_steprate3.py <tag> [...] —— 量**每步墙钟**（解析引擎日志的 `@ step N` 事件行）。

## 为什么不能只数数据行
数据行只在 `--snap-every` 写；**事件行 `@ step N` 每步都写**（`R628 §17` 的教训）。
本工具量 `Δt / Δstep`，并报"跑完剩余步数还需多久"。
"""
import os
import re
import sys
import time

LOG = "/mnt/f/speed_up/_w2_%s.log"
PAT = re.compile(r'@\s*step\s*(\d+)')
tags = [a.split('=')[0] for a in sys.argv[1:]] or ["M0", "M1"]
goal = {}
for a in sys.argv[1:]:
    if '=' in a:
        t, g = a.split('=')
        goal[t] = int(g)


def cur(tag):
    p = LOG % tag
    if not os.path.exists(p):
        return None
    last = None
    try:
        with open(p, 'rb') as fh:
            fh.seek(max(0, os.path.getsize(p) - 400000))
            for ln in fh.read().decode('utf-8', 'replace').splitlines():
                m = PAT.search(ln)
                if m:
                    last = int(m.group(1))
    except OSError:
        return None
    return last


s0 = {t: cur(t) for t in tags}
t0 = time.time()
print("采样 1：%s" % {k: v for k, v in s0.items()}, flush=True)
time.sleep(120)
dt = time.time() - t0
print("=" * 88)
print("步速实测（间隔 %.0f s）" % dt)
print("=" * 88)
print("  %-8s %-12s %-12s %-14s %s" % ('tag', 'step@t0', 'step@t1', 'Δstep', '每步(s) / 预计剩余'))
for t in tags:
    a, b = s0.get(t), cur(t)
    if a is None or b is None:
        print("  %-8s %-12s %-12s %-14s 无日志/无事件行" % (t, a, b, '—'))
        continue
    d = b - a
    if d <= 0:
        print("  %-8s %-12d %-12d %-14d ⚠ 无进展（但可能仍在算 ⇒ 用 `_t11_live2.py` 判活）"
              % (t, a, b, d))
        continue
    per = dt / d
    g = goal.get(t)
    tail = ''
    if g:
        rem = max(g - b, 0)
        tail = '%.1f s/步 ⇒ 剩 %d 步 = **%.1f h**' % (per, rem, rem * per / 3600.0)
    print("  %-8s %-12d %-12d %-14d %s" % (t, a, b, d, tail if tail else '%.1f s/步' % per))
