#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_lanes.py --- ★★ 成功判据⑧ 的取证：**"并行是真的"**。

## 判据原话（goal 成功判据⑧）
> **并行是真的：给出车道表（跑什么 / 绑哪几核 / 起止时间）
> 与批次期间的 load average / 各道占用实测。**

## 本量具收四样（都落盘，不靠回忆）
1. **车道表**：每个 `_bk_exp.py` 的 **tag / pid / 绑定的核（`Cpus_allowed_list`）/ 起止时间 / CPU 时间**
   —— `Cpus_allowed_list` 直接读 `/proc/<pid>/status`，**不是我"记得绑了哪几核"**；
2. **load average**：`/proc/loadavg` 的 1/5/15 分钟 + **运行中/总线程数**；
3. **各道占用**：每个 pid 的 `utime+stime` 增量（两次采样）⇒ **实际吃几个核**；
4. **口径声明**：本机 20 逻辑核；**并发和 ÷ 线程数 = 折算墙钟**（不得与墙钟混算）。
"""
import os
import re
import sys
import time
from datetime import datetime


def read(p):
    try:
        with open(p, encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except OSError:
        return ''


def cpu_of(pid):
    """★ 从 `/proc/<pid>/stat` 取 `utime+stime`（**单位 jiffies**）。

    ⚠ **第一版我写错了**（留痕）：我去 `/proc/<pid>/status` 找 `Utime:` / `Stime:` ——
    **那两个字段根本不在 `status` 里**（它们在 `stat` 里）⇒ 解析恒得 0
    ⇒ 工具报出"**合计占用 0.00 核**"，而**同一时刻 `loadavg` 是 3.98**
    ⇒ **两个数自相矛盾 ⇒ 先怀疑量具（P21）⇒ 果然是量具错。**
    正确做法：`stat` 的第 14/15 个字段（`comm` 之后计数），
    且 **`comm` 可能含空格/括号 ⇒ 必须从最后一个 `)` 之后开始切**。
    """
    try:
        with open('/proc/%d/stat' % pid, encoding='utf-8', errors='replace') as fh:
            s = fh.read()
    except OSError:
        return None
    r = s.rfind(')')
    if r < 0:
        return None
    f = s[r + 2:].split()
    # 从 `state`（第 3 个字段）算起 ⇒ utime 是第 14 个 ⇒ 下标 14-3 = 11
    try:
        return (int(f[11]) + int(f[12])) / os.sysconf('SC_CLK_TCK')
    except (IndexError, ValueError):
        return None


def procs():
    out = []
    for d in os.listdir('/proc'):
        if not d.isdigit():
            continue
        st = read('/proc/%s/status' % d)
        cmd = read('/proc/%s/cmdline' % d).replace('\0', ' ')
        if '_bk_exp.py' not in cmd and '_r581_p2.py' not in cmd:
            continue
        tag = ''
        m = re.search(r'--tag\s+(\S+)', cmd)
        if m:
            tag = m.group(1)
        m2 = re.search(r'Cpus_allowed_list:\s*(\S+)', st)
        rss = re.search(r'VmRSS:\s*(\d+)\s*kB', st)
        c = cpu_of(int(d))
        out.append(dict(
            pid=int(d), tag=tag, cores=(m2.group(1) if m2 else '?'),
            rss_mb=(int(rss.group(1)) / 1024 if rss else 0.0),
            cpu_s=(c if c is not None else float('nan'))))
    return out


def main():
    print('=' * 104)
    print('成功判据⑧ —— "并行是真的"：车道表 + load average + 各道占用')
    print('=' * 104)
    print('  ⚠ 口径：本机 **20 逻辑核**；**并发和 ÷ 线程数 = 折算墙钟**（不得与墙钟混算）')
    print('  ⚠ 所有"绑哪几核"**直接读 `/proc/<pid>/status` 的 `Cpus_allowed_list`**，不是我回忆的')
    print()
    a = procs()
    t0 = time.time()
    print('  ── 采样 1（%s）──' % datetime.now().strftime('%F %T'))
    print('  %-8s %-10s %-10s %-10s %-10s' % ('tag', 'pid', 'Cpus_allowed', 'RSS(MB)', 'CPU时间(s)'))
    for p in sorted(a, key=lambda x: x['pid']):
        print('  %-8s %-10d %-10s %-10.2f %-10.1f'
              % (p['tag'] or '(驱动)', p['pid'], p['cores'], p['rss_mb'], p['cpu_s']))
    la = read('/proc/loadavg').split()
    ncpu = os.cpu_count()
    print()
    print('  `/proc/loadavg`：**1min=%s  5min=%s  15min=%s** ；运行中/总线程 = %s'
          % (la[0], la[1], la[2], la[3]))
    print('  ⇒ 逻辑核数 %d ；**1 分钟利用率 ≈ %.1f%%**'
          % (ncpu, 100.0 * float(la[0]) / ncpu))
    # 第二次采样
    time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 20.0)
    b = {p['pid']: p for p in procs()}
    dt = time.time() - t0
    print()
    print('  ── 采样 2（%.1f s 后）⇒ **实际吃几个核**（Δcpu/Δt）──' % dt)
    print('  %-8s %-10s %-12s %-12s' % ('tag', 'pid', 'Δcpu(s)', '占用核数'))
    tot = 0.0
    for p in sorted(a, key=lambda x: x['pid']):
        q = b.get(p['pid'])
        if not q:
            print('  %-8s %-10d （已退出）' % (p['tag'] or '(驱动)', p['pid'])); continue
        d = q['cpu_s'] - p['cpu_s']
        occ = d / dt
        tot += occ
        print('  %-8s %-10d %-12.2f **%.2f 核**' % (p['tag'] or '(驱动)', p['pid'], d, occ))
    print()
    print('  ⇒ **合计占用 %.2f 核**（全部进程）；**机器有 %d 核** ⇒ 利用率 %.1f%%'
          % (tot, ncpu, 100.0 * tot / ncpu))
    print()
    print('=' * 104)
    print('★ 判读（**预先写死**）')
    print('  · 判据⑧ 要三样：① 车道表（跑什么/绑哪几核/起止）② load average ③ 各道占用实测')
    print('  · **"绑定"以 `Cpus_allowed_list` 为准**；若两道的核集合**不相交** ⇒ 并行是真的')
    print('  · ⚠ 本机是**共享**的（goal 明示）⇒ **load average 只作旁证**，判据仍只信配对比值')
    print('=' * 104)


if __name__ == '__main__':
    main()
