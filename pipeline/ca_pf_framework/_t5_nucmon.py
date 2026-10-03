#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nucmon.py --- ★★★★★ 形核账目监控（覆盖**新增的三项目标**）

## 对应用户目标（原话）
> **「监控形核的**数量与时间**，监控马氏体的**数量是否足够多**，
>   监控多个马氏体板条有**没有正确对应到各自的场中**」**

## 三项各自的量具（**判据预先写死**）
| 目标 | 量 | 判据 |
|---|---|---|
| **形核的数量与时间** | 每档（step/T）的事件数、累计事件数、模式分布 | 报**逐档表**；事件数应追上 `n_target` |
| **马氏体数量是否足够多** | `nslab_n` vs `n_target`（引擎目标）| **达成率 = nslab_n / n_target**；t5N276 只有 **19/66 = 29%** |
| **板条是否正确对应到各自场** | **唯一性 = 不同场号 / 事件数** | **≈1.0 正确**；t5N276 = **0.56**（⇒ 15 次复用场）|

## 数据源（**注意：用真引擎 stdout**）
* `_w2_t5_short_<tag>.log`（**3 MB 级那个**）—— 形核事件逐条;
* `_exp/_bk_t5/dry_<tag>/series.csv` —— `nslab_n`;
* 跑完后 `<dir>/nuc_dbg.json` —— 权威账目。
"""
import csv
import os
import re
import sys
import time

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 180
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 400
LOG = '_w2_t5_short_%s.log' % TAG
CSV = '_exp/_bk_t5/dry_%s/series.csv' % TAG
OUT = '_w2_t5_nucmon_%s.log' % TAG

# 「★★ **athermal 形核** @ step 501：T=729.2 K（…），df=…，场 13（累计 18/23；模式 **attach**…）」
RX = re.compile(r'@ step (\d+)：T=([\d.]+) K.*?场 (\d+)（累计 (\d+)/(\d+)；模式 \*\*([a-z]+)\*\*')
# 引擎形核（另一条打印）
RX2 = re.compile(r'引擎形核 \*?\*? @ step (\d+)：场 (\d+)（变体 V(\d+)），模式 ([a-z]+)')


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(OUT, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def scan():
    ev = []
    try:
        with open(LOG, errors='ignore') as f:
            for line in f:
                m = RX.search(line)
                if m:
                    ev.append(dict(step=int(m.group(1)), T=float(m.group(2)),
                                   field=int(m.group(3)), acc=int(m.group(4)),
                                   tot=int(m.group(5)), mode=m.group(6)))
                    continue
                m2 = RX2.search(line)
                if m2:
                    ev.append(dict(step=int(m2.group(1)), T=float('nan'),
                                   field=int(m2.group(2)), acc=-1, tot=-1,
                                   mode=m2.group(4)))
    except FileNotFoundError:
        return None
    return ev


def total_target():
    """★ 从横幅读**全盒目标** `B·n(T_end)`（不是每块的 `n`）。

    为什么（**我第一版的缺陷**）：事件行里的「累计 k/23」中的 23 是 **`n(T_end)` = 每块根数**，
    而全盒目标是 **`B · n` = 3 × 23 = 69** ⇒ 拿 23 当分母会**高估达成率 3 倍**。
    横幅里的原句（`_t5_short.py` 打印）：
        `总根数 = B · n(T_end) = 3 × 23 = **69 根**`
    """
    try:
        with open(LOG, errors='ignore') as f:
            for line in f:
                m = re.search(r'总根数\s*=\s*B\s*·\s*n\(T_end\)\s*=\s*(\d+)\s*×\s*(\d+)\s*=\s*\*{0,2}(\d+)', line)
                if m:
                    return int(m.group(3)), int(m.group(1)), int(m.group(2))
    except FileNotFoundError:
        pass
    return None, None, None


def nslab():
    try:
        rows = list(csv.DictReader(open(CSV, newline='')))
        if not rows:
            return None, None
        return rows[-1].get('step'), rows[-1].get('nslab_n')
    except Exception:
        return None, None


say('════ 形核账目监控：%s（每 %d s）════' % (TAG, GAP))
say('  三项：①形核数量与时间 ②马氏体数量是否够 ③板条是否对应到各自的场')
say('  ★ 判据：唯一性（不同场/事件）≈1.0 为正确；t5N276 修复前 = **0.56**')
last_n = -1
for _ in range(ROUNDS):
    ev = scan()
    if ev:
        n = len(ev)
        fields = [e['field'] for e in ev]
        uniq = len(set(fields))
        ratios = uniq / n
        modes = {}
        for e in ev:
            modes[e['mode']] = modes.get(e['mode'], 0) + 1
        st, ns = nslab()
        tgt = ev[-1]['tot'] if ev and ev[-1]['tot'] > 0 else None
        if n != last_n:
            last_n = n
            say('  ── 事件 %d 个 ｜ step=%s ｜ nslab_n=%s ──' % (n, st, ns))
            say('     ① 形核：模式分布 %s ｜ 最后事件 step=%d T=%.1f'
                % (modes, ev[-1]['step'], ev[-1]['T']))
            say('     ③ **唯一性 = %d/%d = %.2f** ⇒ %s'
                % (uniq, n, ratios,
                   '✅ 一根板条一个场' if ratios >= 0.95 else
                   ('⚠ 部分复用场' if ratios >= 0.8 else '❌ **有场被复用**')))
            if tgt:
                # ★ 用**全盒目标** B·n（从横幅读）当分母，而不是事件行里的 n(T_end)（每块根数）
                _tot, _B, _n = total_target()
                _den = _tot if _tot else tgt
                try:
                    rate = float(ns) / _den if ns else 0.0
                except Exception:
                    rate = 0.0
                say('     ② 数量：nslab_n=%s / **全盒目标 %s**（B=%s × n=%s）⇒ **达成率 %.0f%%**'
                    % (ns, _den, _B, _n, rate * 100))
            if uniq < n:
                re_ = [e for i, e in enumerate(ev)
                       if e['field'] in {x['field'] for j, x in enumerate(ev) if j < i}]
                say('     ⚠ 复用明细（末 6 条）：%s'
                    % [(e['step'], e['field'], e['mode']) for e in re_[-6:]])
    time.sleep(GAP)
say('════ 监控结束 ════')
