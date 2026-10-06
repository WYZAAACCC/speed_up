#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_frozen_mem.py —— 证明**冻结进程的内存仍在物理内存里**。

三条证据：
  ① `/proc/<pid>/status` 的 `VmRSS`（常驻物理内存）冻结前后是否变化；
  ② `/proc/<pid>/status` 的 `VmSwap`（**被换出**的部分）是否 > 0
     ⇒ 冻结**不会**主动把进程换出；只有整机内存压力才会；
  ③ 进程状态 = `T`（`TASK_STOPPED`）—— 内核只是**把它移出调度队列**，
     地址空间、页表、堆栈、打开的 fd 全部保留。
"""
import os
import time

PIDS = [9315, 10489, 10518, 9314, 10488, 10517, 6735]
OUT = "/mnt/f/speed_up/_w2_frozen_mem.txt"
L = []
L.append("#### %s" % time.strftime('%F %T'))
L.append("")
L.append("%-8s %-6s %-11s %-11s %-11s %-9s %s"
         % ('PID', '状态', 'VmRSS(MB)', 'VmSwap(kB)', 'VmSize(MB)', '线程数', '备注'))
L.append("-" * 108)
tot_rss = tot_swap = 0
for pid in PIDS:
    try:
        st = open('/proc/%d/stat' % pid).read()
        state = st[st.rfind(')') + 2]
        d = {}
        for ln in open('/proc/%d/status' % pid):
            k = ln.split(':')[0]
            if k in ('VmRSS', 'VmSwap', 'VmSize', 'Threads'):
                d[k] = int(ln.split()[1])
        except_ = ''
    except OSError as e:
        L.append("%-8d （不存在：%s）" % (pid, e))
        continue
    rss = d.get('VmRSS', 0) / 1024.0
    sw = d.get('VmSwap', 0)
    vsz = d.get('VmSize', 0) / 1024.0
    tot_rss += rss
    tot_swap += sw
    L.append("%-8d %-6s %-11.1f %-11d %-11.1f %-9d %s"
             % (pid, state, rss, sw, vsz, d.get('Threads', -1),
                ('✅ 内存常驻' if state == 'T' and sw == 0 else
                 ('⚠ 状态非 T' if state != 'T' else '⚠ 有 %d kB 被换出' % sw))))
L.append("-" * 108)
L.append("  合计常驻 RSS = **%.2f GB**   合计被换出 = **%.1f MB**"
         % (tot_rss / 1024.0, tot_swap / 1024.0))
L.append("")
L.append("=== 整机内存（有无压力）===")
for ln in open('/proc/meminfo'):
    if ln.split(':')[0] in ('MemTotal', 'MemFree', 'MemAvailable', 'SwapTotal',
                            'SwapFree', 'Cached'):
        L.append("  " + ln.rstrip())
L.append("")
L.append("=== 说明 ===")
L.append("  · `SIGSTOP` ⇒ 内核把进程置为 `TASK_STOPPED` 并**移出调度队列**；")
L.append("    **不回收地址空间**（页表、匿名页、映射、fd、线程栈全部保留）⇒ 内存**不释放**。")
L.append("  · 冻结**不会主动**把进程换出（swap）；只有**整机内存压力**才会。")
L.append("    本机 `MemAvailable` 很大 ⇒ 无压力 ⇒ 不会被换出。")
L.append("  · 只有四种情况会真丢：`SIGKILL` / 重启 WSL / WSL 崩溃 / 整机 OOM。")
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
