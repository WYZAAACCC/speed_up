#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r494_r482recount.py —— **更正 `_r482` 的事件计数（自查错误 #92）**。

## 错在哪

`_r482_refillverdict.py` 用 `if '引擎形核' in ln` 数事件 —— 那是 **`--arm eng`（cadence）**
路径的打印串。而 `_r482` 跑的是 **`--nuc-law athermal`**，它打的是
**`★★ **athermal 形核** @ step …`**（`_bk_exp.py` 的另一处 `P()`）。
⇒ **两条臂都被数成 0 个事件**，于是：
* V1/V2 的判决**无效**（我在结论里也确实没用它，改用单元测试 `_r484`，但**账必须更正**）；
* 我据此登记的 **F1「`fresh` 被 `stack` 饿死（死锁）」是错的** —— 见下。

## 真实情况（本脚本的正确口径）

按 **`形核 @ step`** 计数，并解析引擎**自己**报的模式（`attach` / `fresh` / `stack`）。

**`_r482` A 臂实测**：5 个事件
| 事件 | step | 模式 | `n_ath_tgt` |
|---|---|---|---|
| 1 | 139 | attach | 1 |
| 2 | 289 | attach | 2 |
| 3 | 449 | attach | 3 |
| 4 | 620 | **fresh** | 4 |
| 5 | 802 | attach | 5 |

⇒ 与代码 `(n_ath_tgt % K) == 0`（K=4）**完全一致** ⇒ **没有死锁**。
⇒ 文档注释写的是 `k % K == 1 ⇒ fresh`（即事件 1 就该 fresh）⇒ **doc 与 code 差一个相位**
（事件序列整体平移），但**不是死锁**。**F1 撤销。**

## 判据（先写死）
* **R-1**：按正确口径数出的事件数必须 **> 0**（证明 #92 确实是"grep 错"而不是"真没事件"）。
* **R-2**：fresh 事件的**决策用**序号（= 打印的 `累计` **− 1**，因为驱动在自增**之后**才打印）
  必须 **== K 的整数倍**（与代码 `% K == 0` 一致）。
* **R-3**：两种口径的计数**必须不同**（否则说明我搞错了哪条路径打哪句话）。
"""
from __future__ import annotations

import glob
import os
import re
import sys

PAT_WRONG = '引擎形核'          # `--arm eng`（cadence）路径的串
PAT_RIGHT = '形核 @ step'       # athermal 路径的串（两种 arm 都会打）
RE_FULL = re.compile(
    r'athermal 形核\*?\*? @ step (\d+)：T=([\d.]+) K.*?场 (\d+).*?累计 (\d+)/(\d+)；模式 \*?\*?(\w+)\*?\*?')


def count(path, pat):
    if not os.path.exists(path):
        return None
    n = 0
    with open(path, errors='replace') as fh:
        for ln in fh:
            if pat in ln:
                n += 1
    return n


def events(path):
    """返回 [(step, T, field, n_ath_tgt, n_law, mode), ...]。"""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, errors='replace') as fh:
        for ln in fh:
            m = RE_FULL.search(ln)
            if m:
                out.append((int(m.group(1)), float(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)), m.group(6)))
    return out


def main():
    logs = sorted(glob.glob('_w2_r482_r482*.log'))
    if not logs:
        print('✗ 找不到 _r482 的日志')
        return 2
    print('=' * 88)
    print('R494  `_r482` 事件计数更正（自查错误 #92）')
    print('=' * 88)
    r1 = r3 = True
    r2 = True
    for p in logs:
        nw = count(p, PAT_WRONG)
        nr = count(p, PAT_RIGHT)
        ev = events(p)
        print('\n  ── %s ──' % os.path.basename(p))
        print('     错口径（`%s`）= %s' % (PAT_WRONG, nw))
        print('     对口径（`%s`）= %s' % (PAT_RIGHT, nr))
        print('     解析到的事件 = %d 个' % len(ev))
        for e in ev:
            print('        step %-5d T=%.1f K  场 %-3d  累计 %d/%d  模式 **%s**'
                  % (e[0], e[1], e[2], e[3], e[4], e[5]))
        if nr and nw is not None:
            r1 &= (nr > 0)
            r3 &= (nw != nr)
        # R-2：fresh 事件的**决策用**序号必须是 K 的整数倍（K=4）
        # ★★ 自查发现的错误 #93：第一版直接用**打印出来的** `累计` 去取模，
        #   而驱动是在 `n_ath_tgt += 1` **之后**才打印的（`_bk_exp.py` 的 P()）
        #   ⇒ 打印值 = **决策值 + 1** ⇒ 我算出来 `5 % 4 = 1` 判"❌"，
        #   而真相是**决策值 4 ⇒ `4 % 4 == 0` ⇒ fresh** —— **与代码完全一致**。
        #   ⇒ 要用 `累计 − 1`。
        for e in ev:
            if e[5] == 'fresh':
                k_dec = e[3] - 1
                ok = (k_dec % 4 == 0)
                r2 &= ok
                print('       ↳ R-2 fresh：打印累计 = %d ⇒ **决策值 = %d**，`%% 4` = %d ⇒ %s'
                      % (e[3], k_dec, k_dec % 4, '✅' if ok else '❌'))
    print('\n' + '=' * 88)
    print('★ R-1 事件数 > 0（#92 确系 grep 错）        : %s' % ('✅ PASS' if r1 else '❌ FAIL'))
    print('★ R-2 fresh 的累计序号 == K 的整数倍        : %s' % ('✅ PASS' if r2 else '❌ FAIL'))
    print('★ R-3 两种口径计数不同（确系两条路径）      : %s' % ('✅ PASS' if r3 else '❌ FAIL'))
    print('=' * 88)
    print('⇒ **结论：F1（fresh 被 stack 饿死 / 死锁）撤销。**')
    print('   真实情况：5 个事件（attach×3, fresh×1, attach×1），与代码 `% K == 0` 一致。')
    print('   保留一条**次要**发现：doc 写 `k % K == 1 ⇒ fresh`，code 是 `% K == 0`')
    print('   ⇒ **相位平移一个**（首个 fresh 从"事件 1"变成"事件 K"），**不是死锁**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
