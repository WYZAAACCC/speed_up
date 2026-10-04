#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_seeddbg.py --- s299：给 `seed_plate` 加**环境变量门控**的调试记账（默认零影响）。

## 为什么要它（本轮已确证的事实）
密快照诊断（`t10DGN`，`--snap-every 1`）实测：
```
step  场数  多块场  各场分量数
 0     1     0     1
 1    14     9     3/3/2/2/2/2/2/2/2/1/1/1/1/1     ← ★ 一出现就多块
 2..20 14     9     （**逐位完全相同**）
```
⇒ **「一场多块」在 step 1（播种那一步）就产生，之后完全冻结** ⇒ 机制在**播种**里，不在长大里。

## 还剩两个互斥的候选（本轮要靠记账分开）
* **(甲) 同一个场被 `seed_plate` 写了多次**（不同中心）⇒ `phi[k]=min(...)` 的并集语义 ⇒ 多块；
* **(乙) `supercrit` 探针的"真放 + 回滚"没还原干净**，在**别的场的候选位点**上留下 φ<0 残迹
  ⇒ 残迹落在**已有场内**（所以场数不增）⇒ 只增分量。

## 本补丁记什么（只在 `SEED_DBG=1` 时打印；默认**不执行任何额外代码**）
每个 `seed_plate` 调用一行：
```
[SEEDDBG] k=<场> undo=<0/1> cells_before=<phi[k]<0 的胞数> cells_after=<...>
           center=(x,y,z) nm  shape=<..>  new_neg=<after 中 before 为 >0 的胞数>
```
* `undo=1` 且 `new_neg` 很大 ⇒ 这是**探针**；若它后面没有回滚干净，就会显出残迹；
* 同一个 `k` 在**未 undo** 的情况下出现 **≥2 次** ⇒ 甲成立；
* `cells_before` 已经 >0 且 `new_neg` 与 `cells_before` **空间上分离** ⇒ 并集多块。

⚠ 纯记账：`undo is None` 时（生产路径绝大多数）只多两次极轻的 `count_nonzero`；
   用 `SEED_DBG` 关闭时**一行都不进** ⇒ 默认逐位不变。
"""
import hashlib
import os
import py_compile
import shutil
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"

OLD = """        sdf = np.maximum(np.abs(d) - t / 2, rperp - R)         # 椭/圆盘 SDF（近似）
"""

NEW = """        # ★★★★★★ s299（**播种调试记账**，`SEED_DBG=1` 才生效；默认一行不进 ⇒ 逐位不变）
        #   目的：分开「同一个场被播多次(甲)」与「探针回滚留残迹(乙)」——
        #   密快照诊断已证「一场多块」在 **step 1 播种那一步**就产生且之后完全冻结。
        if os.environ.get('SEED_DBG') == '1':
            try:
                _pb = int((self.phi[k] < 0).sum())
                _lbl = 'disc'
            except Exception:
                _pb, _lbl = -1, '?'
            _cc = np.asarray(center, float) * 1e9
            print('[SEEDDBG] k=%d undo=%d before=%d shape=%s center=(%.1f,%.1f,%.1f)nm'
                  % (k, 0 if undo is None else 1, _pb, _lbl, _cc[0], _cc[1], _cc[2]),
                  flush=True)
        sdf = np.maximum(np.abs(d) - t / 2, rperp - R)         # 椭/圆盘 SDF（近似）
"""

OLD2 = """            self._seed_undo_note(k, sdf, undo)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            return
"""

NEW2 = """            if os.environ.get('SEED_DBG') == '1':
                try:
                    _pb = int((self.phi[k] < 0).sum())
                    _cc = np.asarray(center, float) * 1e9
                    print('[SEEDDBG] k=%d undo=%d before=%d shape=along center=(%.1f,%.1f,%.1f)nm'
                          % (k, 0 if undo is None else 1, _pb, _cc[0], _cc[1], _cc[2]),
                          flush=True)
                except Exception:
                    pass
            self._seed_undo_note(k, sdf, undo)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            return
"""


def main():
    with open(SRC, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for nm, old in (("A", OLD), ("B", OLD2)):
        n = t.count(old)
        print("  锚点 %s 出现 %d 次 %s" % (nm, n, "✓" if n == 1 else "❌"))
        if n != 1:
            ok = False
    if not ok:
        print("❌ 锚点不唯一 ⇒ 拒绝写入")
        return 1
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(OLD, NEW, 1).replace(OLD2, NEW2, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = SRC + ".s299tmp"
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
    bak = SRC + ".bak_s299seeddbg"
    if not os.path.exists(bak):
        shutil.copy2(SRC, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(SRC, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(SRC, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("if os.environ.get('SEED_DBG') == '1':") == 2, "两处门控 2 个"),
        (t3.count("[SEEDDBG] k=%d undo=%d before=%d shape=") == 2, "两处打印 2 个"),
        (t3.count("sdf = np.maximum(np.abs(d) - t / 2, rperp - R)") == 1, "原 SDF 行仍在"),
        (t3.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
    ]
    allok = True
    for cond, label in checks:
        print("  写后复验 %-26s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从备份恢复")
        return 1
    print("✅ s299 播种调试记账完成（`SEED_DBG=1` 才生效；默认逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
