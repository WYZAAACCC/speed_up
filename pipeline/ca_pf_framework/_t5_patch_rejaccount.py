#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_rejaccount.py --- s291：burst 第二处缺陷（**被拒也消耗目标**）的修复。

## 缺陷
`_bk_exp.py:2150` 定义 `n_ath_tgt = 0  # 当前的累计根数（不含预摆的第 1 片）`
—— 即**盒子里真实存在的板条数**。而 `n_ath_tgt += 1` 在**被引擎拒**时也执行
⇒ 把不存在的板条记进累计数 ⇒ 目标被凭空消耗。
实测（`t5BKMo`/`t5FIX` 两臂逐位相同）：首档尝试 45 次 → **成功 20、被拒 25**
⇒ 那 25 根此后**永不重试**；且打印的「累计 21/23」含 1 根不存在的核（量具错）。

## 修法（只改记账，不改物理律；**完全由 `--burst-km` 门控**）
1. 被拒 ⇒ 不消耗目标，只累计 `_rej`；
2. 每步被拒上限 `_rej_cap = 8`（`--burst-km 0` 时为 `10**9` ⇒ 条件恒真 ⇒ 逐位不变）。

自检：锚点唯一性 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import re
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

A_OLD = "            while n_ath_tgt < _tgt and n_ath_tgt < nv:\n"
A_NEW = """            # ★★★★★★ s291（**用户总目标第 4 项：修 burst 至物理正确 —— 第二处缺陷**）
            #   ## 缺陷（**记账错，且是原代码就带的**）
            #     `:2150` 自己写明 `n_ath_tgt` 是「**当前的累计根数**」
            #     —— 即**盒子里真实存在的板条数**。而下面 `n_ath_tgt += 1`
            #     在**被拒**（`not _ev`，引擎放不下）时**也加 1**
            #     ⇒ 把**不存在的板条**记进累计数 ⇒ 目标被**凭空吃掉**。
            #   ## 为什么在 burst 档下才致命（**实测**）
            #     线性旧律 `floor(αΔT)` **每档只 +1** ⇒ 被拒很稀疏 ⇒ 旧缺陷几乎不显形。
            #     修好的 KM 分数律**首档就要 45 根**（`3·round(23·0.6327)`）
            #     ⇒ 实测（`t5BKMo`/`t5FIX` 两臂**逐位相同**）：
            #         **尝试 45 次 → 成功 20 根、被拒 25 次**
            #       ⇒ 这 25 根**此后永不重试**；打印的「累计 21/23」还多算 1 根。
            #   ## 修法（**只改记账，不改物理律**）
            #     · 被拒 ⇒ **不消耗目标**，只累计 `_rej`
            #     ⇒ `n_ath_tgt` 回到「真实存在的根数」的原定义 ✓
            #     ⇒ 本档放不下的核，**下一档（更低温、目标更大）继续重试** ✓
            #     ⇒ 物理含义：burst 的需求由 KM 律给出，**投放速率受几何容量限制**，
            #       一旦几何腾出空间就补上（不是"作废"）。
            #   ## 防死循环（**代价有界**）
            #     每步被拒上限 `_rej_cap = 8`（局部变量，随本步重置）
            #   ⚠ 惰性：`--burst-km 0`（默认）⇒ `_rej_cap = 10**9` ⇒ 条件恒真，
            #     且下面的 `+= 1` 无条件执行 ⇒ **逐位不变** ✓
            _burst_on = bool(int(getattr(a, 'burst_km', 0) or 0))
            _rej = 0
            _rej_cap = 8 if _burst_on else 10 ** 9
            while n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
"""

B_OLD = """                n_ath_tgt += 1
                if _ev:
"""
B_NEW = """                # ★ s291：**被拒的事件不得消耗目标**（只改记账）
                if _ev or not _burst_on:
                    n_ath_tgt += 1
                else:
                    _rej += 1
                if _ev:
"""

C_OLD = """                    P('   ⚠ athermal 事件 #%d 被引擎拒（无可用空场/落位失败）@ step %d'
                      % (n_ath_tgt, it))
"""
C_NEW = """                    P('   ⚠ athermal 形核**被引擎拒**（无可用空场/落位失败）@ step %d'
                      '：目标 %d 根、**实有 %d 根**，本步第 %d/%d 次被拒'
                      % (it, _tgt, n_ath_tgt, _rej, _rej_cap))
"""


def main():
    with open(SRC, "r", encoding="utf-8") as fh:
        t = fh.read()

    ok = True
    for name, old in (("A", A_OLD), ("B", B_OLD), ("C", C_OLD)):
        n = t.count(old)
        print("  锚点 %s 出现 %d 次 %s" % (name, n, "✓" if n == 1 else "❌"))
        if n != 1:
            ok = False
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入")
        return 1

    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1).replace(C_OLD, C_NEW, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()

    # 语法自检（写盘前，用临时文件）
    tmp = SRC + ".s291tmp"
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

    bak = SRC + ".bak_s291rej"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)

    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        ("_rej_cap = 8 if _burst_on else 10 ** 9" in t3, "_rej_cap 门控"),
        ("_rej < _rej_cap:" in t3, "while 条件"),
        ("if _ev or not _burst_on:" in t3, "_ev 门控"),
        ("_rej += 1" in t3, "_rej 累计"),
        (t3.count("n_ath_tgt += 1") == 1, "n_ath_tgt 只有一处自增"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-28s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s291 记账修复完成（`--burst-km` 门控；默认档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
