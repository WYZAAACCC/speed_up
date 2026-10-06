#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_setcpu.py —— 把每个实验**限制到指定核**（改亲和性 + 降优先级），给用户留出核。

## 用户要求（2026-10-07 原话）
> 「每个实验用 **4 核**即可，要留出核供电脑上的其他工作正常运行。我还在电脑上写论文」

## 做法
  ① **亲和性**：对目标进程的**主线程 + 所有子线程**逐个 `sched_setaffinity`
     （⚠ 必须含子线程：BLAS/OpenMP 的工作线程如果已经创建，
       只改主线程**不会**约束它们 —— 实测靠这个才把 6.3 核压到 4 核）；
  ② **nice = 10**：即使与你抢同一个核，也会**优先让给你**（前台论文写作不卡）；
  ③ **分配（不相交，避免自相竞争）**：
       `c2Eq0` → 核 **0–3**      `c2B647` → 核 **4–7**
       ⇒ 核 **8–19（12 个）全留给你**
"""
import os
import sys

# tag → 允许的核（默认计划；可用命令行覆盖 `tag=0,1,2,3`）
PLAN = {"c2Eq0": [0, 1, 2, 3],
        "c2B647": [4, 5, 6, 7],
        "c2B15": [8, 9, 10, 11]}
for arg in sys.argv[1:]:
    if '=' in arg:
        t, cs = arg.split('=', 1)
        PLAN[t] = [int(x) for x in cs.split(',') if x.strip()]
NICE = 10


def procs():
    out = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            raw = open('/proc/%s/cmdline' % pid, 'rb').read()
        except OSError:
            continue
        line = ' '.join(x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x)
        if '_bk_exp.py' not in line or '--tag' not in line:
            continue
        tag = line.split('--tag')[1].split()[0]
        out.setdefault(tag, []).append(int(pid))
    return out


def threads(pid):
    d = '/proc/%d/task' % pid
    try:
        return [int(t) for t in os.listdir(d)]
    except OSError:
        return []


L = []
for tag, cores in PLAN.items():
    for pid in procs().get(tag, []):
        tids = threads(pid)
        ok = fail = 0
        for tid in tids:
            try:
                os.sched_setaffinity(tid, set(cores))
                ok += 1
            except OSError:
                fail += 1
        try:
            os.setpriority(os.PRIO_PROCESS, pid, NICE)
        except OSError as e:
            L.append("  ⚠ nice 设置失败 PID %d：%s" % (pid, e))
        real = sorted(os.sched_getaffinity(pid))
        L.append("  PID %-7d tag=%-8s 线程 %d 个（成功 %d/失败 %d）⇒ 现允许核 %s，nice=%d"
                 % (pid, tag, len(tids), ok, fail, real,
                    os.getpriority(os.PRIO_PROCESS, pid)))
if not L:
    L.append("  （没有找到带 --tag 的 _bk_exp.py 进程）")
print("\n".join(L))
