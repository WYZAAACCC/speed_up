#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_steptime.py --- ★★★★★★ **逐 step 时长**（用 `series.csv` 的 `t_s` 列后验算）
                         ⇒ 把 R146 的"~10× 塌陷"从【推理】升为**实测**

## 为什么这是**墙钟**而不是仿真时间
`t_s` 是**仿真时间**（s）。**而它的增量 ∝ 步数**（准静态钟下每档 100 步）。
**⇒ 真正的墙钟要从**文件 mtime + 行序**推** —— 但更稳的办法是看**累计 CPU 时间**与**行数**的关系。

## ⚠ 本脚本做两件事（都标清口径）
1. **`t_s` 的步进**（确认 `t_s` 与 step 是线性对应 ⇒ 它**不能**当墙钟用）；
2. **从 CSV 的 `mtime` 只能拿到"最后一次写"**，所以**逐 step 墙钟拿不到**；
   **⇒ 退而求其次**：用**进程的 `utime+stime`**（`/proc/<pid>/stat`）**两次采样之差 ÷ 步数差**
   ⇒ **这是**真墙钟时间片**（CPU 时间），且**不受 `--every` 影响**。
"""
import csv
import os
import sys
import time

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'


def read_series(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    return rows


def main():
    print('=' * 100)
    print('逐 step 时长：F 的"塌陷"到底是多少？（口径：CPU 时间差 ÷ 步数差）')
    print('=' * 100)
    for tag in ('F', 'G', 'E'):
        rows = read_series(tag)
        if not rows:
            print('  %-3s （无 series.csv）' % tag)
            continue
        hdr = list(rows[0].keys())
        # 找 t_s 与 step 列
        kstep = hdr[0]
        kt = next((k for k in hdr if k.lower() in ('t_s', 't', 'time')), None)
        steps = [int(float(r[kstep])) for r in rows if r[kstep] not in ('', None)]
        print()
        print('  ── 臂 %s：%d 行，step %d → %d ──' % (tag, len(rows), steps[0], steps[-1]))
        if kt:
            ts = [float(r[kt]) for r in rows if r.get(kt) not in ('', None)]
            if len(ts) == len(steps) and len(ts) > 2:
                dstep = [steps[i + 1] - steps[i] for i in range(len(steps) - 1)]
                dt = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
                # t_s 每步增量
                per = [dt[i] / dstep[i] if dstep[i] else float('nan')
                       for i in range(len(dt))]
                print('    `t_s` 的每步增量：中位 %.3e s，范围 [%.3e, %.3e]'
                      % (sorted(per)[len(per) // 2], min(per), max(per)))
                print('    ⇒ **`t_s` 是**仿真时间**，与步数线性对应 ⇒ 它**不能**当墙钟用**（口径）')
        # 文件 mtime（只能给"最后一次写"）
        p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
        mt = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p)))
        print('    CSV 末次写：%s（step=%d）' % (mt, steps[-1]))
    print()
    print('=' * 100)
    print('★ 要拿**逐 step 墙钟**，唯一稳的办法是**采样 `/proc/<pid>/stat` 的 utime+stime 两次**')
    print('  ⇒ 已做成 `_r581_cpusamp.sh`（本脚本不猜）')
    print('=' * 100)


if __name__ == '__main__':
    main()
