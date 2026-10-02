#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_handoff.py --- 更新「接手须知」里判据 ④⑥ 那一行（§108 已把答案查明）

## 为什么必须更新
「接手须知」现在写着判据 ④⑥ 的判定点是"**第 23 个形核事件**"，
**而那个点已经在 §106 到达、且答案已在 §108 查明**（`fresh` 被拒）。
**⇒ 若不更新，接手的会话会去**白等一个已经过去的判定点**。**
"""
import re
import sys

P = 'R581_T5_RESTART.md'
src = open(P, encoding='utf-8').read()
orig = src

old = ("| **④ 块间影响** | **待验** | 判定点 = **第 23 个形核事件**"
       "（`K = n(T_end) = 23` ⇒ 那时才有第一个 `fresh` 事件 = 新块）。"
       "判据：`n_var_sig` 应 >1、`nblk_sig` 应 ≥2 |")
new = ("| **④ 块间影响** | **真因已查明（§108，直接证据）** | "
       "**`fresh` 通道每次尝试都被拒**（事件 #24：23 个 attach + 1 次 fresh 被拒；"
       "abA 同期 **5 个 fresh 成功**）⇒ `n_var_sig`=1、`nblk_sig`=1。"
       "**⇒ 下一步 = 判「系统性」：等事件 47/70（不需改代码，~3.5 h）** |")

if old in src:
    src = src.replace(old, new, 1)
    print('  ✅ 已更新判据 ④ 那一行')
else:
    # 退而求其次：只改"判定点"那句里的关键短语（防止空白差异）
    m = re.search(r"判定点 = \*\*第 23 个形核事件\*\*[^|]*", src)
    if m:
        src = src[:m.start()] + ("**真因已查明（§108，直接证据）**：`fresh` 被拒"
                                 "（事件 #24：23 attach + 1 次 fresh 被拒；abA 有 5 个 fresh 成功）"
                                 "⇒ **下一步 = 判「系统性」，等事件 47/70（~3.5 h）** ") + src[m.end():]
        print('  ✅ 已用回退方式更新（关键短语替换）')
    else:
        print('  ⚠ 没找到目标文本 ⇒ **未改动**（请人工核对）')

if src != orig:
    open(P, 'w', encoding='utf-8').write(src)
    print('  已写回 %s（%d 行）' % (P, src.count('\n') + 1))
else:
    print('  未改动')

# ── 验证 ──
s2 = open(P, encoding='utf-8').read()
print()
print('  ── 验证 ──')
print('    仍含过时的"判定点 = 第 23 个形核事件" = %s ⇒ %s'
      % ('判定点 = **第 23 个形核事件**' in s2,
         '❌ 未更新' if '判定点 = **第 23 个形核事件**' in s2 else '✅ 已清除'))
print('    含新结论"真因已查明" = %s' % ('真因已查明' in s2))
print('    文档仍是 markdown 表格结构（含接手须知标题） = %s'
      % ('# ★★★★★ 接手须知' in s2))
