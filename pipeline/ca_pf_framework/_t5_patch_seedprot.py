#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_seedprot.py --- s304：**保护已长成的核** + **修好坏掉的 carved 量具**。

## 两个缺陷（都已实测确认）
### (1) 量具坏掉（本会话第 10 次）
s301c 的清理块里写的是
```python
for j in range(self.nreg):
    if j != k and (-sdf > self.phi[j]).any():     # ← 此时 phi[j] 已被 max 抬起
```
而上面**刚刚**执行过 `phi[j] = np.maximum(phi[j], -sdf)` ⇒ `-sdf > phi[j]` **恒 False**
⇒ `carved_j` 永远是 0 ⇒ **我此前把它当成"擦除未触发"的证据是错的**。
**⇒ 修：在写入之前先算 `_carved` 掩码。**

### (2) 已长成的核被后来的籽晶抹掉（`t10CL2` @step200 实测）
47 个形核事件里 **10 个（21%）在 step200 一个胞都不剩**：
`68, 119, 120, 121, 122, 123, 124, 125, 126, 162`；其中 **119–126 是 8 个连续的同变体(6)场**
⇒ 不是随机缺失，而是**整段连续块被一次性抹掉**，与
`phi[j] = np.maximum(phi[j], -sdf)`（把先播场在该足迹内抬成**正值**）吻合。
带内胞分布是**双峰**（≥1623 或 =0），没有中间态 ⇒ **是"被抹掉"而不是"没长起来"**。

**⇒ 物理**：真实板条不会因为邻片形核而**消失** —— 两个板条相遇是**碰触/阻截**，
不是互相湮灭。`max()` 擦除只是防重叠的**数值手段**，不该把已有核清零。
**⇒ 修：擦除时**跳过已有实质核的场**（负胞数 ≥ `SEED_PROTECT_MIN`，默认 100）。**

## 门控（默认全关 ⇒ 归档逐位不变）
* `SEED_PROTECT=1` ⇒ 启用保护；`SEED_PROTECT_MIN=<n>` ⇒ 阈值（默认 100 胞）
* `SEED_CARVED_DBG=1` ⇒ 打印**修好的** carved 记账：`[SEEDCARVED] k=.. carved=[场号列表]`
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

# ── along 分支（12 空格）──
A_OLD = """            self._seed_undo_note(k, sdf, undo)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
"""
A_NEW = """            self._seed_undo_note(k, sdf, undo)
            # ★★★★★★ s304：(1) **写前**先记"谁会被擦到"（修好恒为 0 的坏量具）；
            #          (2) **保护已有实质核**（真实板条不会因邻片形核而消失）。
            _carved = [j for j in range(self.nreg)
                       if j != k and (-sdf > self.phi[j]).any()]
            _prot = set()
            if os.environ.get('SEED_PROTECT') == '1':
                _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
                for j in _carved:
                    if int((self.phi[j] < 0).sum()) >= _pmin:
                        _prot.add(j)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k and j not in _prot:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            if os.environ.get('SEED_CARVED_DBG') == '1' and _carved:
                print('[SEEDCARVED] k=%d carved=%s protected=%s'
                      % (k, _carved, sorted(_prot)), flush=True)
"""

# ── 主分支（8 空格）──
B_OLD = """        self._seed_undo_note(k, sdf, undo)
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], -sdf)
"""
B_NEW = """        self._seed_undo_note(k, sdf, undo)
        # ★ s304：(1) 写前先记"谁会被擦到"；(2) 保护已有实质核（同 along 分支）
        _carved = [j for j in range(self.nreg)
                   if j != k and (-sdf > self.phi[j]).any()]
        _prot = set()
        if os.environ.get('SEED_PROTECT') == '1':
            _pmin = int(os.environ.get('SEED_PROTECT_MIN', '100') or 100)
            for j in _carved:
                if int((self.phi[j] < 0).sum()) >= _pmin:
                    _prot.add(j)
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k and j not in _prot:
                self.phi[j] = np.maximum(self.phi[j], -sdf)
        if os.environ.get('SEED_CARVED_DBG') == '1' and _carved:
            print('[SEEDCARVED] k=%d carved=%s protected=%s'
                  % (k, _carved, sorted(_prot)), flush=True)
"""


def main():
    with open(WS, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for nm, old in (("along", A_OLD), ("main", B_OLD)):
        c = t.count(old)
        print("  锚点 %-6s 出现 %d 次 %s" % (nm, c, "✓" if c == 1 else "❌"))
        ok &= (c == 1)
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入"); return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
    tmp = WS + ".s304tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc); os.remove(tmp); return 1
    os.remove(tmp)
    bak = WS + ".bak_s304prot"
    if not os.path.exists(bak):
        shutil.copy2(WS, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(WS, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(WS, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("_carved = [j for j in range(self.nreg)") == 2, "写前掩码 2 处"),
        (t3.count("j not in _prot") == 2, "保护跳过 2 处"),
        (t3.count("SEED_PROTECT") == 2, "保护门控 2 处"),
        (t3.count("SEED_CARVED_DBG") == 2, "carved 记账 2 处"),
        (t3.count("[SEEDCARVED]") == 2, "独有成功串 2 处"),
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
    print("✅ s304 核保护 + carved 量具修复完成（默认全关；归档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
