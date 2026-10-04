#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_blockparallel.py --- s293：**平行建块**（块数 = B，前 B 个事件各建一个新块）。

## 为什么不是「K = ceil(n/B) = 8」（**我自己先算错了，这里留档**）
用户的选项 (a) 文字里我写的是 `K = ceil(n/B) = 8`。**代数错了**：
闭式是 `实际块数 = ceil(N / K)`，`N = B·n`；要它 `= B`：
    `(B−1) < B·n/K ≤ B`  ⇒  **`n ≤ K < B·n/(B−1)`**  ⇒ **`K = n` 是唯一整数解**（与 B 无关）
取 `K = ceil(n/B) = ceil(23/3) = 8` ⇒ 实际块数 `ceil(69/8) = ` **9 块**，不是 3 块。
⇒ 引擎 `_bk_exp.py:1123` 那段注释（"**与 B 无关 ⇒ 这是唯一解，不是调出来的**"）**是对的**。

## 真正的缺陷是**次序**，不是 K 的值
`_fresh_now = ((n_ath_tgt % K) == 0)`，`K = 23` ⇒ fresh 落在第 **23 / 46 / 69** 个事件。
而 KM burst 把 **69 根里的 45 根**塞进**首档** ⇒ 第 1..22 个核**全挤进 1 号块**。
实测（对照臂 `t5N276F` 自己的 `series.csv`）：
```
step   0: blk_laths=1     nblk=1 n_var_sig=1
step 400: blk_laths=12    nblk=1 n_var_sig=1     ← 12 根全在一个块、一个变体
step 500: blk_laths=14/1  nblk=2 n_var_sig=1     ← 第 23 个核才建第 2 块
```
两个后果（**都命中用户监控项**）：
1. `n_var_sig = 1` 持续 700 步 ⇒ **自协调的前提不存在**（一个变体谈不上自协调）；
2. burst 首档 45 根里有 22 根必须挤 1 号块的边缘 ⇒ **~20 根就放不下**
   （s291/s292 量到的"20 上限"）。

## 修法（**块数 = B 的本来语义**）
「B 个块、每块 n 根」的正确次序是 **先把 B 个块建出来，再往块里堆**：
```python
if _Bpar and _Bt > 0 and a.nuc_init > 0:
    _fresh_now = (n_fresh_ok < _Bt)          # 前 B 个成功事件各建一个新块
    _nf, _ns = (1, 0) if _fresh_now else (0, 1)
```
* 块数 = **B（规定的）**，每块最终 ≈ `n(T_end)` 根 ⇒ 总量 `B·n` 不变 ✓
* burst 首档 45 根摊到 3 个块 ⇒ 每块 ≈15 根 ⇒ **放得下**（20 上限不再是瓶颈）✓
* 3 个块各取一个变体（`--var-rule` 决定）⇒ `n_var_sig ≥ 2` ⇒ **自协调成为可能** ✓
* **惰性**：`--nuc-block-parallel 0`（默认）⇒ 整段不进 ⇒ 归档臂**逐位不变** ✓
  （`--nuc-fresh-every` 的旧规则原样保留，N8 硬校验也原样保留）

自检：锚点唯一性 + 语法编译 + 备份 + 写后复验（锚点避开本补丁自己的注释）。
"""
import hashlib
import os
import py_compile
import shutil
import sys

BK = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"
TS = "/mnt/f/speed_up/pipeline/ca_pf_framework/_t5_short.py"

# ── ① argparse：新增开关 ──
A1_OLD = "    ap.add_argument('--nuc-fresh-every', type=int, default=0,\n"
A1_NEW = ("    ap.add_argument('--nuc-block-parallel', type=int, default=0, choices=(0, 1),\n"
          "                    help='\\u2605 s293\\uff1a\\u5757\\u6570 = B\\uff08\\u524d B \\u4e2a\\u4e8b\\u4ef6\\u5404\\u5efa\\u65b0\\u5757\\uff09\\u3002"
          "0=\\u65e7\\u89c4\\u5219\\uff08\\u9010\\u4f4d\\u4e0d\\u53d8\\uff09')\n"
          + A1_OLD)

# ── ② N8 硬校验：平行建块档跳过（并打印新规则）──
A2_OLD = """            _K_exp = int(_n_law)
            _K_got = int(getattr(a, 'nuc_fresh_every', 0) or 0)
            if a.nuc_init <= 0:
