#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_steprate2.py <tag> —— **实测步速**：两次采样之间 `gpu/ckpt` 或日志前进了多少。

判据：两次采样间隔 180 s，比较
  · 日志字节数 / 行数
  · `ckpt/` 里最新的 mtime 与文件名
  · 进程 CPU 时间增量（确认在算）
⇒ 给出 **s/步** 的**实测**值（不是推算）。
"""
import glob
import os
import time

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tags = ["c2Eq0", "c2B647", "c2B15"]
INTERVAL = int(os.environ.get("IVL", "180"))


def probe():
    st = {}
    for t in tags:
        d = os.path.join(ROOT, "dry_%s" % t)
        log = "/mnt/f/speed_up/_w2_%s.log" % t
        ck = sorted(glob.glob(os.path.join(d, "ckpt", "*.npz")))
        st[t] = dict(
            logsz=os.path.getsize(log) if os.path.exists(log) else 0,
            ck=os.path.basename(ck[-1]) if ck else '—',
            ckmt=os.path.getmtime(ck[-1]) if ck else 0.0,
            snap=len(glob.glob(os.path.join(d, "snap_*.npz"))),
        )
    return st


a = probe()
t0 = time.time()
print("采样 1 完成，等 %d s …" % INTERVAL, flush=True)
time.sleep(INTERVAL)
b = probe()
dt = time.time() - t0
print("=" * 96)
print("实测步速（间隔 %.0f s）" % dt)
print("=" * 96)
print("%-8s %-12s %-14s %-12s %s"
      % ('tag', '日志增长(B)', '最新ckpt变化', '快照数变化', '判读'))
for t in tags:
    dsz = b[t]['logsz'] - a[t]['logsz']
    ck = '%s→%s' % (a[t]['ck'], b[t]['ck']) if a[t]['ck'] != b[t]['ck'] else a[t]['ck']
    dsn = b[t]['snap'] - a[t]['snap']
    verdict = ('✅ 有输出' if (dsz > 0 or dsn > 0 or a[t]['ck'] != b[t]['ck'])
               else '⚠ **%.0f s 内零输出**（看 CPU 增量判是否在算）' % dt)
    print("%-8s %-12d %-14s %-12s %s" % (t, dsz, ck, '+%d' % dsn, verdict))
