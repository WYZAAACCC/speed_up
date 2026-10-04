#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_sceta.py --- s296：把 η 接到**形核闸门**上（修法 A 的另一半）。

## 发现（**引擎自己的 dbg 实测**，s295 接线后才看得见）
`fresh` 通道实测 **100% 被拒**（三臂一致：6/6、5/5、2/2）。s295 接出引擎分诊计数后：
```
fresh_cand=12   fresh_blocked=12   sites_resampled=12   sc_try=11   supercrit=11
sc_last_df    = +1.2273e8      ← 化学驱动力 ✓（理论 1.2275e8，4 位吻合）
sc_last_ed    = -2.1342e8      ← ★ 弹性罚能 = 驱动力的 1.74 倍
sc_last_fcrit =  1.6e6
```
`sites_resampled=12` ⇒ 引擎的**解卡机制正常工作**（位点被重抽了 12 个），
但重抽的位点**全部卡在同一条判据**上 ⇒ **阻塞是"判据"，不是"几何"**。

## 判据（`windowB_surface.py:1872/1884`，逐行读过）
```python
fcrit = 2.0 * float(gamma) / max(float(t), 1e-30)          # :1872
return bool(float(df) + med > fcrit), med, fcrit, nc       # :1884
```
代入实测：`1.2273e8 + (−2.1342e8) = −9.07e7`，**远不大于** `1.6e6` ⇒ **拒绝** ✓ 与实测一致。

## ⇒ 根因：**η（修法 A）只接了一半**
`η` 此前只接在 **长大律** `dG_cell = Δdf + η·Δed − γκ`（`:4366`），
**没有**接在 **形核闸门** `df + ed > 2γ/t` 上。
而"弹性罚能高估 ~3 倍"（纯线弹性无塑性弛豫/TRIP）这条物理理由
**对形核闸门同样成立** —— 储存能里同样有 2/3 应被塑性耗散掉。

⇒ 后果：**核根本放不下**（`fresh` 全拒），只有 `attach`/`stack`（**不经**该判据）能放核，
而这些核放下去又被长大律溶解 ⇒ 「一场多板条」+ 「块数恒 1」+ burst 被拒，
**三个症状同一个根因**。

## 修法（一处，与长大律口径一致）
```python
return bool(float(df) + ETA * med > fcrit), med, fcrit, nc
```
其中 `ETA = float(getattr(self, 'ed_eta', 1.0) or 1.0)`。
* `η = 0.375`：`1.2273e8 + 0.375·(−2.1342e8) = **+4.270e7** > 1.6e6` ⇒ **通过** ✓
* `η = 1.0`（**默认**）⇒ **与原文逐字等价** ⇒ 归档臂**逐位不变** ✓
* 与 `:4366` 的 `dG_cell` 用**同一个** `self.ed_eta` ⇒ 两条律口径一致（不再一半一半）

自检：锚点唯一性 + 语法编译 + 备份 + 写后复验（锚点用代码行，避开本补丁自己的注释）。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

OLD = "        return bool(float(df) + med > fcrit), med, fcrit, nc\n"

NEW = """        # ★★★★★★ s296（**修法 A 的另一半**：把 η 接到**形核闸门**上）
        #   ## 为什么要接（**s295 接出引擎 dbg 后才看得见的实测**）
        #     `fresh` 通道实测 **100% 被拒**（三臂一致）。引擎分诊计数：
        #       `fresh_cand=12  fresh_blocked=12  sites_resampled=12`
        #       `sc_try=11  supercrit=11`
        #       `sc_last_df = +1.2273e8`（= 理论 ΔG(Ms)，4 位吻合 ✓）
        #       `sc_last_ed = -2.1342e8`（**弹性罚能 = 驱动力的 1.74 倍**）
        #       `sc_last_fcrit = 1.6e6`
        #     `sites_resampled=12` ⇒ 引擎的**解卡机制正常工作**（重抽了 12 个位点），
        #     但重抽的位点**全部卡在同一条判据**上 ⇒ **阻塞是"判据"，不是"几何"**。
        #   ## 判据本身（下面两行，逐行读过）
        #     `fcrit = 2γ/t`；判据 `df + med > fcrit`
        #     代入：`1.2273e8 + (−2.1342e8) = −9.07e7`，**远不大于** `1.6e6` ⇒ 拒绝 ✓
        #   ## 根因：**η 只接了一半**
        #     `η` 此前只接在**长大律** `dG_cell = Δdf + η·Δed − γκ`（`:4366`），
        #     **没有**接在**形核闸门** `df + ed > 2γ/t` 上。
        #     而"弹性罚能高估 ~3 倍"（**纯线弹性、无塑性弛豫/TRIP**）这条物理理由
        #     **对形核闸门同样成立** —— 储存能里同样有 2/3 应被塑性耗散掉。
        #   ## 后果（**三个症状同一个根因**）
        #     核根本放不下 ⇒ 只有 `attach`/`stack`（**不经**该判据）能放核，
        #     而这些核放下去又被长大律溶解 ⇒
        #       「一场多板条」+「块数恒 1」+「burst 首档被拒」全部由此而来。
        #   ## 修法（**一处，与长大律口径一致**）
        #     `η = 0.375` 时：`1.2273e8 + 0.375·(−2.1342e8) = +4.270e7 > 1.6e6` ⇒ **通过** ✓
        #   ⚠ `η = 1.0`（**默认**）⇒ **与原文逐字等价** ⇒ 归档臂**逐位不变** ✓
        #   ⚠ 与 `:4366` 用**同一个** `self.ed_eta` ⇒ 两条律口径一致，不再"一半一半"
        _eta_sc = float(getattr(self, 'ed_eta', 1.0) or 1.0)
        return bool(float(df) + _eta_sc * med > fcrit), med, fcrit, nc
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
    tmp = SRC + ".s296tmp"
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
    bak = SRC + ".bak_s296sceta"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("\n        _eta_sc = float(getattr(self, 'ed_eta', 1.0) or 1.0)") == 1,
         "η 读取 1 处"),
        (t3.count("\n        return bool(float(df) + _eta_sc * med > fcrit), med, fcrit, nc") == 1,
         "判据行 1 处"),
        (t3.count("return bool(float(df) + med > fcrit)") == 0, "旧判据行已消失"),
        (t3.count("float(getattr(self, 'ed_eta', 1.0) or 1.0) * (edk - edl)") == 1,
         "长大律 η 仍在位（口径一致）"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-32s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s296 η 接到形核闸门完成（默认 η=1.0 ⇒ 逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