"""
A2_NEW = """            _K_exp = int(_n_law)
            _K_got = int(getattr(a, 'nuc_fresh_every', 0) or 0)
            # ★★★★★★ s293（**平行建块**；用户 2026-10-04 批准）
            #   ## 为什么不是「K = ceil(n/B)」
            #     闭式 `实际块数 = ceil(B·n / K)`，要它 `= B` ⇒ **`K = n` 是唯一整数解**
            #     （与 B 无关）。取 `K = ceil(n/B) = 8` ⇒ 实际 **9 块**，不是 3 块。
            #     ⇒ 引擎下面那段注释是对的；**缺陷在"次序"不在"K 的值"**。
            #   ## 真正缺陷
            #     `K = n = 23` ⇒ fresh 落在第 23/46/69 个事件，
            #     而 burst 把 45 根塞进首档 ⇒ **前 22 个核全挤进 1 号块**。
            #     实测（`t5N276F` 的 `series.csv`）：`step 400: nblk=1, n_var_sig=1`。
            #   ## 本开关的语义（**「B 个块、每块 n 根」的本来次序**）
            #     先把 B 个块建出来，再往块里堆 ⇒ 块数 = B（规定的），每块 ≈ n 根。
            _Bpar = bool(int(getattr(a, 'nuc_block_parallel', 0) or 0))
            if _Bpar and _Bt0 > 0:
                P('      \\u2605\\u2605\\u2605 **\\u5e73\\u884c\\u5efa\\u5757\\uff08`--nuc-block-parallel 1`\\uff09**\\uff1a'
                  '\\u524d **B = %d** \\u4e2a\\u6210\\u529f\\u4e8b\\u4ef6\\u5404\\u5efa\\u4e00\\u4e2a**\\u65b0\\u5757**\\uff0c'
                  '\\u4e4b\\u540e\\u624d\\u8f6c `stack`'
                  ' \\u21d2 \\u5757\\u6570 = B = %d\\uff08**\\u89c4\\u5b9a\\u7684**\\uff09\\uff0c'
                  '\\u6bcf\\u5757\\u6700\\u7ec8 \\u2248 n(T_end) = %d \\u6839' % (_Bt0, _Bt0, _K_exp))
                P('         \\u65e7\\u89c4\\u5219\\uff08`K = n(T_end) = %d`\\uff09\\u628a fresh \\u653e\\u5728'
                  '\\u7b2c %d/%d/%d\\u2026 \\u4e2a\\u4e8b\\u4ef6 \\u21d2 **\\u524d %d \\u4e2a\\u6838\\u5168\\u6324\\u8fdb 1 \\u53f7\\u5757**'
                  '\\uff08\\u5b9e\\u6d4b `t5N276F`\\uff1a\\u524d 400 \\u6b65 nblk=1\\u3001n_var_sig=1\\uff09'
                  ' \\u21d2 \\u81ea\\u534f\\u8c03\\u4e0d\\u53ef\\u80fd + burst \\u9996\\u6863\\u88ab\\u62d2\\u3002'
                  % (_K_exp, _K_exp, 2 * _K_exp, 3 * _K_exp, _K_exp - 1))
            elif a.nuc_init <= 0:
"""

# ── ③ athermal 块：新的 fresh/stack 规则 ──
A3_OLD = """                _K = int(getattr(a, 'nuc_fresh_every', 0) or 0)
                if _K > 0 and a.nuc_init > 0:
                    _fresh_now = ((n_ath_tgt % _K) == 0)
                    _nf, _ns = (1, 0) if _fresh_now else (0, 1)
                else:
                    _nf, _ns = (1 if a.nuc_init > 0 else 0), 1
"""
A3_NEW = """                _K = int(getattr(a, 'nuc_fresh_every', 0) or 0)
                # ★★★★★★ s293：**平行建块**（前 B 个成功事件各建一个新块）——
                #   见上面 N8 区的长注释。默认关 ⇒ 逐位不变。
                _Bpar2 = bool(int(getattr(a, 'nuc_block_parallel', 0) or 0))
                if _Bpar2 and int(_Bt) > 0 and a.nuc_init > 0:
                    _fresh_now = (n_fresh_ok < int(_Bt))
                    _nf, _ns = (1, 0) if _fresh_now else (0, 1)
                elif _K > 0 and a.nuc_init > 0:
                    _fresh_now = ((n_ath_tgt % _K) == 0)
                    _nf, _ns = (1, 0) if _fresh_now else (0, 1)
                else:
                    _nf, _ns = (1 if a.nuc_init > 0 else 0), 1
"""

# ── ④ 计数器初始化 ──
A4_OLD = "    n_ath_tgt = 0                # 当前的累计根数（不含预摆的第 1 片）\n"
A4_NEW = (A4_OLD +
          "    n_fresh_ok = 0               # ★ s293：**成功建立的新块数**"
          "（`--nuc-block-parallel` 用；旧档不读）\n")

# ── ⑤ 断点续跑：恢复 ──
A5_OLD = "            n_ath_tgt = int(_rb_drv.get('n_ath_tgt', n_ath_tgt))\n"
A5_NEW = (A5_OLD +
          "            n_fresh_ok = int(_rb_drv.get('n_fresh_ok', n_fresh_ok))\n")

# ── ⑥ 断点续跑：保存 ──
A6_OLD = "                             n_ath_ev=n_ath_ev, n_ath_tgt=n_ath_tgt,\n"
A6_NEW = "                             n_ath_ev=n_ath_ev, n_ath_tgt=n_ath_tgt,\n                             n_fresh_ok=n_fresh_ok,\n"

# ── ⑦ 成功计数（**必须放在 `if _ev:` 里**）──
A7_OLD = """                if _ev:
                    n_eng_ev += len(_ev)
                    n_ath_ev += 1
