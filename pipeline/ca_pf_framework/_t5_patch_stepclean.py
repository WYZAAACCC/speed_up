#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_stepclean.py --- s303：**周期性连通性清理**（`SEED_CLEAN_EVERY=<N>`，默认关）。

## 为什么还要它（`t10FIX` @ step 100 实测）
s301c 把「播种后清理」修好并使用后，⑦ 从 **27% → 79%**（J1 PASS），但仍有 **8/38 场带 1–3 个小碎片**
（分量数 中位 1、均值 1.37、最大 4）。而本跑 `[SEEDCLEAN] … carved_j=0` **一次都没触发**
⇒ **碎片不是播种期擦除造成的，是演化期再分裂出来的。**

## 修法
在步循环里 `g.advance()` **之后**，按 `SEED_CLEAN_EVERY` 的周期对**全部场**做一次
`keep_largest_neg`（保留最大 26-连通块、清掉其余）。**与 s301c 同一条表示约定**：
「一个相场 = 一根板条」⇒ 演化期冒出来的第二块同样是表示层的多余物，应当清掉。
* 门控：`SEED_CLEAN_EVERY` 未设或 ≤0 ⇒ **整段不进，归档逐位不变** ✓
* 代价：每 N 步一次全 nv 的 labeling（N=160/nv=220 时约 20–60 s），**摊到 N 步上可忽略**
* **独有成功串** `[SEEDCLEAN-STEP] step=.. dropped=..` ⇒ 跑没跑是**可观测**的

自检：锚点唯一 + 语法编译 + 备份 + 写后复验。
"""
import hashlib
import os
import py_compile
import shutil
import sys

BK = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"

OLD = """            g.advance(dt, **kw)
"""
NEW = """            g.advance(dt, **kw)
            # ★★★★★★ s303（**周期性连通性清理**）；未设 `SEED_CLEAN_EVERY` ⇒ 整段不进
            #   ## 为什么（t10FIX @step100 实测）
            #     s301c 的"播种后清理"修好后 ⑦ 从 27%→79%（J1 PASS），但仍 8/38 场带小碎片，
            #     而本跑 `carved_j=0` 一次未触发 ⇒ **碎片来自演化期再分裂**，不是播种期擦除。
            #   ## 修法：同一条表示约定（一个相场 = 一根板条），周期性地保留最大连通块。
            #   ## 独有成功串 ⇒ "跑没跑"可观测（不再重犯"把沉默当无事可做"的错）。
            if os.environ.get('SEED_CLEAN_EVERY'):
                try:
                    _ce = int(os.environ['SEED_CLEAN_EVERY'])
                except Exception:
                    _ce = 0
                if _ce > 0 and it % _ce == 0:
                    _nd = 0
                    for _j in range(1, g.nreg):
                        _nd += g.keep_largest_neg(_j)
                    if _nd > 0:
                        print('[SEEDCLEAN-STEP] step=%d dropped=%d' % (it, _nd),
                              flush=True)
"""


def main():
    with open(BK, "r", encoding="utf-8") as fh:
        t = fh.read()
    n = t.count(OLD)
    print("  锚点出现 %d 次 %s" % (n, "✓" if n == 1 else "❌"))
    if n != 1:
        print("❌ 锚点不唯一 ⇒ 拒绝写入"); return 1
    if "\nimport os" not in t and "\nimport os\n" not in t:
        print("  ⚠ _bk_exp.py 顶层未见 `import os` —— 需先确认")
    h0 = hashlib.sha256(t.encode("utf-8")).hexdigest()
    t2 = t.replace(OLD, NEW, 1)
    tmp = BK + ".s303tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
        print("  ✅ 语法编译通过")
    except py_compile.PyCompileError as exc:
        print("  ❌ 语法错 ⇒ 拒绝写入：%s" % exc); os.remove(tmp); return 1
    os.remove(tmp)
    bak = BK + ".bak_s303step"
    if not os.path.exists(bak):
        shutil.copy2(BK, bak); print("  备份 → %s" % os.path.basename(bak))
    with open(BK, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(BK, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    checks = [
        (t3.count("            g.advance(dt, **kw)\n") == 1, "advance 行仍在 1 处"),
        (t3.count("if os.environ.get('SEED_CLEAN_EVERY'):") == 1, "周期门控 1 处"),
        (t3.count("[SEEDCLEAN-STEP]") == 1, "独有成功串 1 处"),
        (t3.count("_nd += g.keep_largest_neg(_j)") == 1, "调用 1 处"),
        (t3.count("_eta_sc * med > fcrit") == 0, "（此表在 windowB，跳过）"),
    ]
    allok = True
    for cond, label in checks[:-1]:
        print("  写后复验 %-28s %s" % (label, "✓" if cond else "❌"))
        allok &= bool(cond)
    print("  sha256 %s → %s（%d → %d B）"
          % (h0[:12], hashlib.sha256(t3.encode()).hexdigest()[:12], len(t), len(t3)))
    if not allok:
        print("❌ 写后复验失败"); return 1
    print("✅ s303 周期性清理完成（SEED_CLEAN_EVERY=<N> 才启用；默认逐位不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
