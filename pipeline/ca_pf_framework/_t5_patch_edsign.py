#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_edsign.py --- 给 R208 三项诊断**加带符号统计**（`Δed` 的符号分布）

## 为什么
诊断块（`windowB_surface.py:4372`）目前只报 `|Δed|` 的绝对值 ⇒
**无法判"弹性能项把界面推向哪边"**，而那正是"孤立种子为何溶解/碎裂"的要害。
**要做的最小改动**：在同一块里补三个**纯记账**字段：
* `med_ed_signed`：`Δed = ed_k − ed_l` 的**带符号中位**;
* `frac_ed_neg`  ：`Δed < 0` 的**占比**（⇒ 驱动**回退**的比例）;
* `q10/q90_ed_signed`：带符号的分位（看分布是否**两边都有**）。

## 安全性论证（**逐条**）
1. 改动只在 `if getattr(self, 'diag_terms_on', False):` **块内** ⇒
   `--diag-terms` 关时（**默认**）**逐位不变** ✓
2. 新增字段**只写进返回的 dict**，**不参与任何分支/数值** ✓
3. `_bk_exp.py` 的打印处只 `P(...)` 输出，**不改数值** ✓
"""
import hashlib
import os
import shutil
import sys

SUR = 'windowB_surface.py'
EXP = '_bk_exp.py'
ok = 0

# ─────────────── ① `windowB_surface.py`：给 `_stats` 加带符号字段 ───────────────
src = open(SUR, encoding='utf-8').read()
h0 = hashlib.sha256(src.encode()).hexdigest()
print('  %s 改前 sha256 = %s…' % (SUR, h0[:16]))
OLD = """                        frac_ed0=float((a == 0.0).mean()),
                        frac_sk0=float((b == 0.0).mean()))"""
NEW = """                        frac_ed0=float((a == 0.0).mean()),
                        frac_sk0=float((b == 0.0).mean()),
                        # ★★★★★ s268：**带符号**的 `Δed`（纯记账）。
                        #   为什么要它：本轮查"孤立种子为何溶解/碎裂"时，
                        #   `|Δed|` 中位 = 2.7e8（比 `γκ` 大 130 倍）⇒ 弹性项是主导项，
                        #   但**只报绝对值就无法判它把界面推向哪边**。
                        #   `Δed < 0` ⇒ 该胞的 winner 被弹性项**惩罚** ⇒ 界面**回退**。
                        #   ⚠ 只在 `diag_terms_on` 块内、只进返回 dict：
                        #     `--diag-terms` 关时（默认）逐位不变。
                        med_ed_signed=float(np.median(_edt[mask])),
                        q10_ed_signed=float(np.percentile(_edt[mask], 10)),
                        q90_ed_signed=float(np.percentile(_edt[mask], 90)),
                        frac_ed_neg=float((_edt[mask] < 0).mean()))"""
n = src.count(OLD)
print('  锚点出现次数 = %d' % n)
if n == 1:
    out = src.replace(OLD, NEW, 1)
    try:
        compile(out, SUR, 'exec')
        if not os.path.exists(SUR + '.bak_edsign'):
            shutil.copy2(SUR, SUR + '.bak_edsign')
            print('  已备份 → %s.bak_edsign' % SUR)
        open(SUR, 'w', encoding='utf-8').write(out)
        print('  ✅ %s 已改（sha256 %s…）' % (SUR, hashlib.sha256(out.encode()).hexdigest()[:16]))
        ok += 1
    except SyntaxError as e:
        print('  ❌ 语法错：%s ⇒ 未写盘' % e)
else:
    print('  ⚠ 锚点不唯一 ⇒ 跳过 %s' % SUR)

# ─────────────── ② `_bk_exp.py`：把新字段打进输出 ───────────────
src2 = open(EXP, encoding='utf-8').read()
OLD2 = "med_sk=med_sk"
if OLD2 not in src2:
    # 找实际打印行
    import re
    m = re.search(r'med_ed[^\n]*med_sk[^\n]*', src2)
    print('  ② `_bk_exp.py` 打印行形态：%s' % (m.group(0)[:130] if m else '（未找到）'))
    OLD2 = m.group(0) if m else None
if OLD2:
    NEW2 = OLD2 + " + ' ｜ `Δed` 带符号 中位 %.3e（<0 占 %.1f%%）' % (r['med_ed_signed'], 100.0 * r['frac_ed_neg'])"
    n2 = src2.count(OLD2)
    print('  ② 锚点出现次数 = %d' % n2)
    if n2 == 1:
        out2 = src2.replace(OLD2, NEW2, 1)
        try:
            compile(out2, EXP, 'exec')
            if not os.path.exists(EXP + '.bak_edsign'):
                shutil.copy2(EXP, EXP + '.bak_edsign')
                print('  已备份 → %s.bak_edsign' % EXP)
            open(EXP, 'w', encoding='utf-8').write(out2)
            print('  ✅ %s 已改' % EXP)
            ok += 1
        except SyntaxError as e:
            print('  ❌ 语法错：%s ⇒ 未写盘' % e)
    else:
        print('  ⚠ 锚点不唯一 ⇒ 跳过 %s' % EXP)
print()
print('  改动计数 = %d（期望 2）' % ok)
