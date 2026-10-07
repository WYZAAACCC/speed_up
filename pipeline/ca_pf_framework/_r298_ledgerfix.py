#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r298_ledgerfix.py —— 精化台账自查 + **给真正被撤回的旧节补就地指针**。

## 为什么要精化（`_r297` 的判据有假阳性）
`_r297` 把"**做出**更正的节"也当成了"被更正的节"。
例：`§98` 的标题就是"**更正 §95**" ⇒ 被更正的是 **§95**，不是 §98。

**⇒ 精化判据**：只有**被点名的节号 < 当前节号**时，才算"T 被 S 撤回"。
并排除"T 本身就是 S 的更正对象、且 S 已带指针"的情形。

## 动作
对每个**真阳性** (T 被 S 撤回、而 T 正文无指针) ⇒
**在 T 的标题行之后插入一行指针**：
    > ⚠ **本节已被 `§S` 撤回/更正（补记）** —— 详见该节。
⚠ **补记**：老节（`§22`/`§76`/`§82`/`§86`/`§95` 等）写作时本仓库还没有"就地打指针"的惯例，
本轮**统一补齐**，避免读者读到前文时拿到已被推翻的结论。
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')

SECLINE = re.compile(r'^## (§\d+)[^\n]*$', re.M)
NAMES = re.compile(r'(撤回|更正|收窄|作废|推翻)\s*(?:了)?\s*`?(§\d+)`?')
# ★ 修（**第 27 个自查错误**）：第一版的 POINTER 只认**单个**目标节号
#   （`已被 \`§A\` 撤回`）；而本轮补记里有"`§138`/`§141`"这种**多目标**写法
#   ⇒ 正则匹配不到 ⇒ **复跑时把 §137 误报成"仍无指针"**（假阳性）。
#   ⇒ 改成：`已被` 后面允许出现**一串** `§数字`（可带反引号/斜杠/顿号分隔），
#     只要最后跟撤回类动词即可。
POINTER = re.compile(
    r'(已被|本条已被)\s*[`§\d/\s、,，]*§\d+[`\d/\s、,，]*\s*'
    r'(撤回|更正|收窄|作废|推翻|补记)')


def num(s):
    return int(s[1:])


def main():
    txt = io.open(LED, encoding='utf-8').read()
    lines = txt.split('\n')
    # 节边界（行号）
    secs = []
    for i, L in enumerate(lines):
        m = SECLINE.match(L)
        if m:
            secs.append((m.group(1), i))
    secs.append(('__END__', len(lines)))
    print('=' * 104)
    print('_r298 —— 精化自查 + 给真阳性的旧节补就地指针')
    print('=' * 104)
    print('  共 %d 个节' % (len(secs) - 1))

    # 找真阳性：T 被 S 撤回，且 S > T，且 T 无指针
    pairs = {}      # T -> set(S)
    for k in range(len(secs) - 1):
        sid, start = secs[k]
        end = secs[k + 1][1]
        body = '\n'.join(lines[start:end])
        for m in NAMES.finditer(body):
            T = m.group(2)
            if T.startswith('§') and T in [s for s, _ in secs]:
                if num(T) < num(sid) and T != sid:
                    pairs.setdefault(T, set()).add(sid)
    print()
    print('  ## 真阳性候选（被**更晚**的节点名撤回）')
    real = []
    for T in sorted(pairs, key=num):
        Ss = sorted(pairs[T], key=num)
        # T 正文是否已有指针
        idx = [i for (s, i) in secs if s == T][0]
        end = secs[[s for s, _ in secs].index(T) + 1][1]
        body = '\n'.join(lines[idx:end])
        has = bool(POINTER.search(body))
        title = lines[idx][:66]
        print('     %-8s ← %-22s 指针=%s  %s'
              % (T, ','.join(Ss), '有' if has else '**无**', title))
        if not has:
            real.append((T, Ss, idx))
    print()
    print('  ⇒ **真阳性（需补指针）= %d 个**：%s'
          % (len(real), [t for (t, _, _) in real]))
    if not real:
        print('  ✅ 无需修改')
        return 0

    # 插入指针（从后往前插，避免行号位移）
    real.sort(key=lambda x: -x[2])
    ins = 0
    for (T, Ss, idx) in real:
        note = ('> ⚠ **本节已被 `%s` 撤回/更正（**补记**）** —— 详见该节。\n'
                '> （补记说明：老节写作时本仓库尚无"就地打指针"的惯例，本轮统一补齐，\n'
                '>   以免读者读到前文时拿到已被推翻的结论。）\n'
                % '`/`'.join(Ss))
        if POINTER.search(lines[idx + 1] if idx + 1 < len(lines) else ''):
            continue
        lines.insert(idx + 1, note.rstrip('\n'))
        ins += 1
        print('     ✅ 已在 %s 标题后插入指针（指向 %s）' % (T, ','.join(Ss)))
    out = '\n'.join(lines)
    assert '\t' not in out, '插入了制表符？'
    with io.open(LED, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    print()
    print('  ⇒ 共插入 %d 处指针；台账 %d 行 → **%d 行**'
          % (ins, txt.count('\n') + 1, out.count('\n') + 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
