#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_t28_idx.py --- 同步 `T28_verify_geomAR.py` 的元组索引（Round 139）

`geom_ar()` 的返回元组从 5 元扩到 7 元：
    旧 (k, L_, t_,  L_/t_,       cells)        ⇒ t_ 在 v[2]
    新 (k, L_, W_, t_, L_/t_, L_/W_, cells)    ⇒ t_ 在 **v[3]**、W_ 在 v[2]

`T28` 是 `geom_ar` 的**正对照**，用了 3 处 `v[2]` 取厚度 ⇒ 不同步就会
**静默拿"宽"当"厚"比**（AGENTS §3.24「改一半」陷阱）。
本脚本：① 插入 `T_of/W_of/LW_of` 取槽工具；② 把 3 处 `v[2]` 改成 `T_of(v)`；
③ 就地记录这次同步；④ 断言替换条数（找不到就 FAIL，不静默跳过）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, 'T28_verify_geomAR.py')
s = open(p, encoding='utf-8').read()

OLD_HDR = '''    # `geom_ar` 用 `atab[k]` 当长轴、`NPF[k]` 当厚度轴 ⇒ 这里照真接口调用
    return g, geom_ar(g.region(), g, NPF)'''
NEW_HDR = '''    # `geom_ar` 用 `atab[k]` 当长轴、`NPF[k]` 当厚度轴 ⇒ 这里照真接口调用
    # ⚠⚠ Round 139：`geom_ar` 的返回元组**已扩为 7 元**
    #    旧 (k, L_, t_, L_/t_, cells)            =>  t_ 在 v[2]
    #    新 (k, L_, W_, t_, L_/t_, L_/W_, cells)  =>  t_ 在 **v[3]**、W_ 在 v[2]
    #   ⇒ 本文件所有取厚度的 `v[2]` 必须改成 `v[3]`；不改会**静默**拿"宽"当"厚"比。
    #   本文件是 `geom_ar` 的正对照 ⇒ 索引必须与实现同步（AGENTS §3.24「改一半」）。
    return g, geom_ar(g.region(), g, NPF)


# ★ 统一取槽位的小工具（以后再改元组长度时只改这里，避免又散落 v[2]/v[3]）
def T_of(rec):
    """沿 `npref` 的厚度（新元组 v[3]）。"""
    return rec[3]


def W_of(rec):
    """沿 `npref × a` 的宽度（新元组 v[2]）。"""
    return rec[2]


def LW_of(rec):
    """几何长:宽（新元组 v[5]）—— **靶② 只认这个**。"""
    return rec[5]'''

REPL = [
    ('t1 = [v[2] for v in a1]', 't1 = [T_of(v) for v in a1]'),
    ('t2 = [v[2] for v in a2]', 't2 = [T_of(v) for v in a2]'),
    ('all(abs(v[2] / T - 1.0) <= 0.10 for v in a3)',
     'all(abs(T_of(v) / T - 1.0) <= 0.10 for v in a3)'),
    ("['%.1f' % (v[2] * 1e9) for v in a3]", "['%.1f' % (T_of(v) * 1e9) for v in a3]"),
]

ok = True
if s.count(OLD_HDR) != 1:
    print('FAIL: 头部锚点出现 %d 次（应为 1）' % s.count(OLD_HDR)); ok = False
else:
    s = s.replace(OLD_HDR, NEW_HDR)

for old, new in REPL:
    n = s.count(old)
    if n != 1:
        print('FAIL: 锚点 %r 出现 %d 次（应为 1）' % (old[:50], n)); ok = False
        continue
    s = s.replace(old, new)
    print('OK   %s  ->  %s' % (old[:52], new[:52]))

left = s.count('v[2]')
print('\n残留 `v[2]`（应只剩新头部注释与 …）: %d' % left)
for i, ln in enumerate(s.split('\n'), 1):
    if 'v[2]' in ln:
        print('   :%d  %s' % (i, ln.strip()[:110]))

if not ok:
    print('\n⛔ 有锚点未命中 ⇒ **未写回**（避免半途状态）'); sys.exit(1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('\n已写回 %s' % p)
