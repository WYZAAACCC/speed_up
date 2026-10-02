#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nucsteps.py --- ★★★★★ 形核事件**发生在哪些步**（决定负对照 2/3 有没有分辨力）

## 为什么要查
负对照 2（不恢 RNG）与 3（不恢 `_cnt`/`_t_since_reinit`）**没有 FAIL**。
**在下结论"它们不重要"之前，必须先证明"这一轮**根本没走到**那个状态"**
—— 否则就是把"负对照没有分辨力"误读成"那一项不必要"（本仓库 P12/P24 的陷阱）。

## 判据
* 若**所有**形核事件都发生在 **step > 10**（检查点之后）⇒ **steps 1–10 没消耗 RNG**
  ⇒ 续跑的 setup 自然给出同样的 RNG 状态 ⇒ **负对照 2 无分辨力**（**要改跑更长的窗口**）；
* 若有事件发生在 **step ≤ 10** ⇒ 负对照 2 **应当** FAIL；没 FAIL 就是**真问题**。
"""
import os
import re
import sys

LOGS = ['_w2_r581_rsmoke_rs3.log', '_w2_r581_rsmoke_rs2.log',
        '_w2_r581_neg_nc_neg2.log', '_w2_r581_neg_nc_neg3.log']
# 形核公告的几种可能写法（**先宽后窄**，中英文都抓）
PATS = [r'引擎形核\D*@?\s*step\s*(\d+)',
        r'形核\D{0,12}step\s*(\d+)',
        r'nucleat\w*\D{0,12}(\d+)',
        r'@\s*step\s*(\d+)[：:].*形核']
print('=' * 96)
print('形核事件发生在哪些步（检查点在 **step 10**）')
print('=' * 96)
for L in LOGS:
    if not os.path.exists(L):
        continue
    txt = open(L, encoding='utf-8', errors='replace').read()
    steps = []
    for p in PATS:
        steps += [int(x) for x in re.findall(p, txt)]
    steps = sorted(set(steps))
    # 只看"像步号"的（避免把温度/参数数字抓进来）
    hit = [s for s in steps if 0 <= s <= 60]
    print()
    print('  ── %s ──' % L)
    print('     抓到候选步号：%s' % (hit if hit else '（无）'))
    # 更可靠：直接找含"形核"且含 "step" 的行
    lines = [l for l in txt.split('\n') if '形核' in l and 'step' in l.lower()]
    print('     含「形核」+「step」的行 %d 条：' % len(lines))
    for l in lines[:6]:
        print('       %s' % l.strip()[:112])
    if not lines:
        # 退回：找任何含"形核"且带数字的行
        alt = [l for l in txt.split('\n') if '形核' in l][:6]
        print('     （退回：含「形核」的前 6 行）')
        for l in alt:
            print('       %s' % l.strip()[:112])
print()
print('  ★ 读法：**若全部事件都在 step > 10 ⇒ 负对照 2 无分辨力**（不是"RNG 不重要"）')
print('     ⇒ 修法：把检查点放在**形核已经发生过**的步（或跑更长的窗口）再测。')
print('=' * 96)
