#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_freshwatch.py --- ★★★★★ 「fresh 通道」监视器（④⑤ 的**直接前兆**）

## 为什么必须加（**本轮的关键发现**）
我先前查错了日志文件（`_w2_t5_n276.log` 只有 709 字节，是启动器日志），
**用 `readlink /proc/<pid>/fd/1` 找到真正的引擎 stdout 后**，得到**直接证据**：
```
t5N276 形核模式统计：16 × attach · 4 × stack · **0 × fresh**
事件进度：累计 **21/23**（T_6 @ step 501、T_7 @ step 601 …）
```
**⇒ 判据④（块间影响）与⑤（自协调）**唯一依赖 `fresh`**（只有它能造新变体/新块）。
**⇒ 所以 ④⑤ 不出现的原因不是"没到时候"，而是 `fresh` **一次都没触发**。**
**⇒ 而 `fresh` 的计数**比块表更早、更灵敏** ⇒ 应作为**第一类前兆量**持续监控。**

## 本脚本
每 `GAP` 秒从 `_w2_t5_short_<tag>.log`（**引擎 stdout，3 MB 级那个**）统计：
* `attach` / `stack` / **`fresh`** 的模式计数；
* `athermal 形核` 公告总数与**最新一条的累计进度**（`累计 k/23`）；
**⇒ 只在 **fresh 首次出现** 或 **模式计数变化** 时写记录；每 30 min 一条心跳。**
"""
import os
import re
import sys
import time

TAGS = (sys.argv[1] if len(sys.argv) > 1 else 't5N276,t5NR').split(',')
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 120
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 400
OUT = '_w2_t5_fresh.log'

MODE = re.compile(r'模式 \*\*([a-z]+)\*\*')
ACC = re.compile(r'累计 (\d+)/(\d+)')


def logpath(tag):
    return '_w2_t5_short_%s.log' % tag


def scan(tag):
    p = logpath(tag)
    cnt = {}
    acc = None
    nev = 0
    try:
        with open(p, errors='ignore') as f:
            for line in f:
                if '形核' in line:
                    nev += 1
                    m = ACC.search(line)
                    if m:
                        acc = (int(m.group(1)), int(m.group(2)))
                    for mm in MODE.finditer(line):
                        cnt[mm.group(1)] = cnt.get(mm.group(1), 0) + 1
    except FileNotFoundError:
        return None
    return dict(cnt=cnt, acc=acc, nev=nev, size=os.path.getsize(p) if os.path.exists(p) else 0)


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(OUT, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


say('════ fresh 通道监视器启动：臂=%s，每 %d s ════' % (TAGS, GAP))
say('  数据源：`_w2_t5_short_<tag>.log`（**引擎 stdout** —— 不是启动器日志 `_w2_t5_<tag>.log`）')
say('  报警：**fresh 首次出现** · 模式计数变化 · 每 30 min 心跳')
prev, last_beat = {}, 0.0
for _ in range(ROUNDS):
    for tag in TAGS:
        s = scan(tag)
        if s is None:
            continue
        c = s['cnt']
        old = prev.get(tag, {})
        if c != old:
            fr = c.get('fresh', 0)
            old_fr = old.get('fresh', 0)
            if fr > old_fr:
                say('★★★ [%s] **`fresh` 通道首次/再次触发**！fresh=%d（attach=%d stack=%d）'
                    '　事件累计=%s　⇒ **新变体/新块的前提启动了**'
                    % (tag, fr, c.get('attach', 0), c.get('stack', 0), s['acc']))
            else:
                say('  [%s] 模式计数变化：attach=%d stack=%d fresh=%d　事件累计=%s'
                    % (tag, c.get('attach', 0), c.get('stack', 0), fr, s['acc']))
            prev[tag] = dict(c)
    if time.time() - last_beat > 1800:
        for tag in TAGS:
            s = scan(tag)
            if s:
                c = s['cnt']
                say('  ♥ [%s] attach=%d stack=%d **fresh=%d**　事件累计=%s　⇒ %s'
                    % (tag, c.get('attach', 0), c.get('stack', 0), c.get('fresh', 0), s['acc'],
                       '**fresh 已启动**' if c.get('fresh', 0) else '**fresh 尚未启动**（④⑤ 的前兆未到）'))
        last_beat = time.time()
    time.sleep(GAP)
say('════ 监视器结束 ════')
