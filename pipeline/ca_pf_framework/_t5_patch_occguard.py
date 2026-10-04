#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_occguard.py --- s300：**播种占用守卫**（`--nuc-occ-guard`，默认 0 ⇒ 逐位不变）

## 根因（`t10DBG` 的 SEEDDBG 记账，**铁证**）
```
[SEEDDBG] k=1 undo=0 before=0    shape=along center=(5000.0,5000.0,5000.0)nm   ← 初始籽晶
[SEEDDBG] k=1 undo=1 before=1022 shape=disc  center=(7885.5,5447.1,9381.1)nm   ← 探针（回滚干净✓）
[SEEDDBG] k=1 undo=0 before=1022 shape=along center=(7885.5,5447.1,9381.1)nm   ← ★ 真放，换了位置
[SEEDDBG] k=2..14 undo=0 before=0  （各一次，**before 全为 0**）
调用总次数 16 ；按场号 >1 的**只有 k=1**
```
`seed_plate` 的语义是 `phi[k] = min(phi[k], sdf)`（**并集**）⇒ 同一个场被写两次不同位置
⇒ **一个场里出现两块互不相连、彼此远离、各约一个籽晶大小的板条**。
密快照诊断另证：**该多块在 step 1（播种那一步）就产生，step 1→20 逐位冻结**、且**与 η 无关**。

## 修法（**物理正确 + 工程可实现**）
* 物理：**一个相场 = 一根板条**是本模型的**表示约定**；把第二块写进同一个场不对应任何真实物理。
* 工程：**不改择优准则**，只在**同一准则下把已占用的场排除**（`ed` 的 `argmax` 在"空闲场"集合里取）。
  零新增求解；占用表每次 `nucleate()` **只算一次**（不是每个候选算一次）。
* `--nuc-occ-guard 0`（默认）⇒ 整段不进 ⇒ **归档逐位不变** ✓

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

WS = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"
BK = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"
TS = "/mnt/f/speed_up/pipeline/ca_pf_framework/_t5_short.py"

# ── ① windowB_surface：nuc_cfg 签名加 occ_guard ──
W1_OLD = "                supercrit=False, sites_refill=False, sites_margin=4,\n"
W1_NEW = ("                supercrit=False, sites_refill=False, sites_margin=4,\n"
          "                occ_guard=False,\n")

# ── ② windowB_surface：把 occ_guard 写进 cfg ──
W2_OLD = "                         supercrit=bool(supercrit),\n"
W2_NEW = ("                         supercrit=bool(supercrit),\n"
          "                         occ_guard=bool(occ_guard),   # ★ s300 占用守卫\n")

# ── ③ windowB_surface：fresh 通道的择优加占用过滤 ──
W3_OLD = """                else:                                   # 'ed'（默认）
                    _ks = [int(np.argmax(drv)) + 1]
"""
W3_NEW = """                else:                                   # 'ed'（默认）
                    _ks = [int(np.argmax(drv)) + 1]
                # ★★★★★★ s300（**播种占用守卫**）；`--nuc-occ-guard 0`（默认）⇒ 整段不进
                #   ## 根因（`t10DBG` 的 SEEDDBG 记账，见 `_t5_patch_occguard.py` 头部）
                #     `seed_plate` 是**并集**语义 `phi[k]=min(phi[k],sdf)`；
                #     而 `fresh` 通道按 `argmax(drv)` 直接取场号、**不检查该场是否已被占用**
                #     ⇒ 同一个场被写进第二块（不同中心）⇒ **一场多块**（实测 k=1 被写了两次真放）。
                #     密快照诊断：该多块 **step 1 就出现、step 1→20 逐位冻结、与 η 无关** ✓
                #   ## 修法：**同一择优准则下把已占用的场排除**（不改准则本身）
                #     占用表**每次调用只算一次**（`(phi[1:]<0).any(axis=(1,2,3))`，
                #     nv=220·N=160 时约 1–2 s）——不是每个候选算一次 ⇒ 代价可控。
                if bool(c.get('occ_guard', False)):
                    _occ = (self.phi[1:] < 0).any(axis=(1, 2, 3))     # 长度 nv
                    _free = ~_occ
                    _kd = int(_ks[0]) if _ks else 0
                    if _kd >= 1 and (not _free[_kd - 1]):
                        _d2 = np.where(_free, drv, -np.inf)
                        if np.isfinite(_d2).any():
                            _ks = [int(np.argmax(_d2)) + 1]
                        else:
                            _ks = []          # 无空场 ⇒ 本候选不投放（调用方会退回 stack）
"""

