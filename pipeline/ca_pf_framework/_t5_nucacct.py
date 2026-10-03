#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nucacct.py --- ★★★★★ 形核账目：何时形核 / 形了多少 / 都变成板条了吗

## 用户的问题
> "马氏体板条在刚开始的时候会有一个 **burst**……旁边也会有马氏体板条。
>  请你查一下：**什么时候形的核，形了多少核？形的核都变成马氏体板条了吗？**"

## 本脚本要算清的三件事
1. **时序**：每个温度档（step）形了几个核；
2. **总数**：`n_events` 与引擎**计划**的 `n_target` 差多少；
3. **★★ 关键：每个核是**创建了新场**还是**塞进了已有的场****
   —— 只有前者才**变成一根新板条**；后者只是**给已有板条加料**（⇒ 碎片化）。
"""
import json
from collections import Counter, defaultdict

F = '_exp/_bk_t5/dry_t5N276/nuc_dbg.json'
j = json.load(open(F))
ev = j['T_events']
dbg = j.get('dbg', {})
bymode = j.get('n_events_by_mode', {})

print('=' * 100)
print('★ t5N276 形核账目')
print('=' * 100)

# ① 时序
print('\n① 时序（按 step 聚合）')
print('   %-8s %-9s %-8s %s' % ('step', 'T(K)', '事件数', '本档的场号（* = 该场已存在）'))
seen = set()
by_step = defaultdict(list)
for e in ev:
    by_step[e['step']].append(e)
for st in sorted(by_step):
    lst = by_step[st]
    marks = []
    for e in lst:
        k = e['field']
        marks.append(('%d%s' % (k, '*' if k in seen else '')))
        seen.add(k)
    print('   %-8d %-9.1f %-8d %s' % (st, lst[0]['T'], len(lst), ' '.join(marks)))

# ② 总数
print('\n② 总数')
print('   形核事件数 n_events = **%d**' % len(ev))
print('   引擎最后的计划量 n_target = **%d**' % ev[-1]['n_target'])
print('   ⇒ 计划 %d 个核，实际落位 **%d** 个 ⇒ **差 %d 个（%.0f%% 没落位）**'
      % (ev[-1]['n_target'], len(ev), ev[-1]['n_target'] - len(ev),
         100.0 * (ev[-1]['n_target'] - len(ev)) / ev[-1]['n_target']))

# ③ ★ 关键：新场 vs 复用
seen2 = set()
new_cnt = 0
reuse = []
for e in ev:
    k = e['field']
    if k in seen2:
        reuse.append((e['step'], k, e['mode']))
    else:
        new_cnt += 1
        seen2.add(k)
print('\n③ ★★ 每个核是"创建新场"还是"塞进已有场"')
print('   **创建了新场的核 = %d 个**（每创建一个 ⇒ 多一根板条）' % new_cnt)
print('   **塞进已有场的核 = %d 个**（只给已有板条加料 ⇒ 碎片化）' % len(reuse))
print('   ⇒ 不同场号共 **%d** 个' % len(seen2))
print()
print('   复用的明细（step, 场号, 通道）：')
for st, k, m in reuse:
    print('      step %-6d 场 %-4d 通道 **%s**' % (st, k, m))

# ④ 按通道统计"新场 / 复用"
print('\n④ 按通道拆（判"哪个通道不产生新板条"）')
mc = defaultdict(lambda: [0, 0])
for e in ev:
    pass
seen3 = set()
for e in ev:
    k = e['field']
    if k in seen3:
        mc[e['mode']][1] += 1
    else:
        mc[e['mode']][0] += 1
        seen3.add(k)
print('   %-9s %-11s %-11s %s' % ('通道', '创建新场', '复用已有场', '结论'))
for m in ('attach', 'stack', 'fresh'):
    a, b = mc.get(m, [0, 0])
    note = ('**每次都创建新场** ✓' if b == 0 else
            ('**全部复用已有场** ⇒ 不产生新板条 ✗' if a == 0 else '混合'))
    print('   %-9s %-11d %-11d %s' % (m, a, b, note))

# ⑤ dbg 计数（看通道被拒的情况）
print('\n⑤ 引擎计数器（看"为什么没落位"）')
for k in ('n_events', 'ok', 'att', 'attach_ok', 'cov', 'empty', 'exc', 'oob',
          'nocand', 'sites_resampled', 'fresh_cand', 'fresh_blocked',
          'fresh_covfail', 'nfsv_ok', 'nfsv_nofield', 'forced_reinit'):
    if k in dbg:
        print('   %-18s %s' % (k, dbg[k]))
print()
print('   ⚠ `nfsv_nofield` %s' % ('**不在 dbg 里**（从未触发）'
                                 if 'nfsv_nofield' not in dbg else '= %s' % dbg['nfsv_nofield']))
