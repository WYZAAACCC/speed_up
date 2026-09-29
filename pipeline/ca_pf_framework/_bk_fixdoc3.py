#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_fixdoc3.py —— 删掉 `BLOCK_STATUS.md` 里那段**被截断的重复小节**。

背景（Round 13 文档卫生检查发现）：`### 3.6b 卡死的**精化判据**` 出现了**两次**
（line 345 与 line 359），第一份在 `* 不是` 处**被截断**（复制粘贴残留），
第二份是完整的。节号自检脚本（见下面的 `_scan`）扫出了 6 处节号与所在章不符，
其中这一处是**真损坏**（其余是历史遗留的引用/旧编号）。

做法：按**内容指纹**定位要删的区间（不按行号 —— 行号会随其它编辑漂移），
删之前先打印出被删的原文供复核，删之后重新扫一遍节号。
"""
import io
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(_HERE, 'BLOCK_STATUS.md')
HDR = '### 3.6b 卡死的**精化判据**（Round 8 实测，把范围缩窄了一半）'
TAIL = '* 不是'


def scan(lines):
    sec, bad = None, []
    for i, l in enumerate(lines, 1):
        m = re.match(r'^## §(\d+)', l)
        if m:
            sec = int(m.group(1))
            continue
        m = re.match(r'^### (\d+)\.', l)
        if m and sec is not None and int(m.group(1)) != sec:
            bad.append((i, sec, l[:56]))
    return bad


def main():
    lines = io.open(P, encoding='utf-8').read().split('\n')
    idx = [i for i, l in enumerate(lines) if l.strip() == HDR]
    print('找到 %d 处同名小节标题，行号（1-based）：%s'
          % (len(idx), [i + 1 for i in idx]))
    if len(idx) != 2:
        print('⚠ 不是预期的 2 处 ⇒ 不动，人工处理')
        return 1
    a, b = idx
    # 第一份的结尾 = 第二个标题之前、最后一行内容为 `* 不是` 的位置
    tail = [i for i in range(a, b) if lines[i].strip() == TAIL]
    if not tail:
        print('⚠ 第一份里没找到截断标记 %r ⇒ 不动' % TAIL)
        return 1
    end = tail[-1]
    print('--- 将被删除的第 %d–%d 行 ---' % (a + 1, end + 1))
    for l in lines[a:end + 1]:
        print('   | ' + l)
    print('--- 删除后紧接的内容（应仍是同一个小节标题）---')
    print('   | ' + lines[end + 2])
    # ⚠ 第一版这里写成 `lines[end+1]`（那是 `* 不是` 之后的**空行**）⇒ 断言误报。
    #   删除区间是 `[a, end+1]`（含尾部空行）⇒ 删完 `lines[a]` 应正好是第二份标题。
    assert lines[end + 2].strip() == HDR, '删完应正好接上第二份'
    del lines[a:end + 2]          # 含 `* 不是` 之后的空行
    assert lines[a].strip() == HDR, '删除后新位置不是第二份标题'
    io.open(P, 'w', encoding='utf-8').write('\n'.join(lines))
    print('已删 %d 行' % (end + 2 - a))
    new = io.open(P, encoding='utf-8').read().split('\n')
    bad = scan(new)
    print('删后节号不符的行数 = %d（删前 6）' % len(bad))
    for x in bad:
        print('   line %-5d 在 §%d 里却写成 %s' % x)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
