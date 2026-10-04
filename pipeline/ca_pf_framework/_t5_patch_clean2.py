#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_clean2.py --- s301b：清理范围改为**「本场 + 被本次播种擦到的那些场」**。

## 为什么（`t10CLN` 实测）
s301 第一版在**场 k 自己播完**时清理 `k` ⇒ 那一刻 `k` 只有一个连通块 ⇒ 无事可做
⇒ 实测与守卫 ON 那跑**逐位相同**（step 1 仍 9/15 多块）。
**⇒ 第二块是之后被别的籽晶"擦"出来的。**

## 机制（`seed_plate` 里的两行，`windowB_surface.py:2890-2893`）
```python
self.phi[k] = np.minimum(self.phi[k], sdf)          # 写本场
for j in range(self.nreg):
    if j != k:
        self.phi[j] = np.maximum(self.phi[j], -sdf)  # ★ 把**其它场**在 sdf<0 区内擦成正值
```
⇒ 后播的籽晶若**横穿**先播的板条，就在先播的那个场上**挖掉一段** ⇒ 一分为二。
被挖掉的那段 `phi[j]` 变**正值** ⇒ 在 `region` 口径下归**母相** ——
**这正是 `_t10_erode.py` 实测"连线 80–90% 是母相"的成因**（我上一轮把该证据读反了）。

## 修法
在**真实播种**后，对**本场 `k` 以及本次被 `max` 改动过的每个 `j`** 各做一次
`keep_largest_neg`（被改动过的 `j` 才可能被挖断；没改动的无需清理）。
⇒ 每个籽晶最多几次 labeling，且作用域是包围盒 ⇒ 便宜。
探针路径（`undo is not None`）**绝不**清理（它要"真放+精确回滚"的语义）。

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

OLD = """            # ★ s301：真实播种后清掉 φ<0 的多余连通块（`--nuc-occ-guard 2` 才启用）
            if undo is None and int((getattr(self, '_nuc', None) or {})
                                    .get('occ_guard', 0) or 0) >= 2:
                self.keep_largest_neg(k)
            return
"""
NEW = """            # ★ s301b：真实播种后清理——**本场 k 以及本次被 `max` 擦过的每个 j**
            #   （第一版只清 k ⇒ 实测与守卫档逐位相同，因为 k 在"自己播完"那一刻
            #    仍是单连通；第二块是**之后**被别的籽晶擦出来的。）
            if undo is None and int((getattr(self, '_nuc', None) or {})
                                    .get('occ_guard', 0) or 0) >= 2:
                self.keep_largest_neg(k)
                for j in range(self.nreg):
                    if j != k and (-sdf > self.phi[j]).any():
                        self.keep_largest_neg(j)
            return
"""

OLD2 = """        # ★ s301：真实播种后清掉 φ<0 的多余连通块（`--nuc-occ-guard 2` 才启用）
        if undo is None and int((getattr(self, '_nuc', None) or {})
                                .get('occ_guard', 0) or 0) >= 2:
            self.keep_largest_neg(k)
"""
NEW2 = """        # ★ s301b：真实播种后清理——**本场 k 以及本次被 `max` 擦过的每个 j**（同 along 分支）
        if undo is None and int((getattr(self, '_nuc', None) or {})
                                .get('occ_guard', 0) or 0) >= 2:
            self.keep_largest_neg(k)
            for j in range(self.nreg):
                if j != k and (-sdf > self.phi[j]).any():
                    self.keep_largest_neg(j)
"""


def main():
    with open(WS, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for nm, old in (("along", OLD), ("main", OLD2)):
        c = t.count(old)
        print("  锚点 %-6s 出现 %d 次 %s" % (nm, c, "✓" if c == 1 else "❌"))
        ok &= (c == 1)
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入"); return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(OLD, NEW, 1).replace(OLD2, NEW2, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = WS + ".s301btmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc); os.remove(tmp); return 1
    os.remove(tmp)
    bak = WS + ".bak_s301b"
    if not os.path.exists(bak):
        shutil.copy2(WS, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(WS, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(WS, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("if j != k and (-sdf > self.phi[j]).any():") == 2, "擦除者清理 2 处"),
        (t3.count("self.keep_largest_neg(k)") == 2, "本场清理 2 处"),
        (t3.count("def keep_largest_neg(self, k):") == 1, "helper 仍在位"),
        (t3.count("self._seed_undo_note(k, sdf, undo)") == 2, "原记账点仍在 2 处"),
        (t3.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-26s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复"); return 1
    print("✅ s301b 清理范围修正完成（`--nuc-occ-guard 2` 才启用；默认逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
