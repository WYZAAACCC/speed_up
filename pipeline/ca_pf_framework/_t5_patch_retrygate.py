#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_retrygate.py --- s292：s291 重试机制的**代价闸**。

## 为什么必须加（**实测**）
s291 让「被拒的核不消耗目标」⇒ 跨档重试。功能上**成立**（`t5BKMo` 在第 7 步补上了第 20 根），
但**代价失控**：`_t5_trend291.sh` 每 60 s 采样实测
```
t=0    t5FIX 成功19 被拒 4
t=544  t5FIX 成功19 被拒75     ← 被拒以 ~1.2 次/s 增长，成功数为 0
t=423  t5BKMo 成功20 被拒59    ← 第 7 步补上 1 根
```
⇒ 节拍从 **7.87 s/步** 掉到 **~60 s/步**（**7.6×**）。根因：每次落位尝试都要跑
`--nuc-supercrit 1` 的弹性探针（约 5–6 s）⇒ 8 次/步的 `_rej_cap` 就是 +45 s/步。
6000 步 ⇒ **约 100 小时**，不可接受。

## 修法（**物理语义更准，而不是"为了快"**）
KM 律给的是「**在温度 T 下应当有多少根**」——**粒度本来就是"档"**，不是"步"。
而 `_tgt` 只在进入新温度档时增长（45 → 60 → 66 → 66 → 67 …）。
⇒ **只在本档目标比上次尝试时更大时才补投**：
```python
_tgt_try = int(getattr(g, '_burst_tgt_try', -1))
_do_try  = (_tgt > _tgt_try) if _burst_on else True
if _do_try and _burst_on: g._burst_tgt_try = int(_tgt)
while _do_try and n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
```
* 每个温度档**至多一次**补投轮 ⇒ 全跑 **≤ 23 档 × 8 = 184** 次落位尝试（≈18 min 总代价）；
* **"欠着的核不作废"仍然成立** —— 下一档目标变大时继续补 ✓
* **`--burst-km 0`（默认）⇒ `_do_try = True` 恒真** ⇒ 逐位不变 ✓
  （旧线性律每步 `_tgt` 都 +1 ⇒ 新档判据每步都为真 ⇒ 旧路径行为不变）

自检：锚点唯一性 + 语法编译 + 备份 + 写后复验（锚点串**避开本补丁自己的注释**）。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

A_OLD = """            _burst_on = bool(int(getattr(a, 'burst_km', 0) or 0))
            _rej = 0
            _rej_cap = 8 if _burst_on else 10 ** 9
            while n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
"""

A_NEW = """            _burst_on = bool(int(getattr(a, 'burst_km', 0) or 0))
            _rej = 0
            _rej_cap = 8 if _burst_on else 10 ** 9
            # ★★★★★★ s292（**代价闸**，2026-10-04）
            #   ## 为什么加（**实测，不是猜**）
            #     s291 让"被拒的核不消耗目标" ⇒ 跨档重试。功能**成立**
            #     （`t5BKMo` 在第 7 步补上了第 20 根），但**代价失控**：
            #     每 60 s 采样实测 —— 节拍从 **7.87 s/步** 掉到 **~60 s/步（7.6×）**，
            #     被拒数以 **~1.2 次/s** 增长而成功数为 0。
            #     根因：每次落位尝试都要跑 `--nuc-supercrit 1` 的弹性探针（≈5–6 s）
            #     ⇒ `_rej_cap = 8`/步 就是 **+45 s/步** ⇒ 6000 步 ≈ **100 小时**。
            #   ## 修法（**物理语义更准，不是"为了快"**）
            #     KM 律给的是「**在温度 T 下应当有多少根**」——
            #     **它的粒度本来就是"档"，不是"步"**。
            #     而 `_tgt` 只在进入新温度档时才增长（45 → 60 → 66 → 66 → 67 …）
            #     ⇒ **只在本档目标比上次尝试时更大时才补投**。
            #     · 每档至多一次补投轮 ⇒ 全跑 ≤ 23 档 × 8 = 184 次尝试（≈18 min）
            #     · **"欠着的核不作废"仍成立** —— 下一档目标变大时继续补 ✓
            #   ⚠ 惰性：`--burst-km 0`（默认）⇒ `_do_try = True` 恒真 ⇒ 逐位不变 ✓
            #     （旧线性律每步 `_tgt` 都 +1 ⇒ 新档判据每步都为真 ⇒ 旧路径行为不变）
            _tgt_try = int(getattr(g, '_burst_tgt_try', -1))
            _do_try = (_tgt > _tgt_try) if _burst_on else True
            if _do_try and _burst_on:
                g._burst_tgt_try = int(_tgt)
            if _do_try and _burst_on:
                P('   ◆ s292 补投轮：本档目标 %d 根，实有 %d 根'
                  % (_tgt, n_ath_tgt))
            while _do_try and n_ath_tgt < _tgt and n_ath_tgt < nv and _rej < _rej_cap:
"""


def main():
    with open(SRC, "r", encoding="utf-8") as fh:
        t = fh.read()

    n = t.count(A_OLD)
    print("  锚点 A 出现 %d 次 %s" % (n, "✓" if n == 1 else "❌"))
    if n != 1:
        print("❌ 锚点不唯一 ⇒ 拒绝写入")
        return 1

    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(A_OLD, A_NEW, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()

    tmp = SRC + ".s292tmp"
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

    bak = SRC + ".bak_s292gate"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)

    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    # ⚠ 复验锚点**避开本补丁自己写的注释**（s291 的教训）：
    #   用带行首缩进的**代码行**，注释里那两行是 `#` 开头 ⇒ 不匹配。
    checks = [
        ("_tgt_try = int(getattr(g, '_burst_tgt_try', -1))" in t3, "_tgt_try 读取"),
        ("_do_try = (_tgt > _tgt_try) if _burst_on else True" in t3, "_do_try 表达式"),
        ("g._burst_tgt_try = int(_tgt)" in t3, "写回 g"),
        ("while _do_try and n_ath_tgt < _tgt" in t3, "while 条件含 _do_try"),
        (t3.count("\n            while _do_try and n_ath_tgt < _tgt") == 1,
         "受控 while **代码行**唯一"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-30s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s292 代价闸完成（`--burst-km` 门控；默认档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
