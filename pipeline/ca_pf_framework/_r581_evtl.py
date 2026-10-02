#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_evtl.py --- ★★★★★ **事件**时间线**：`p2_b5` 的 10 个事件是**停了**还是**步数不够**？

## 为什么这是关键问题（R94 的 40% 达成率）
R94 实测：`p2_b5` 的 `_tgt` = **25**，而 `n_athermal_ev` 只有 **10** ⇒ 我把它读成"**达成率 40%**"。
**但两种解释都说得通，而它们的处方**完全相反**：**
| 解释 | 含义 | 处方 |
|---|---|---|
| **A. 事件停了**（目标还在，但放不进去） | 达成率是**硬上限** | **提高位点可用性**（`_nuc_safe_mask` / S4 / `m`） |
| **B. 步数不够**（事件还在陆续放，只是没跑完） | 达成率只是**进度** | **跑更久**（加 `--steps`），与位点无关 |

**⇒ 判据（预先写死）：看 `T_events` 里**最后一个事件的 step**与**日志最后一步**的关系：**
* **末事件 step ≈ 最后一步**（且事件间隔**没有明显拉长**）⇒ **B（还在放）**；
* **末事件 step ≪ 最后一步**（后面一长段**一个都没放**）⇒ **A（停了）**。

## 用法
  _r581_evtl.py <tag> [root]
"""
import json
import os
import sys

TAG = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
ROOTS = ['_exp/_bk_p2', '_exp/_bk_mb', '_exp/_bk_mn64']
if len(sys.argv) > 2:
    ROOTS = [sys.argv[2]]


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, 'dry_' + tag, 'nuc_dbg.json')
        if os.path.exists(p):
            return p, r
    return None, None


def main():
    p, r = find(TAG)
    print('=' * 96)
    print('事件时间线：`%s`（%s）' % (TAG, r or '找不到'))
    print('=' * 96)
    if not p:
        print('  ❌ 无 `nuc_dbg.json`'); return
    j = json.load(open(p, encoding='utf-8'))
    cfg = j.get('nuc_cfg', {})
    vg = {int(a): int(b) for a, b in cfg.get('vgroup', {}).items()}
    ev = j.get('T_events', [])
    nt = j.get('n_target_final', '?')
    print('  `n_target_final` = %s ；`n_athermal_ev` = %s ；事件条数 = %d'
          % (nt, j.get('n_athermal_ev'), len(ev)))
    print('  `n_events_by_mode` = %s' % j.get('n_events_by_mode'))
    if not ev:
        print('  ⚠ `T_events` 空'); return
    print()
    print('  %-4s %-8s %-6s %-6s %-9s %-10s %s'
          % ('#', 'step', 'field', '变体', 'Δstep', 'mode', 'T(K)'))
    prev = None
    steps = []
    for i, e in enumerate(ev, 1):
        s = int(e.get('step', -1)); steps.append(s)
        f = int(e.get('field', -1))
        d = ('%+d' % (s - prev)) if prev is not None else '—'
        print('  %-4d %-8d %-6d %-6s %-9s %-10s %.1f'
              % (i, s, f, 'V%d' % vg.get(f, -1), d, e.get('mode'), float(e.get('T', 0))))
        prev = s
    print()
    print('  ── 判读 ──')
    print('  首事件 step = %d ；末事件 step = %d' % (steps[0], steps[-1]))
    if len(steps) > 2:
        gaps = [steps[i + 1] - steps[i] for i in range(len(steps) - 1)]
        print('  事件间隔（step）：%s' % gaps)
        first_half = gaps[:len(gaps) // 2]
        last_half = gaps[len(gaps) // 2:]
        m1 = sum(first_half) / len(first_half) if first_half else 0
        m2 = sum(last_half) / len(last_half) if last_half else 0
        print('  前半平均间隔 = %.1f ；后半平均间隔 = %.1f ；比值 = %.2f'
              % (m1, m2, (m2 / m1) if m1 else float('nan')))
    print()
    print('  ⚠ **本量具不知道**日志最后跑到第几步** ⇒ 请与 `_w2_r581_p2_%s.log` 的末 step 对照：' % TAG)
    print('     · 末事件 step ≈ 日志末 step（且间隔没拉长）⇒ **B：还在放，只是步数不够**')
    print('     · 末事件 step ≪ 日志末 step（后面一大段没放）⇒ **A：停了，是硬上限**')
    print('=' * 96)


if __name__ == '__main__':
    main()
