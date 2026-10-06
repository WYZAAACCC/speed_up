#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_memwatch.py —— 独立监控：每 N 秒采一次**引擎进程的 RSS 与系统内存**，写文件。

## 为什么必须独立监控（本轮教训）
  `t10PROD1` 被**启动器的看门狗**（我设 20 GB）杀 ⇒ 它的 `VmHWM` 才被打印出来（20.18 GB）。
  `t10PROD2`（上限设 26 GB）**被 OOM-killer 直接杀** ⇒ **日志里连收尾行都没有**
  ⇒ **两次都没拿到"真实峰值"** ⇒ 无法判断 `nv=220` 到底需要多少内存。
  ⇒ 本脚本**不依赖被测进程的任何打印**，自己采样。

用法: _t11_memwatch.py <输出文件> <总时长秒> [间隔秒]
"""
import os
import sys
import time

out = sys.argv[1]
dur = float(sys.argv[2])
iv = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0


def engine_rss_kb():
    """所有 `_bk_exp.py` 进程的 RSS 之和（KB）。"""
    tot = 0
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            with open('/proc/%s/cmdline' % pid, 'rb') as fh:
                cl = fh.read().decode('utf-8', 'replace')
            if '_bk_exp.py' not in cl:
                continue
            with open('/proc/%s/status' % pid) as fh:
                for ln in fh:
                    if ln.startswith('VmRSS:'):
                        tot += int(ln.split()[1])
                        break
        except OSError:
            pass
    return tot


def sysmem():
    d = {}
    with open('/proc/meminfo') as fh:
        for ln in fh:
            k, v = ln.split(':', 1)
            d[k] = int(v.split()[0])
    return d


t0 = time.time()
peak_rss = 0
peak_used = 0
peak_avail = 10 ** 9
min_avail = 10 ** 9
sw = 0
with open(out, 'w') as fh:
    fh.write("# t_s  engine_rss_GB  sys_used_GB  sys_avail_GB  swap_used_GB\n")
    fh.flush()
    while time.time() - t0 < dur:
        r = engine_rss_kb() / 1048576.0
        m = sysmem()
        used = (m['MemTotal'] - m['MemAvailable']) / 1048576.0
        avail = m['MemAvailable'] / 1048576.0
        swu = m.get('SwapTotal', 0) and (m['SwapTotal'] - m['SwapFree']) / 1048576.0
        peak_rss = max(peak_rss, r)
        peak_used = max(peak_used, used)
        min_avail = min(min_avail, avail)
        sw = max(sw, swu or 0)
        fh.write("%7.0f  %12.2f  %11.2f  %12.2f  %12.2f\n"
                 % (time.time() - t0, r, used, avail, swu or 0))
        fh.flush()
        time.sleep(iv)
print("=== 监控汇总（被监控进程结束或时长到）===")
print("  引擎 RSS 峰值      = %.2f GB" % peak_rss)
print("  系统 used 峰值     = %.2f GB" % peak_used)
print("  系统 available 最低 = %.2f GB" % min_avail)
print("  swap 用量峰值      = %.2f GB" % sw)
print("  （明细见 %s）" % out)
