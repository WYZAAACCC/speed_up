#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_watch.py <log> [minutes] [samples] —— **低频**里程碑采样（默认每 20 min，共 9 次）。

目的：拿 t10PROD2 的**真实事件速率**（含 ckpt / 累计根数 / CPU / 内存），
      低开销、不干扰长跑（每 20 min 一次只读几个文件）。
判据：
  · 若「累计 N/135」在 2 个采样点间**不增**且 CPU 增量为 0 ⇒ 才判卡死；
  · 速率 = ΔN / Δt（min/事件），用于**时间规划**（不外推绝对值）。
"""
import os
import re
import subprocess
import sys
import time

log = sys.argv[1]
every_min = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 9


def snap():
    try:
        txt = open(log, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    lines = txt.splitlines()
    cums = [int(m.group(1)) for m in re.finditer(r'累计 (\d+)/135', txt)]
    ev = sum(1 for ln in lines if 'athermal 形核** @ step' in ln)
    ck = [ln.strip()[:52] for ln in lines if '[ckpt' in ln]
    try:
        cpu = subprocess.run(['bash', '-c',
                              'for p in $(pgrep -x python); do '
                              'tr "\\0" " " < /proc/$p/cmdline | grep -q _bk_exp.py '
                              '&& awk "{print \\$14+\\$15}" /proc/$p/stat; done'],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:                      # noqa: BLE001
        cpu = '?'
    free = subprocess.run(['bash', '-c', 'free -m | sed -n 2p; free -m | sed -n 3p'],
                          capture_output=True, text=True, timeout=30).stdout.strip()
    return dict(n=(cums[-1] if cums else 0), ev=ev, nline=len(lines),
                ck=len(ck), cpu=cpu, free=free.replace('\n', ' | '),
                mt=time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(log))))


print("=== 采样开始 %s（每 %.0f min，共 %d 次）==="
      % (time.strftime('%H:%M:%S'), every_min, samples), flush=True)
prev = None
for i in range(samples):
    s = snap()
    if s is None:
        print("[%s] **日志不可读**" % time.strftime('%H:%M:%S'), flush=True)
    else:
        d = ''
        if prev is not None:
            dn = s['n'] - prev['n']
            dt = every_min
            d = ('  ΔN=%+d  ⇒ %.1f min/事件' % (dn, dt / dn) if dn > 0
                 else '  ΔN=0（**该窗口无事件**）')
        print("[%s] 累计=%d/135 事件行=%d 日志行=%d ckpt=%d mtime=%s%s"
              % (time.strftime('%H:%M:%S'), s['n'], s['ev'], s['nline'],
                 s['ck'], s['mt'], d), flush=True)
        print("          CPU(jiffies)=%s" % s['cpu'], flush=True)
        print("          %s" % s['free'], flush=True)
        prev = s
    if i < samples - 1:
        time.sleep(every_min * 60)
print("=== 采样结束 %s ===" % time.strftime('%H:%M:%S'), flush=True)
