#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_edsign2.py --- 把**带符号 `Δed`** 打进打印行（`_bk_exp.py:2444-2451`）

## 为什么（上一版 patcher 的 ② 没找到锚点）
上一版我按 `med_sk=med_sk` 猜锚点 ⇒ 没匹配上。**实际打印行在第 2444–2451 行**
（多行隐式拼接的 `P(...)`）⇒ 本版**按真实行文本**锚定。

## 安全性（与上一版同）
* 只往 `P(...)` 的**格式串与实参**里加一项 ⇒ **只影响输出文本**;
* 该 `P(...)` 整体在 `if bool(a.diag_terms) and getattr(g, 'diag_terms', None):` 内
  ⇒ **`--diag-terms` 关时（默认）根本不执行** ⇒ 逐位不变 ✓
"""
import hashlib
import os
import shutil
import sys

EXP = '_bk_exp.py'
src = open(EXP, encoding='utf-8').read()
print('  %s 改前 sha256 = %s…' % (EXP, hashlib.sha256(src.encode()).hexdigest()[:16]))

OLD = """                                 100 * _f(_p.get('med_ratio', float('nan'))),
                                 100 * _f(_p.get('p99_ratio', float('nan')))))"""
NEW = """                                 100 * _f(_p.get('med_ratio', float('nan'))),
                                 100 * _f(_p.get('p99_ratio', float('nan')))))
                            # ★★★★★ s268：**带符号 `Δed`**（纯记账，只影响本行输出）。
                            #   动机：查"孤立种子为何溶解/碎裂"时 `|Δed|` 中位 = 2.7e8
                            #   （比 `γκ` 大 130 倍）⇒ 弹性项是主导项，但**只报绝对值
                            #   无法判它把界面推向哪边**。`Δed < 0` ⇒ winner 被弹性项
                            #   **惩罚** ⇒ 界面**回退**。`<0` 的占比就是"回退面"的比例。
                            P('        **`Δed` 带符号** 中位 %+.3e ｜ <0 占 **%.1f%%** ｜ '
                              '10~90 分位 [%+.3e, %+.3e]'
                              % (_f(_p.get('med_ed_signed', float('nan'))),
                                 100.0 * _f(_p.get('frac_ed_neg', float('nan'))),
                                 _f(_p.get('q10_ed_signed', float('nan'))),
                                 _f(_p.get('q90_ed_signed', float('nan')))))"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)
try:
    compile(out, EXP, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
if not os.path.exists(EXP + '.bak_edsign2'):
    shutil.copy2(EXP, EXP + '.bak_edsign2')
    print('  已备份 → %s.bak_edsign2' % EXP)
open(EXP, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…）' % hashlib.sha256(out.encode()).hexdigest()[:16])
