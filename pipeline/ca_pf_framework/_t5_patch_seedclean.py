#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_seedclean.py --- s301：**播种后连通性清理**（`--nuc-occ-guard 2`，默认 0/1 不变）

## 为什么走这条（三条机制假说均被自己的判据否掉）
| 假说 | 判据 | 结果 |
|---|---|---|
| 同一场被播多次 | SEEDDBG 真放按场号计数（守卫 ON） | **空** ⇒ 否证（守卫已修，但不足以解决） |
| `sdf` 本身不连通 | `_t10_sdftest.py` 逐字复刻公式 30 例 × 2 分支 | **0/30 多连通** ⇒ 否证 |
| 后播籽晶擦断 | `_t10_erode.py` 连线被他场占据比例 | **中位 0.067** ⇒ 否证 |
而实测仍在：`t10OCC` step 1 有 9/15 场多块（守卫 ON、每场真放一次），
三维图显示**主体是一根板条 + 一个 166 胞的孤立小球**。

## 本条修法（**表示约定层面，物理上正当**）
模型的设计意图是 **「一个相场 = 一根板条」**（`field 0` 之外每个场恰好一根）。
⇒ 若一次播种后 `phi[k] < 0` 出现**多个 26-连通块**，那第二块**不对应任何真实板条**，
是数值伪影 ⇒ **只保留最大块，其余置正**（清掉）。

* **物理正确**：清掉的是伪影，不是板条；模型因此与它自己的表示约定一致。
* **工程可实现**：只在**真实播种且场原本为空**时做一次，作用域限于该场的**包围盒**
  （籽晶足迹约 10³ 胞 ⇒ 极便宜）；用 `scipy.ndimage.label`，惰性导入。
* **门控**：`--nuc-occ-guard 2` 才启用（0=关、1=仅占用守卫）；**默认档逐位不变**。

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

# 辅助方法：插在 _seed_undo_apply 之后
H_OLD = """    def _seed_undo_apply(self, undo):
        \"\"\"★ R479：按 `_seed_undo_note` 记下的内容把 `phi` **精确还原**。\"\"\"
        for (j, ii, vals) in undo:
            self.phi[j].reshape(-1)[ii] = vals
"""
H_NEW = H_OLD + '''
    def keep_largest_neg(self, k):
        """★ s301：把 `phi[k] < 0` 只保留**最大 26-连通块**，其余置正（清数值伪影）。

        ## 依据
        模型表示约定是「一个相场 = 一根板条」。实测（`t10OCC` step 1，守卫 ON、
        每场只真放一次）仍有 9/15 个场含 2–3 块，且三维图显示主体是板条、
        另一块是**孤立的 166 胞小球**。三条机制假说（重复播种 / sdf 不连通 /
        后播擦断）均被各自判据否掉 ⇒ 按**表示约定**清理伪影，是物理上正当的止损。

        ⚠ 只在**真实播种**（`undo is None`）后调用；**探针路径绝不调用**
          （探针要的是"真放再精确回滚"，清理会破坏它的语义）。
        返回被清掉的胞数。
        """
        try:
            from scipy import ndimage
        except Exception:
            return -1
        m = self.phi[k] < 0
        n = int(m.sum())
        if n <= 1:
            return 0
        idx = np.argwhere(m)
        lo = idx.min(0); hi = idx.max(0) + 1
        sub = m[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        lab, nc = ndimage.label(sub, structure=ndimage.generate_binary_structure(3, 3))
        if nc <= 1:
            return 0
        sz = np.bincount(lab.ravel())[1:]
        keep = int(np.argmax(sz)) + 1
        drop = (lab != keep) & (lab > 0)
        nd = int(drop.sum())
        if nd == 0:
            return 0
        sl = (slice(lo[0], hi[0]), slice(lo[1], hi[1]), slice(lo[2], hi[2]))
        cur = self.phi[k][sl]
        # 置正：取绝对值（并加一个小量，确保严格 > 0）
        cur[drop] = np.abs(cur[drop]) + 1e-12
        self.phi[k][sl] = cur
        return nd
'''

# ① along 分支（12 空格缩进）
A_OLD = """            self._seed_undo_note(k, sdf, undo)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            return
"""
A_NEW = """            self._seed_undo_note(k, sdf, undo)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            # ★ s301：真实播种后清掉 φ<0 的多余连通块（`--nuc-occ-guard 2` 才启用）
            if undo is None and int((getattr(self, '_nuc', None) or {})
                                    .get('occ_guard', 0) or 0) >= 2:
                self.keep_largest_neg(k)
            return
"""

# ② 主分支（8 空格缩进，函数末尾）
B_OLD = """        self._seed_undo_note(k, sdf, undo)
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], -sdf)
"""
B_NEW = """        self._seed_undo_note(k, sdf, undo)
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], -sdf)
        # ★ s301：真实播种后清掉 φ<0 的多余连通块（`--nuc-occ-guard 2` 才启用）
        if undo is None and int((getattr(self, '_nuc', None) or {})
                                .get('occ_guard', 0) or 0) >= 2:
            self.keep_largest_neg(k)
"""


def main():
    with open(WS, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for nm, old in (("helper", H_OLD), ("along", A_OLD), ("main", B_OLD)):
        c = t.count(old)
        print("  锚点 %-7s 出现 %d 次 %s" % (nm, c, "✓" if c == 1 else "❌"))
        ok &= (c == 1)
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入")
        return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(H_OLD, H_NEW, 1).replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = WS + ".s301tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc)
        os.remove(tmp); return 1
    os.remove(tmp)
    bak = WS + ".bak_s301clean"
    if not os.path.exists(bak):
        shutil.copy2(WS, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(WS, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(WS, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("def keep_largest_neg(self, k):") == 1, "helper 1 处"),
        (t3.count("self.keep_largest_neg(k)") == 2, "调用 2 处"),
        (t3.count("if undo is None and int((getattr(self, '_nuc', None) or {})") == 2,
         "门控 2 处（undo is None）"),
        (t3.count("self._seed_undo_note(k, sdf, undo)") == 2, "原记账点仍在 2 处"),
        (t3.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
        (t3.count("if os.environ.get('SEED_DBG') == '1':") == 2, "s299 记账仍在位"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-28s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s301 播种连通性清理完成（`--nuc-occ-guard 2` 才启用；默认逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
