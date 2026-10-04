#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_cumden.py --- s298：修形核日志的**分母口径错**（纯打印，不改数值）。

## 缺陷（实测日志原文）
```
★★ **athermal 形核** @ step 1：T=849.0 K（T_4 理论=777.2 K；块内第 4 根 / 共 3 块），
   df=1.2273e+08，场 178（累计 10/23；模式 **attach**；累计 fresh=3 stack=0）
```
`累计 10/23` 的分母取的是 **`_n_law` = `n(T_end)` = 23**（**每块**的根数，C-2 口径），
而 `while` 循环真正的判据是 **`n_ath_tgt < _tgt`**，其中 **`_tgt = B × _n_blk`**：
* 本档（首档）`_n_blk = round(23 × 0.6327) = 15` ⇒ **`_tgt = 3 × 15 = 45`**；
* 末档 `_tgt = 69`。
⇒ 这一列会一路涨到 **`45/23`**，**看着像"超额 2 倍"，实际完全正确**。
**这是报告口径错，不是物理错**，但它会让人误判 burst 的投放量。

## 修法（**加法式**：两个口径都给，旧日志仍可解析）
`累计 %d/%d` → `累计 %d/%d（本档目标；每块口径 %d）`
即：`n_ath_tgt, _tgt, _n_law`。
* 原有的"累计 N/23"信息**不丢**（仍在括号里）；
* 不再出现"分子 > 分母"的假超额；
* ⚠ **纯打印** ⇒ 数值路径逐位不变 ✓

自检：锚点唯一 + 语法编译 + 备份 + 写后复验（锚点用代码行，避开本补丁自己的注释）。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

OLD = """                      '，df=%.4e，场 %d（累计 %d/%d；模式 **%s**；累计 fresh=%d stack=%d）'
                      % (it, _Tnow, _kpb, CL.T_of_k(_kpb, _alpha), _kpb, _B_eff,
                         float(g.df[1]), _ev[0][0], n_ath_tgt, _n_law,
                         _ev[0][1], n_mode.get('fresh', 0), n_mode.get('stack', 0)))
"""

NEW = """                      # ★★★★★★ s298（**量具口径修正**；纯打印，**数值逐位不变**）
                      #   ## 缺陷（实测日志原文）
                      #     `累计 10/23` 的分母取的是 `_n_law`（= `n(T_end)` = 23，
                      #     **每块**根数，C-2 口径），而 `while` 真正的判据是
                      #     `n_ath_tgt < _tgt`，`_tgt = B × _n_blk`：
                      #       首档 `_n_blk = round(23×0.6327) = 15` ⇒ **`_tgt = 45`**
                      #       末档 `_tgt = 69`
                      #     ⇒ 这一列会涨到 **`45/23`**，**看着像超额 2 倍，实际正确**。
                      #   ## 修法（**加法式**：两个口径都给，旧日志仍可解析）
                      #     `累计 n/本档目标（本档目标；每块口径 _n_law）`
                      '，df=%.4e，场 %d（累计 %d/%d（本档目标；每块口径 %d）；'
                      '模式 **%s**；累计 fresh=%d stack=%d）'
                      % (it, _Tnow, _kpb, CL.T_of_k(_kpb, _alpha), _kpb, _B_eff,
                         float(g.df[1]), _ev[0][0], n_ath_tgt, _tgt, _n_law,
                         _ev[0][1], n_mode.get('fresh', 0), n_mode.get('stack', 0)))
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
    tmp = SRC + ".s298tmp"
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
    bak = SRC + ".bak_s298cumden"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("（累计 %d/%d（本档目标；每块口径 %d）；") == 1, "新格式 1 处"),
        (t3.count("n_ath_tgt, _tgt, _n_law,") == 1, "参数序 _tgt 已插入"),
        ("n_ath_tgt, _n_law," not in t3, "旧的裸 _n_law 已消失"),
        (t3.count("% (it, _Tnow, _kpb, CL.T_of_k(_kpb, _alpha), _kpb, _B_eff,") == 1,
         "参数行唯一"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-30s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s298 口径修正完成（纯打印；数值路径逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
