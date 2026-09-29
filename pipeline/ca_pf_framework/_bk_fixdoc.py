#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_fixdoc.py —— 一次性把 `BLOCK_PARAM_CLOSURE.md` 里被 `_bk_docnum.py` 抓到的
**过时数字**改掉（改完打印每一处 before/after，便于复核）。"""
import io
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(_HERE, 'BLOCK_PARAM_CLOSURE.md')

SUBS = [
    ('参数总表（由代码生成，42 条）', '参数总表（由代码生成，43 条）'),
    ('完整 42 条见', '完整 43 条见'),
    ('43 条参数每一条都有', '43 条参数每一条都有'),   # 占位，下面按实际文本再试
    ('42 条参数每一条都有', '43 条参数每一条都有'),
    ('`ΔG_v/(4γ/t) = 57`', '`ΔG_v/(4γ/t) = 57.5`'),
    ('ΔG_v/f_crit = 57', 'ΔG_v/f_crit = 57.5'),
    ('2.98e6 K/s', '2.98e6 K/s'),
]

OLD_N11 = '`n = 11` 的敏感度情景需要 7601 步（~2.7 h），**本轮未跑**。'
NEW_N11 = ('`n = 11`（α_KM = 2e-2）的敏感度情景需要 **6124 步**（≈4 h），**本轮未跑**；'
           '`n = 2`（α_KM = 5e-3）只需 **842 步**（≈40 min），已跑（`cln2`）。')

# `BLOCK_PARAM_CLOSURE.md` 里 §7 的机时条目（旧措辞）
OLD_RT = '**闭环配置一次 2853 步约 1.0–1.2 h（N=96，实测 ~1.3 s/步）。**'
NEW_RT = '**闭环配置一次 2853 步约 1.5–2 h（N=96，实测 1.6→3.6 s/步，随板条数上升）。**'


def main():
    t = io.open(P, encoding='utf-8').read()
    n = 0
    for a, b in SUBS:
        if a != b and a in t:
            t = t.replace(a, b)
            print('改了  %-46s → %s' % (a[:46], b[:46]))
            n += 1
    if OLD_N11 in t:
        t = t.replace(OLD_N11, NEW_N11)
        print('改了  §7 的 n=11 机时条目（7601 步 → 6124 步；并补 n=2 已跑）')
        n += 1
    if OLD_RT in t:
        t = t.replace(OLD_RT, NEW_RT)
        print('改了  §7 的机时条目（1.0–1.2 h → 1.5–2 h）')
        n += 1
    io.open(P, 'w', encoding='utf-8').write(t)
    print('共改 %d 处' % n)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
