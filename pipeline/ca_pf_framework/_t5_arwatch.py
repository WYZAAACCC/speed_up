#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_arwatch.py --- ★★★★★ **长宽比衰减报警**（补监视器缺的一路：目标②本身可能衰减）

## 为什么必须加（**实测驱动的更正**）
`t5AD_1000`（`eng-elong=10`）实测：
```
step  120 : 长宽比 **7.32**
step 1240 : 长宽比 **1.26**      ⇒ **−83%**
step 1360 : 长宽比 **1.24**
```
**⇒ 我先前"`--eng-elong` 在生长中稳定"的结论**只在 step 40–200 成立**。**
**⇒ 而原监视器只盯 ③④⑤ 的跃迁（`nblk_sig`/`nf2`/`n_var_sig`）⇒ **完全漏掉了"② 本身会衰减"**。**

## 本脚本
**每 120 s 读 `_w2_t5_ar_monitor.log`，对指定臂跟踪长宽比/长厚比；**
**只有当出现**实质变化**时才写记录**：
| 事件 | 判据（**预先写死**）|
|---|---|
| **E1 新高** | 长宽比创**该臂历史新高**（> 上次最高 + 5%）|
| **E2 显著回落** | 长宽比**从历史最高跌 > 30%**（**首次触发时报，之后每跌 10% 再报一次**）|
| **E3 跌破真实区间** | 长宽比 **< 5**（真实板条 5–20 的下沿）|
| **E4 心跳** | 每 30 分钟一条（含当前值 + 历史最高 + 跌幅）|
"""
import re
import sys
import time

LOG = '_w2_t5_ar_monitor.log'
OUT = '_w2_t5_ar_decay.log'
TAGS = (sys.argv[1] if len(sys.argv) > 1 else 't5N276,t5NR').split(',')
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 120
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 400

PAT = re.compile(r'\]\s+(\S+)\s+step\s+(\d+)\s+场=(\d+)\s+\*\*长宽比 中位 ([\d.]+).*?'
                 r'\*\*长厚比 中位 ([\d.]+)')
PHYS_LO, PHYS_HI = 5.0, 20.0      # 真实板条长宽比区间


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(OUT, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def series(tag):
    """返回该臂的 (step, ar, lt) 序列（按出现顺序）"""
    out = []
    try:
        for line in open(LOG, errors='ignore'):
            m = PAT.search(line)
            if m and m.group(1) == tag:
                out.append((int(m.group(2)), float(m.group(4)), float(m.group(5))))
    except FileNotFoundError:
        pass
    # 去重（同一 step 可能被多轮读到）
    seen, uniq = set(), []
    for s, a, l in out:
        if s not in seen:
            seen.add(s); uniq.append((s, a, l))
    return uniq


say('════ 长宽比衰减监视器启动：臂=%s，每 %d s ════' % (TAGS, GAP))
say('  判据（预先写死）：E1 新高(>+5%%) · **E2 自历史最高跌 >30%%** · E3 跌破 5 · E4 每 30 min 心跳')
peak = {}
last_beat = 0.0
for _ in range(ROUNDS):
    for tag in TAGS:
        ss = series(tag)
        if not ss:
            continue
        st, ar, lt = ss[-1]
        pk = peak.get(tag, (0.0, 0))
        if ar > pk[0] * 1.05 or pk[0] == 0.0:
            if pk[0] > 0:
                say('★E1 [%s] **长宽比新高**：%.2f → **%.2f**（step %s）· 长厚比 %.2f'
                    % (tag, pk[0], ar, st, lt))
            peak[tag] = (ar, st)
        else:
            drop = 1.0 - ar / pk[0]
            prev_drop = peak.get(tag + '_rep', 0.0)
            if drop > 0.30 and drop > prev_drop + 0.10:
                say('★E2⚠ [%s] **长宽比显著回落**：峰值 **%.2f**（step %s）→ 现 **%.2f**（step %s）'
                    '　**跌 %.0f%%**' % (tag, pk[0], pk[1], ar, st, drop * 100))
                peak[tag + '_rep'] = drop
            elif ar < PHYS_LO and pk[0] >= PHYS_LO:
                say('★E3⚠ [%s] **跌破真实区间下沿**：长宽比 **%.2f** < %.1f（step %s，峰值 %.2f）'
                    % (tag, ar, PHYS_LO, st, pk[0]))
    if time.time() - last_beat > 1800:
        for tag in TAGS:
            ss = series(tag)
            if ss:
                st, ar, lt = ss[-1]
                pk = peak.get(tag, (ar, st))
                say('  ♥ [%s] step=%s 长宽比=%.2f 长厚比=%.2f ｜ 峰值=%.2f(step %s) 跌=%.0f%%'
                    % (tag, st, ar, lt, pk[0], pk[1], max(0.0, 1 - ar / max(pk[0], 1e-9)) * 100))
        last_beat = time.time()
    time.sleep(GAP)
say('════ 监视器结束 ════')
