#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_dbgprint.py --- s295：把引擎的**形核分诊计数**接出来（纯量具，不改数值）。

## 为什么必须接（用户硬约束「尤其需要注意量具的正确性」）
s293/s294 让「块数 = B」的规则正确工作（`fresh` 请求次数不再被错误消耗），
但实测 **`fresh` 每次都被拒**：
```
t5FIX  成功=6  fresh 被拒退回 stack=6
t5BKMo 成功=5  fresh 被拒退回 stack=5
t5ETAo 成功=2  fresh 被拒退回 stack=2
```
⇒ 修法**卡死在引擎里**，而引擎**自己就有**分诊计数，却**一个都没打印**：
* `dbg['fresh_exc']`      —— `windowB_surface.py:2183`（`seed_plate` 抛异常；注释指明
                             典型原因是 `elong*R > margin`，**有界盒播种**，N13）
* `dbg['fresh_blocked']`  —— `:2188`（位点全不合格 ⇒ `_placed` 仍为 False）
* `dbg['sites_resampled']`—— `:2219`（整张位点表被重抽的次数，R481b 的解卡机制）
* `dbg['att'/'oob'/'cov'/'exc'/'ok'/'nocand']` —— `:2039`（各通道的成败计数）
⇒ 不接出来就只能**猜**。**这是量具缺口，不是物理缺口。**

## 本补丁做什么
在 athermal 块的 `while` 循环**之后**（每步一处），只在计数**变化**时打印一行。
* **纯记账**：只读 `g._nuc['dbg']`，**不写任何数值** ⇒ 数值路径逐位不变 ✓
* 噪声有界：≤ 事件数（本项目 ≤ 69 行）
* `g._dbg_sig` 只用于去重，不参与任何判据

自检：锚点唯一性 + 语法编译 + 备份 + 写后复验（锚点用**代码行**，避开本补丁自己的注释）。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

OLD = "                      % (it, _tgt, n_ath_tgt, _rej, _rej_cap))\n"

NEW = """                      % (it, _tgt, n_ath_tgt, _rej, _rej_cap))
            # ★★★★★★ s295（**量具**：把引擎的形核分诊计数接出来）
            #   ## 为什么必须接（用户硬约束「尤其需要注意量具的正确性」）
            #     s293/s294 让「块数 = B」的规则正确工作，但实测 **`fresh` 每次都被拒**：
            #       `t5FIX` 成功=6 / fresh 被拒=6；`t5BKMo` 5/5；`t5ETAo` 2/2。
            #     ⇒ 修法**卡死在引擎里**，而引擎**自己就有**分诊计数却**一个都没打印**：
            #       · `dbg['fresh_exc']`       `windowB_surface.py:2183`
            #         （`seed_plate` 抛异常；注释指明典型原因是 `elong*R > margin`
            #          —— **有界盒播种**，N13）
            #       · `dbg['fresh_blocked']`   `:2188`（位点全不合格 ⇒ `_placed` 仍 False）
            #       · `dbg['sites_resampled']` `:2219`（整张位点表重抽次数，R481b 的解卡机制）
            #       · `dbg['att'/'oob'/'cov'/'exc'/'ok'/'nocand']` `:2039`
            #     ⇒ 不接出来就只能**猜**。**这是量具缺口，不是物理缺口。**
            #   ## 本行做什么
            #     只读 `g._nuc['dbg']`，只在计数**变化**时打印一行。
            #   ⚠ **纯记账，不写任何数值** ⇒ 数值路径逐位不变 ✓
            #   ⚠ 噪声有界：≤ 事件数（本项目 ≤ 69 行）
            #   ⚠ `g._dbg_sig` 只用于去重，不参与任何判据
            _nucd = getattr(g, '_nuc', None)
            if isinstance(_nucd, dict):
                _dbgd = _nucd.get('dbg')
                if isinstance(_dbgd, dict) and _dbgd:
                    _dsig = tuple(sorted('%s=%s' % (_k, _v)
                                         for _k, _v in _dbgd.items()))
                    if _dsig != getattr(g, '_dbg_sig', None):
                        g._dbg_sig = _dsig
                        P('   ◆ s295 形核分诊（引擎 dbg）：'
                          + ' '.join(sorted('%s=%s' % (_k, _v)
                                            for _k, _v in _dbgd.items())))
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
    tmp = SRC + ".s295tmp"
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
    bak = SRC + ".bak_s295dbg"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("\n            _nucd = getattr(g, '_nuc', None)") == 1, "读取 1 处"),
        (t3.count("'   ◆ s295 形核分诊（引擎 dbg）：'") == 1, "打印 1 处"),
        (t3.count("g._dbg_sig = _dsig") == 1, "去重 1 处"),
        # 不得引入任何对 dbg 的**写**
        (t3.count("_dbgd[") == 0 and t3.count("dbg'][") == 0, "未写 dbg"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-26s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s295 形核分诊量具接线完成（纯记账，数值逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
