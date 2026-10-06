#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_watchdog.py <tag> [<limit_gb>] —— **内存看门狗**：护着实验进程，超限即杀。

## 为什么需要（`R625 §14` 的教训）
本项目**已发生过 3 次 OOM**。看门狗**必须是发起实验的那一层**：
`_bk_exp.py` 自己**没有**看门狗；`_t5_short.py` 有一个但生产绕过了它。

## 判据
每 20 s 读一次**目标进程**（按命令行匹配 `--tag <tag>`）的 `VmRSS`：
  · `RSS > limit` ⇒ **立刻 SIGKILL** 并打印；
  · 同时监控**系统 `MemAvailable`**：低于 2 GB 也杀（`R625` 的红线）。
退出码：0 = 正常结束；3 = 被看门狗杀掉。
"""
import os
import subprocess
import sys
import time

TAG = sys.argv[1]
LIMIT_GB = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0
SYS_FLOOR_MB = 2048
LOG = "/mnt/f/speed_up/_w2_wd_%s.txt" % TAG


def pids_of_tag():
    out = []
    for p in os.listdir('/proc'):
        if not p.isdigit():
            continue
        try:
            raw = open('/proc/%s/cmdline' % p, 'rb').read().decode('utf-8', 'replace')
        except OSError:
            continue
        if '_bk_exp.py' in raw and ('--tag' in raw) and (TAG in raw):
            out.append(int(p))
    return out


def rss_mb(pid):
    try:
        for ln in open('/proc/%d/status' % pid):
            if ln.startswith('VmRSS:'):
                return int(ln.split()[1]) / 1024.0
    except OSError:
        return 0.0
    return 0.0


def memavail_mb():
    for ln in open('/proc/meminfo'):
        if ln.startswith('MemAvailable:'):
            return int(ln.split()[1]) / 1024.0
    return float('nan')


fh = open(LOG, 'w')
n = 0
killed = False
while True:
    ps = pids_of_tag()
    if not ps:
        if n > 3:
            break
        n += 1
        time.sleep(20)
        continue
    n = 0
    tot = sum(rss_mb(p) for p in ps)
    ma = memavail_mb()
    line = "%s  tag=%s  nproc=%d  RSS合计=%.0f MB  MemAvailable=%.0f MB" % (
        time.strftime('%H:%M:%S'), TAG, len(ps), tot, ma)
    fh.write(line + "\n")
    fh.flush()
    if tot > LIMIT_GB * 1024 or ma < SYS_FLOOR_MB:
        why = ('RSS %.0f MB > %.0f MB' % (tot, LIMIT_GB * 1024)
               if tot > LIMIT_GB * 1024 else 'MemAvailable %.0f MB < %d MB'
               % (ma, SYS_FLOOR_MB))
        fh.write("!!! 看门狗中止：%s ⇒ SIGKILL %s\n" % (why, ps))
        fh.flush()
        for p in ps:
            try:
                os.kill(p, 9)
            except OSError:
                pass
        killed = True
        break
    time.sleep(20)
fh.write("结束（killed=%s）\n" % killed)
fh.close()
sys.exit(3 if killed else 0)
