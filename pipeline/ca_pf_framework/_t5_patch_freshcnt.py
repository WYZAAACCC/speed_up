#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_freshcnt.py --- s294：修 s293 的**计数器缺陷**（退回 stack 也被记成 fresh）。

## 缺陷（**我自己的，实测抓到**）
s293 写的是
```python
if _ev:
    ...
    if _nf > 0:
        n_fresh_ok += 1
```
而 `_bk_exp.py` 在 `fresh` 被拒时会**退回 `stack`** 并把那次算作成功：
```python
if _nf > 0 and not _ev and _ns == 0:
    _ev = g.nucleate(..., n_fresh=0, n_stack=1, ...)
```
⇒ **退回的那次也被记进 `n_fresh_ok`** ⇒ 3 次失败后 `n_fresh_ok == B == 3`
⇒ `_fresh_now = (n_fresh_ok < _Bt)` **永久为假** ⇒ **再也不请求 fresh** ⇒ 块数永远是 1。

实测（`t5ETAo`，step 100）：
```
fresh 被拒退回 stack = 3
事件 #2 / #3 / #4 全部「fresh 被拒 ⇒ 退回 stack」
模式分布：5 × attach
nblk_sig = 1、n_var_sig = 1、blk_laths = 3   ← 判据 1 FAIL
```

## 修法
**只有引擎真的报了 `fresh` 模式**才算建了一个新块：
```python
if _nf > 0 and str(_ev[0][1]) == 'fresh':
    n_fresh_ok += 1
```
⇒ 每次失败都不消耗"建块预算"，引擎会**继续重试** `fresh`
（而引擎侧本身已有正确的解卡机制：`windowB_surface.py:2212` 在一个位点都没放成时
 **重抽整张位点表** —— R481b 的更正，见 `:2193-2210`）。

## 惰性
`--nuc-block-parallel 0`（默认）⇒ `n_fresh_ok` 不被读 ⇒ 归档路径逐位不变 ✓
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

OLD = """                    # ★ s293：只有**成功**且**要的是 fresh** 才记一个新块
                    if _nf > 0:
                        n_fresh_ok += 1
"""

NEW = """                    # ★★★★★★ s294 修（**s293 的计数器缺陷**，实测抓到）
                    #   s293 写的是 `if _nf > 0:`，而下面这条**退回**路径
                    #   （`:2672` 一带）在 `fresh` 被拒时会改用 `stack` 并把那次算成功：
                    #       `if _nf > 0 and not _ev and _ns == 0: _ev = nucleate(n_fresh=0, n_stack=1)`
                    #   ⇒ **退回的那次也被记进 `n_fresh_ok`** ⇒ 3 次失败后 `n_fresh_ok == B`
                    #   ⇒ `_fresh_now = (n_fresh_ok < _Bt)` **永久为假**
                    #   ⇒ **再也不请求 fresh** ⇒ 块数永远 = 1。
                    #   实测（`t5ETAo` step 100）：`fresh 被拒退回 stack = 3`、
                    #   事件 #2/#3/#4 全退回、模式 5 × attach、`nblk_sig = 1`（判据 1 FAIL）。
                    #   ## 修法（**只有引擎真的报 `fresh` 才算建了一个新块**）
                    #   ⇒ 每次失败都**不消耗**建块预算 ⇒ 引擎继续重试 `fresh`；
                    #     引擎侧本身已有正确的解卡机制（`windowB_surface.py:2212`：
                    #     一个位点都没放成时**重抽整张位点表**，见 R481b 的更正 `:2193-2210`）。
                    #   ⚠ 惰性：`--nuc-block-parallel 0` ⇒ `n_fresh_ok` 不被读 ⇒ 逐位不变 ✓
                    if _nf > 0 and str(_ev[0][1]) == 'fresh':
                        n_fresh_ok += 1
"""


def main():
    with open(SRC, "r", encoding="utf-8") as fh:
        t = fh.read()
    n = t.count(OLD)
    print("  锚点出现 %d 次 %s" % (n, "✓" if n == 1 else "❌"))
    if n != 1:
        print("❌ 锚点不唯一 ⇒ 拒绝写入")
        return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(OLD, NEW, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = SRC + ".s294tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc)
        os.remove(tmp)
        return 1
    os.remove(tmp)
    bak = SRC + ".bak_s294freshcnt"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    # ⚠ 复验锚点用**代码行**（避开本补丁自己注释里的同名字面串）
    checks = [
        (t3.count("\n                    if _nf > 0 and str(_ev[0][1]) == 'fresh':") == 1,
         "受控条件 1 处"),
        (t3.count("\n                        n_fresh_ok += 1") == 1, "自增 1 处"),
        ("if _nf > 0:\n                        n_fresh_ok" not in t3, "旧的裸 `if _nf > 0:` 已消失"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-28s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s294 计数器修复完成（`--nuc-block-parallel` 门控；默认档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