# ── ④ _bk_exp.py：传参 + argparse ──
B1_OLD = "                  sites_refill=bool(int(getattr(a, 'nuc_sites_refill', 0))),\n"
B1_NEW = (B1_OLD +
          "                  occ_guard=bool(int(getattr(a, 'nuc_occ_guard', 0))),"
          "   # ★ s300 占用守卫\n")
B2_OLD = "    ap.add_argument('--nuc-block-parallel', type=int, default=0, choices=(0, 1),\n"
B2_NEW = ("    ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1),\n"
          "                    help='s300: \\u64ad\\u79cd\\u5360\\u7528\\u5b88\\u536b"
          "\\uff08\\u4e00\\u4e2a\\u573a\\u53ea\\u64ad\\u4e00\\u5757\\uff09\\uff1b0=\\u65e7\\u884c\\u4e3a')\n"
          + B2_OLD)

# ── ⑤ _t5_short.py：透传 + argparse ──
T1_OLD = "            (['--nuc-block-parallel', str(a.nuc_block_parallel)]\n"
T1_NEW = ("            (['--nuc-occ-guard', str(a.nuc_occ_guard)]\n"
          "             if int(getattr(a, 'nuc_occ_guard', 0) or 0) > 0 else []) +\n"
          + T1_OLD)
T2_OLD = "    ap.add_argument('--nuc-block-parallel', type=int, default=0, choices=(0, 1),\n"
T2_NEW = ("    ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1),\n"
          "                    help='s300: \\u64ad\\u79cd\\u5360\\u7528\\u5b88\\u536b')\n"
          + T2_OLD)


def patch(path, pairs, suffix):
    with open(path, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for i, (old, _n) in enumerate(pairs):
        c = t.count(old)
        print("  [%s] 锚点%d 出现 %d 次 %s" % (os.path.basename(path), i + 1, c,
                                             "✓" if c == 1 else "❌"))
        if c != 1:
            ok = False
    if not ok:
        print("  ❌ 锚点不唯一 ⇒ 拒绝写入 %s" % path)
        return None
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t
    for old, new in pairs:
        t2 = t2.replace(old, new, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = path + ".s300tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过：%s" % os.path.basename(path))
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc)
        os.remove(tmp)
        return None
    os.remove(tmp)
    bak = path + suffix
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(t2)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t2)))
    return t2


def main():
    print("=== ① windowB_surface.py ===")
    w = patch(WS, [(W1_OLD, W1_NEW), (W2_OLD, W2_NEW), (W3_OLD, W3_NEW)], ".bak_s300occ")
    if w is None:
        return 1
    print("=== ② _bk_exp.py ===")
    b = patch(BK, [(B1_OLD, B1_NEW), (B2_OLD, B2_NEW)], ".bak_s300occ")
    if b is None:
        return 1
    print("=== ③ _t5_short.py ===")
    s = patch(TS, [(T1_OLD, T1_NEW), (T2_OLD, T2_NEW)], ".bak_s300occ")
    if s is None:
        return 1
    print("=== ④ 写后复验（锚点用带缩进的代码行，避开本补丁自己的注释）===")
    checks = [
        (w.count("\n                if bool(c.get('occ_guard', False)):") == 1, "ws: 门控 1 处"),
        (w.count("_occ = (self.phi[1:] < 0).any(axis=(1, 2, 3))") == 1, "ws: 占用表 1 处"),
        (w.count("_d2 = np.where(_free, drv, -np.inf)") == 1, "ws: 空闲择优 1 处"),
        (w.count("occ_guard=bool(occ_guard),") == 1, "ws: cfg 写入 1 处"),
        (b.count("occ_guard=bool(int(getattr(a, 'nuc_occ_guard', 0))),") == 1, "bk: 传参 1 处"),
        (b.count("ap.add_argument('--nuc-occ-guard'") == 1, "bk: argparse 1 处"),
        (s.count("ap.add_argument('--nuc-occ-guard'") == 1, "t5: argparse 1 处"),
        (s.count("(['--nuc-occ-guard', str(a.nuc_occ_guard)]") == 1, "t5: 透传 1 处"),
        (w.count("_eta_sc * med > fcrit") == 1, "s296 形核闸门仍在位"),
        (w.count("_fresh_now = (n_fresh_ok < int(_Bt))") == 0, "（此表在 _bk_exp，跳过）"),
    ]
    allok = True
    for cond, label in checks[:-1]:
        print("  %-30s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从 .bak_s300occ 恢复")
        return 1
    print("✅ s300 播种占用守卫完成（`--nuc-occ-guard` 门控；默认档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
