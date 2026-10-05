#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_protfix.py --- s304b：**保护范围必须排除场 0（母相 β）** —— 这是 s304 的缺陷。

## 缺陷（`t10PRT` 的 `[SEEDCARVED]` 首次真实记账当场抓到）
```
[SEEDCARVED] k=2  carved=[0, 1, 111]   protected=[0, 1, 111]
[SEEDCARVED] k=3  carved=[0, 1]        protected=[0, 1]
```
**`protected` 里出现了 `0`** —— 而场 0 是**母相 β**：`init_parent()` 令
`phi[0] = −min(phi[1:])` ⇒ φ₀ 在母相区处处为负、负胞数极大 ⇒ **恒 ≥100 ⇒ 恒被保护**。

**⚠ 后果**：新板条形核处**母相必须被擦成正值**（否则 `region = argmin(φ)` 仍选母相
⇒ 板条在**物理相口径**下根本不出现）⇒ **s304 的"保护"会把核变成死核，而不是修好死核。**

**⇒ 修：保护只作用于变体场 `1..nreg−1`；场 0 一律允许被擦。**

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

OLD_A = """            if os.environ.get('SEED_PROTECT') == '1':
                _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
                for j in _carved:
                    if int((self.phi[j] < 0).sum()) >= _pmin:
                        _prot.add(j)
"""
NEW_A = """            if os.environ.get('SEED_PROTECT') == '1':
                _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
                for j in _carved:
                    # ★ s304b：**场 0（母相 β）绝不保护** —— 新板条形核处母相必须被擦成正
                    #   值，否则 `region = argmin(φ)` 仍选母相 ⇒ 板条在物理相口径下不出现
                    #   （`t10PRT` 的 `[SEEDCARVED] protected=[0,…]` 当场暴露此缺陷）。
                    if j == 0:
                        continue
                    if int((self.phi[j] < 0).sum()) >= _pmin:
                        _prot.add(j)
"""

OLD_B = """        if os.environ.get('SEED_PROTECT') == '1':
            _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
            for j in _carved:
                if int((self.phi[j] < 0).sum()) >= _pmin:
                    _prot.add(j)
"""
NEW_B = """        if os.environ.get('SEED_PROTECT') == '1':
            _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
            for j in _carved:
                if j == 0:
                    continue          # ★ s304b：母相不保护（同 along 分支）
                if int((self.phi[j] < 0).sum()) >= _pmin:
                    _prot.add(j)
"""


def main():
    with open(WS, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for nm, old in (("along", OLD_A), ("main", OLD_B)):
        c = t.count(old)
        print("  锚点 %-6s 出现 %d 次 %s" % (nm, c, "✓" if c == 1 else "❌"))
        ok &= (c == 1)
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入"); return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(OLD_A, NEW_A, 1).replace(OLD_B, NEW_B, 1)
    tmp = WS + ".s304btmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc); os.remove(tmp); return 1
    os.remove(tmp)
    bak = WS + ".bak_s304b"
    if not os.path.exists(bak):
        shutil.copy2(WS, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(WS, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(WS, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("if j == 0:") >= 2, "排除场 0 ≥2 处"),
        (t3.count("_prot.add(j)") == 2, "保护添加仍在 2 处"),
        (t3.count("_carved = [j for j in range(self.nreg)") == 2, "写前掩码仍在 2 处"),
        (t3.count("[SEEDCARVED]") == 2, "carved 串仍在 2 处"),
        (t3.count("SEED_CLEAN") == 2, "s301c 门控仍在位"),
        (t3.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-26s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    h1 = hashlib.sha256(t3.encode("utf-8")).hexdigest()
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复"); return 1
    print("✅ s304b 保护范围修正完成（母相不保护；默认仍全关）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
