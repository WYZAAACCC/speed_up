#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_dbgtab.py --- ★★★★★★ 读 `nuc_dbg.json` 的**拒绝计数器**（`oob`/`cov`/`exc`/`ok`/`nocand`）
                     ⇒ 回答"`fresh` 为什么被拒"：**位点用尽** 还是 **落位失败**（`cov`/`oob`）

## 为什么
`windowB_surface.py:1961-1979`（R481）说池子耗尽会被 `sites_refill` 补上，而各队列脚本**都传了**
`--nuc-sites-refill 1` ⇒ 池子不该空 ⇒ **拒绝只可能来自「落位失败」**（`oob`/`cov`/`exc`）。
**本脚本把那些计数器打出来。**
"""
import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B', 'C', 'D', 'E', 'F', 'G']

KEYS = ['ok', 'cov', 'oob', 'exc', 'nocand', 'att']


def main():
    print('=' * 100)
    print('`fresh` 为什么被拒：**位点用尽**（池子）还是 **落位失败**（`cov`/`oob`/`exc`）？')
    print('=' * 100)
    print(' %-5s %-8s %-8s %-8s %-8s %-8s %-8s  %s'
          % ('臂', 'ok', 'att', 'cov', 'oob', 'exc', 'nocand', 'n_events_by_mode'))
    print(' ' + '-' * 92)
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'nuc_dbg.json')
        if not os.path.exists(p):
            print(' %-5s （无 nuc_dbg.json）' % t)
            continue
        j = json.load(open(p, encoding='utf-8'))
        d = j.get('dbg', {}) or {}
        modes = j.get('n_events_by_mode', {}) or {}
        # 有些版本把 dbg 放在别的键下 ⇒ 兜底找
        if not d:
            for k, v in j.items():
                if isinstance(v, dict) and any(x in v for x in KEYS):
                    d = v
                    break
        row = [d.get(k, '—') for k in KEYS]
        print(' %-5s %-8s %-8s %-8s %-8s %-8s %-8s  %s'
              % (t, row[0], row[5], row[1], row[2], row[3], row[4], str(modes)[:34]))
    print()
    print('  ★ 判读：')
    print('   · **`cov` 或 `oob` 大** ⇒ **落位失败**（空间竞争）⇒ 杠杆是 S4 / 盒子空间，**不是** `--nuc-init`')
    print('   · **全为 0 而 `fresh` 仍被拒** ⇒ **位点池空**（R481 那条）⇒ 杠杆才是 `--nuc-init` / `--nuc-sites-refill`')
    print('   · **`nocand` 大** ⇒ 没有候选位点 ⇒ 同上')
    print('=' * 100)


if __name__ == '__main__':
    main()
