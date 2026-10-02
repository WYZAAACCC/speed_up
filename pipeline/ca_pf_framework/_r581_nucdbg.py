#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nucdbg.py --- ★★★★★ **形核失败**为什么**：读 `nuc_dbg.json` 的 `dbg` 拒绝计数**

## 为什么这是当前最关键的一问（R98 的结论）
R98 的逐事件时间线证明：**核只在温度档跳变时放，且每档都没放满**
（`p2_b5`：每档 3/2/4/1，而每档新名额 = `B` = 5；**末事件 step 401 ≪ 末步 600**）。
**⇒ 瓶颈是"**每档能放几个**"** ⇒ **必须知道**放不下时是**卡在哪一步**。**
**⇒ 而 `nuc_dbg.json` 的 `dbg` 字典里就有这些计数器**（R80 读到过键名）：
`att / oob / cov / exc / ok / nocand / nfsv_ok / c_shift_max_dx / edge_gap_min_dx /
attach_ok / n_events / forced_reinit`。

## 用法
  _r581_nucdbg.py [tag ...]
"""
import json
import os
import sys

ROOTS = ['_exp/_bk_p2', '_exp/_bk_mb', '_exp/_bk_mn64']
TAGS = sys.argv[1:] or ['p2_b5', 'p2_b3', 'p2_b5ov', 'A', 'B']

# 每个计数器的**中文含义**（从键名 + 源码语境推断；未核实的标 ⚠）
MEAN = {
    'att': '尝试次数（attempts）',
    'ok': '成功次数',
    'oob': '超出盒/超出允许区（out-of-bounds）',
    'cov': '覆盖率不足（coverage，F3 覆盖率）',
    'exc': '被排除（excluded，例如与已有相重叠）',
    'nocand': '★ 找不到候选（no candidate）',
    'nfsv_ok': '★ `nfsv` 成功找到空场的次数',
    'attach_ok': '`attach` 通道成功次数',
    'n_events': '事件总数',
    'forced_reinit': '被迫重初始化次数',
    'c_shift_max_dx': '最大中心偏移（胞）',
    'edge_gap_min_dx': '最小边缘间隙（胞）',
}


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, 'dry_' + tag, 'nuc_dbg.json')
        if os.path.exists(p):
            return p
    return None


def main():
    print('=' * 100)
    print('形核失败在哪一步？—— `nuc_dbg.json` 的 `dbg` 计数器')
    print('=' * 100)
    for t in TAGS:
        p = find(t)
        if not p:
            continue
        j = json.load(open(p, encoding='utf-8'))
        dbg = j.get('dbg', {})
        print()
        print('#' * 100)
        print('# 臂 %s   （`n_target_final`=%s、`n_athermal_ev`=%s、`n_events_by_mode`=%s）'
              % (t, j.get('n_target_final'), j.get('n_athermal_ev'),
                 j.get('n_events_by_mode')))
        print('#' * 100)
        if not dbg:
            print('  ⚠ `dbg` 空'); continue
        print('  %-18s %-14s %s' % ('计数器', '值', '含义（⚠ 未核实处见注）'))
        print('  ' + '-' * 90)
        for k in sorted(dbg, key=lambda x: (x not in ('att', 'ok', 'nocand', 'nfsv_ok'), x)):
            v = dbg[k]
            print('  %-18s %-14s %s' % (k, v, MEAN.get(k, '⚠ 未核实')))
    print()
    print('=' * 100)
    print('★ 判读（**预先写死**）')
    print('  · `nocand` 占大头 ⇒ **位点/空场找不到** ⇒ 正是 `_nuc_safe_mask()` 与 `m` 要解决的')
    print('  · `cov` 占大头     ⇒ **F3 覆盖率不足** ⇒ 是 S4（`--nuc-overlap-nm`）要解决的')
    print('  · `oob` 占大头     ⇒ 位点生成超出允许区 ⇒ 是位点采样的问题')
    print('  · `exc` 占大头     ⇒ 被"太近/重叠"排除 ⇒ 也是 `_nuc_safe_mask()` 的目标')
    print('  · **`ok`/`att` 之比** = 我 R94 说的"达成率"的**逐尝试**版本')
    print('=' * 100)


if __name__ == '__main__':
    main()
