#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_thlabel.py --- s297：修**误导性标签**「厚度(在位的场)」（纯标签，不改数值）。

## 缺陷（**量具标签错，且 `_bk_measure.py` 早已写明**）
`_bk_exp.py:3193/3199` 打印
```python
'厚度(在位的场) %s nm | ...'
% (..., ' '.join('%d:%.0f' % (k, mm['n_%d' % k] * 1e9) ...), ...)
```
而 `mm['n_%d']` 的定义在 `_bk_measure.py:176` 白纸黑字写着：
> `n_%d`（= `ths`，板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
> 实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**（1500 步），
> 而由 φ 量出的**两张宽面之间的距离**只有 780 → **732 nm**（−48 nm）。
> ⇒ 包围跨度被**碎片**与 **`n*` 与真实板条法向的夹角**撑大。

⇒ **打印的标签是错的**，而**碎片化会把包围盒撑满整个盒子**。

## 实测后果（**我自己就上当了，记账**）
s296 之后 `t5ETAo` step 40：
```
厚度(在位的场) 1:510 162:5944 185:3913 nm
```
`5944 nm` **比 5.0 µm 的盒子还大** ⇒ **物理不可能值** ⇒ 当场可判是量具问题。
我上一轮据此报了「新的形核不是板条状的」—— **那是伪影**。
**视觉反证**（`_t5_split3d2.py t5ETAo 162 40`，`_w2_t5_split3d_t5ETAo_f162_en.png`）：
场 162 的主体是一张**干净的薄板**（2488 胞，`pieces=3/主74%`）⇒ **形核是板条状的** ✓

⇒ **撤回**「形核不是板条状」这条结论（按纪律记账，不抹掉）。
**改判**：`n_k` 大 ⟺ **该场碎片化严重**（或 `n*` 与真实法向夹角大）
⇒ 它其实是一个**对碎片化很敏感的代理量**，只是**标签必须改**。

## 本补丁做什么（**纯标签 + 注释，零数值改动**）
`'厚度(在位的场) %s nm'` → `'包围跨度(沿n*,≠厚度) %s nm'`
再加一段长注释说明口径与陷阱。CSV 列名 `ths`/`n_lath` **不动**（改列名会破坏所有分析脚本），
但在注释里点名 `n_lath` 也是同一个量。

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

OLD = "          '厚度(在位的场) %s nm | 壁=%d | %.2fs/步'\n"

NEW = """          # ★★★★★★ s297（**量具标签修正**；纯标签，**零数值改动**）
          #   ## 缺陷
          #     本行原来写「**厚度**(在位的场)」，而取的是 `mm['n_%d' % k]`。
          #     `_bk_measure.py:176` 白纸黑字写明：
          #       > `n_%d`（= `ths`，板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
          #       > 实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**（1500 步），
          #       > 而由 φ 量出的**两张宽面之间的距离**只有 780 → **732 nm**（−48 nm）。
          #       > ⇒ 包围跨度被**碎片**与 **`n*` 与真实法向的夹角**撑大。
          #     ⇒ **标签是错的**，而且**碎片化会把包围盒撑满整个盒子**。
          #   ## 实测后果（**我自己上过当，记账**）
          #     s296 后 `t5ETAo` step 40 打印 `1:510 162:5944 185:3913 nm` ——
          #     **5944 nm 比 5.0 µm 的盒子还大** ⇒ 物理不可能值 ⇒ 当场可判是量具问题。
          #     我据此报过「新的形核不是板条状的」——**那是伪影，已撤回**。
          #     视觉反证（`_w2_t5_split3d_t5ETAo_f162_en.png`）：场 162 主体是
          #     **干净的薄板**（2488 胞，`pieces=3`、主体 74%）⇒ 形核**是**板条状的 ✓
          #   ## 正确读法
          #     `n_k` 大 ⟺ 该场**碎片化严重**（或 `n*` 与真实法向夹角大）
          #     ⇒ 它是对**碎片化很敏感**的代理量；要物理厚度必须**另用量具**
          #       （由 φ 的两张宽面间距，且**显式减掉 1Δx 的系统偏差**，见 `_bk_measure.py`）。
          #   ⚠ CSV 列 `ths`/`n_lath` 是**同一个量**，本补丁不改列名（会破坏分析脚本），
          #     但在此点名。s297 起读 CSV 的人请按「包围跨度」理解。
          '包围跨度(沿n*,≠厚度) %s nm | 壁=%d | %.2fs/步'
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
    tmp = SRC + ".s297tmp"
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
    bak = SRC + ".bak_s297thlabel"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        ("'包围跨度(沿n*,≠厚度) %s nm | 壁=%d | %.2fs/步'" in t3, "新标签 1 处"),
        ("'厚度(在位的场) %s nm" not in t3, "旧误导标签已消失"),
        (t3.count("mm['n_%d' % k] * 1e9") == 2, "取值表达式未动（2 处）"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-28s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s297 标签修正完成（纯标签，数值逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