"""
A7_NEW = """                if _ev:
                    n_eng_ev += len(_ev)
                    n_ath_ev += 1
                    # ★ s293：只有**成功**且**要的是 fresh** 才记一个新块
                    if _nf > 0:
                        n_fresh_ok += 1
"""

# ── ⑧ `_t5_short.py` 透传 ──
B1_OLD = "            (['--nuc-fresh-every', str(a.nuc_fresh_every)]\n"
B1_NEW = ("            (['--nuc-block-parallel', str(a.nuc_block_parallel)]\n"
          "             if int(getattr(a, 'nuc_block_parallel', 0) or 0) > 0 else []) +\n"
          + B1_OLD)

B2_OLD = "    ap.add_argument('--nuc-fresh-every', type=int, default=0,\n"
B2_NEW = ("    ap.add_argument('--nuc-block-parallel', type=int, default=0, choices=(0, 1),\n"
          "                    help='s293: \\u5757\\u6570 = B\\uff08\\u524d B \\u4e2a\\u4e8b\\u4ef6\\u5404\\u5efa\\u65b0\\u5757\\uff09')\n"
          + B2_OLD)


def patch(path, pairs, bak_suffix):
    with open(path, "r", encoding="utf-8") as fh:
        t = fh.read()
    ok = True
    for i, (old, _new) in enumerate(pairs):
        n = t.count(old)
        print("  [%s] 锚点 %d 出现 %d 次 %s" % (os.path.basename(path), i + 1, n,
                                              "✓" if n == 1 else "❌"))
        if n != 1:
            ok = False
    if not ok:
        print("  ❌ 锚点不唯一 ⇒ 拒绝写入 %s" % path)
        return None
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t
    for old, new in pairs:
        t2 = t2.replace(old, new, 1)
    h1 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    tmp = path + ".s293tmp"
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
    bak = path + bak_suffix
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("  备份 → %s" % os.path.basename(bak))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(t2)
    print("  sha256 %s → %s（%d → %d B）" % (h0[:12], h1[:12], len(t), len(t2)))
    return t2


def main():
    print("=== ① _bk_exp.py ===")
    t3 = patch(BK, [(A1_OLD, A1_NEW), (A2_OLD, A2_NEW), (A3_OLD, A3_NEW),
                    (A4_OLD, A4_NEW), (A5_OLD, A5_NEW), (A6_OLD, A6_NEW),
                    (A7_OLD, A7_NEW)], ".bak_s293bpar")
    if t3 is None:
        return 1
    print("=== ② _t5_short.py ===")
    t4 = patch(TS, [(B1_OLD, B1_NEW), (B2_OLD, B2_NEW)], ".bak_s293bpar")
    if t4 is None:
        return 1

    print("=== ③ 写后复验（锚点串**避开本补丁自己的注释**：用带缩进的代码行）===")
    checks = [
        (t3.count("\n            _Bpar = bool(int(getattr(a, 'nuc_block_parallel', 0) or 0))") == 1,
         "bk: _Bpar 定义 1 处"),
        (t3.count("\n                _Bpar2 = bool(int(getattr(a, 'nuc_block_parallel', 0) or 0))") == 1,
         "bk: _Bpar2 定义 1 处"),
        (t3.count("\n                    _fresh_now = (n_fresh_ok < int(_Bt))") == 1,
         "bk: 新规则 1 处"),
        (t3.count("\n    n_fresh_ok = 0 ") == 1, "bk: 计数器初始化 1 处"),
        (t3.count("\n                    if _nf > 0:\n                        n_fresh_ok += 1") == 1,
         "bk: 成功计数 1 处"),
        (t3.count("n_fresh_ok=n_fresh_ok,") == 1, "bk: 检查点保存 1 处"),
        (t3.count("_rb_drv.get('n_fresh_ok'") == 1, "bk: 检查点恢复 1 处"),
        (t3.count("ap.add_argument('--nuc-block-parallel'") == 1, "bk: argparse 1 处"),
        (t4.count("ap.add_argument('--nuc-block-parallel'") == 1, "t5_short: argparse 1 处"),
        (t4.count("(['--nuc-block-parallel', str(a.nuc_block_parallel)]") == 1,
         "t5_short: 透传 1 处"),
    ]
    allok = True
    for cond, label in checks:
        print("  %-34s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    if not allok:
        print("❌ 写后复验失败 ⇒ 请从 .bak_s293bpar 恢复")
        return 1
    print("✅ s293 平行建块完成（`--nuc-block-parallel` 门控；默认档逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
