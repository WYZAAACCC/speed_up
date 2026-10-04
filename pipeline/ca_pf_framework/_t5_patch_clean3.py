#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_clean3.py --- s301c：清理门控改读**环境变量** + 打独有成功串。

## 缺陷（`t10CLN` 实测：清理 ON 与守卫 ON 逐位相同）
s301/s301b 门控读 `self._nuc`，而 `windowB_surface.py:2856-2865` **自己写明**：
`self._nuc` 只在 `nuc_cfg()` 里创建，而驱动层 `_seed_next()` 会**先**调 `seed_plate`
⇒ 播种时 `self._nuc` 不存在 ⇒ `{}` ⇒ 门控**恒 False** ⇒ **清理从未执行**。
**⇒ 我把"沉默"当成了"无事可做"**（同 AGENTS.md P44）。

## 本次修法（**最不易出错**）
门控改读 **环境变量** `SEED_CLEAN=1`（`os` 已在该文件导入 —— s299 的 `SEED_DBG` 同款）
⇒ **与构造顺序、与 `self._nuc`、与任何对象状态都无关**；由启动器控制。
并打**独有成功串** `[SEEDCLEAN] k=.. dropped=.. carved_j=..`
⇒ 以后"它跑没跑"是**可观测**的，不再靠沉默推断。
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

GATE_OLD = """            if undo is None and int((getattr(self, '_nuc', None) or {})
                                    .get('occ_guard', 0) or 0) >= 2:
"""
GATE_NEW = """            # ★ s301c：门控改读**环境变量**（`self._nuc` 在驱动层播种时还不存在
            #   ⇒ 旧门控恒 False、清理静默不执行，`t10CLN` 与 `t10OCC` 逐位相同即此故）
            if undo is None and os.environ.get('SEED_CLEAN') == '1':
"""
GATE2_OLD = """        if undo is None and int((getattr(self, '_nuc', None) or {})
                                .get('occ_guard', 0) or 0) >= 2:
"""
GATE2_NEW = """        # ★ s301c：门控改读环境变量（同 along 分支）
        if undo is None and os.environ.get('SEED_CLEAN') == '1':
"""

# 把两处 body 也换成带成功串的版本（缩进各自保持）
A_OLD = GATE_OLD + """                self.keep_largest_neg(k)
                for j in range(self.nreg):
                    if j != k and (-sdf > self.phi[j]).any():
                        self.keep_largest_neg(j)
"""
A_NEW = GATE_NEW + """                _d = self.keep_largest_neg(k)
                _nj = 0
                for j in range(self.nreg):
                    if j != k and (-sdf > self.phi[j]).any():
                        _d += self.keep_largest_neg(j)
                        _nj += 1
                if _d > 0:
                    print('[SEEDCLEAN] k=%d dropped=%d carved_j=%d' % (k, _d, _nj),
                          flush=True)
"""

B_OLD = GATE2_OLD + """            self.keep_largest_neg(k)
            for j in range(self.nreg):
                if j != k and (-sdf > self.phi[j]).any():
                    self.keep_largest_neg(j)
"""
B_NEW = GATE2_NEW + """            _d = self.keep_largest_neg(k)
            _nj = 0
            for j in range(self.nreg):
                if j != k and (-sdf > self.phi[j]).any():
                    _d += self.keep_largest_neg(j)
                    _nj += 1
            if _d > 0:
                print('[SEEDCLEAN] k=%d dropped=%d carved_j=%d' % (k, _d, _nj),
                      flush=True)
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
    tmp = WS + ".s301ctmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc); os.remove(tmp); return 1
    os.remove(tmp)
    bak = WS + ".bak_s301c"
    if not os.path.exists(bak):
        shutil.copy2(WS, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(WS, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(WS, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("os.environ.get('SEED_CLEAN') == '1'") == 2, "env 门控 2 处"),
        (t3.count("[SEEDCLEAN]") == 2, "独有成功串 2 处"),
        (t3.count("getattr(self, '_nuc', None) or {})") == 1, "只剩 periodic_seed 那一处引用"),
        (t3.count("def keep_largest_neg(self, k):") == 1, "helper 仍在位"),
        (t3.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-30s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    h1 = hashlib.sha256(t3.encode("utf-8")).hexdigest()
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复"); return 1
    print("✅ s301c 门控改为 SEED_CLEAN=1（与构造顺序无关）+ 独有成功串")
    return 0


if __name__ == "__main__":
    sys.exit(main())
