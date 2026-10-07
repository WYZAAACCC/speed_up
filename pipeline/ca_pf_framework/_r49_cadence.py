#!/usr/bin/env python3
"""R49: 快照"标称间隔"与"实际间隔"的对照。

## 背景（这是一条**口径缺陷**，不是参数没生效的小事）
`_bk_exp.py` 的旧写法把**整块 CSV + 快照**都放在
`if (it % a.every) and (it != a.steps): continue` **之后**
⇒ **快照的实际间隔 = lcm(every, snap_every)**，而不是 `snap_every`。

⚠ 修 `eff_int` 的口径（自我更正，第一版错）：
  第一版取 `diffs[0]`（最小间隔），而**末快照落在 `steps` 上**时
  会多出一个"尾巴间隔"（例如 1400→1500 = 100）⇒ 把 200 的臂误报成 100。
  **正确口径取众数**，并把"臂太短、根本没到第二个 `snap_every`"单列，
  不混进缺陷计数。
"""
import json
import os
import re
import glob
from collections import Counter

ROOTS = ['_exp/_bk_mb', '_exp/_bk_closed']


def eff_interval(steps):
    """众数间隔；并列时取最小的那个（更保守）。"""
    if len(steps) < 2:
        return None
    c = Counter(b - a for a, b in zip(steps, steps[1:]))
    top = max(c.values())
    return min(k for k, v in c.items() if v == top)


def main():
    hdr = ('%-14s %-6s %-7s %-7s %-8s %-7s %s'
           % ('arm', 'every', 'snapE', 'nominal', 'eff_int', 'n_snap', 'snap_steps'))
    print(hdr)
    bad, short, tot = [], [], 0
    for root in ROOTS:
        for d in sorted(glob.glob(root + '/*/')):
            mp = os.path.join(d, 'meta.json')
            if not os.path.exists(mp):
                continue
            m = json.load(open(mp))
            ev, se, st = m.get('every'), m.get('snap_every'), m.get('steps')
            snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
            steps = [int(re.search(r'snap_(\d+)', s).group(1)) for s in snaps]
            eff = eff_interval(steps)
            name = os.path.basename(d.rstrip('/'))
            tot += 1
            flag = ''
            if eff is None:
                flag = '  (快照不足，无法判定)'
                short.append(name)
            elif st and st < 2 * se:
                # 臂本身比两个 `snap_every` 还短 ⇒ 只有 0 和末步两个快照，
                # 这是"跑得短"，**不是** lcm 缺陷。必须分开记，否则会把
                # 缺陷数报大（第一版就是这么误伤的 dry_cln2 / dry_clsmoke）。
                flag = '  (短跑：steps=%s < 2×snap_every，只有首末两点)' % st
                short.append(name)
            elif se and eff != se:
                flag = '  <== 缺陷：实际 != snap_every'
                bad.append((name, ev, se, eff))
            print('%-14s %-6s %-7s %-7s %-8s %-7s %s%s'
                  % (name, ev, se, se, eff, len(steps), steps[:8], flag))
    print('--- 共 %d 臂：%d 条**实际间隔 != snap_every**，%d 条快照不足'
          % (tot, len(bad), len(short)))
    for b in bad:
        print('    缺陷: %-14s every=%-5s snap_every=%-6s 实际=%-6s (lcm=%s)'
              % (b[0], b[1], b[2], b[3], _lcm(b[1], b[2])))
    return 0 if not bad else 1


def _lcm(a, b):
    from math import gcd
    return a * b // gcd(a, b) if a and b else None


if __name__ == '__main__':
    raise SystemExit(main())
