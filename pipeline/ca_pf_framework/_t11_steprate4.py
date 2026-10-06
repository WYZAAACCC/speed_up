#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_steprate4.py <tag>=<goal> ... —— 量**步速**（解析引擎日志的 `[  N]` 数据行）。

⚠ 记账（`_t11_steprate3.py` 的错）：我曾按 `@ step N` 写正则 —— 而**当前日志格式是
`  [  25] Vt=...`**（`@ step N` 是**形核事件行**，只在形核时出现）
⇒ 旧工具读到的是**旧值**、误报"无进展"。
**⇒ 先看原始文本再写正则**（教训 29）。
"""
import os
import re
import sys
import time

LOG = "/mnt/f/speed_up/_w2_%s.log"
# 数据行形如 `  [  25] Vt=0.0034 µm³ ...`；行首空白 + `[` + 数字 + `]`
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s+Vt=')
args = sys.argv[1:] or ["M2=1200"]
tags, goal = [], {}
for a in args:
    t, _, g = a.partition('=')
    tags.append(t)
    if g:
        goal[t] = int(g)


def cur(tag):
    p = LOG % tag
    if not os.path.exists(p):
        return None
    last = None
    try:
        with open(p, 'rb') as fh:
            fh.seek(max(0, os.path.getsize(p) - 300000))
            for ln in fh.read().decode('utf-8', 'replace').replace('\r', '\n').splitlines():
                m = PAT.search(ln)
                if m:
                    last = int(m.group(1))
    except OSError:
        return None
    return last


s0 = {t: cur(t) for t in tags}
t0 = time.time()
print("采样 1：%s；等 120 s …" % {k: v for k, v in s0.items()}, flush=True)
time.sleep(120)
dt = time.time() - t0
print("=" * 90)
print("步速实测（间隔 %.0f s，正则 = `^\\s*\\[\\s*(\\d+)\\]\\s+Vt=`）" % dt)
print("=" * 90)
print("  %-8s %-11s %-11s %-9s %s" % ('tag', 'step@t0', 'step@t1', 'Δstep', '每步(s) ⇒ 剩余预计'))
for t in tags:
    a, b = s0.get(t), cur(t)
    if a is None or b is None:
        print("  %-8s %-11s %-11s %-9s 无日志" % (t, a, b, '—'))
        continue
    d = b - a
    if d <= 0:
        print("  %-8s %-11d %-11d %-9d ⚠ 无进展（用 `_t11_live2.py` 判活）" % (t, a, b, d))
        continue
    per = dt / d
    g = goal.get(t)
    tail = '%.1f s/步' % per
    if g:
        rem = max(g - b, 0)
        tail += ' ⇒ 剩 %d 步 = **%.1f h**' % (rem, rem * per / 3600.0)
    print("  %-8s %-11d %-11d %-9d %s" % (t, a, b, d, tail))
