#!/usr/bin/env python3
"""
把**溶质拖曳项**补进生产输入：让 `f_loc` 也进 η 方程。

## 为什么必须补（这不是可选项，是修一个真实的不一致）

现在生产模型里：
* `f_loc(c, η)`（含分配项 `A_part·c²·h_solid` 与偏析项 `(Ω₀/w)(c−c₀)h_gb`）
  **只进了 c 方程**（`SplitCHParsed`）
* η 方程（`ACGrGrPolyJ` + `AllenCahn(f_drive)`）**完全没有 c 的贡献**

⇒ 于是 `δF/δη` 与 `δF/δc` 来自**不同的自由能** ⇒ **模型不是变分的**。
仓库自己的笔记（`tests/front1d.i` 文件头）也写着这一点：
「生产的 `A·c²·Ση²` 只进了 c 方程，没进 η 方程，所以**不是变分的**
（源码自述"暂时没有溶质拖曳"）」。

⚠ 这是个**形式上的热力学不一致**，审稿人会抓 —— **与量级无关**。

## 量级（必须先说清楚，避免夸大）

补上之后，η 方程里新增的两项比势垒项小 **9~11 个数量级**：

| 来源 | 量级 | 与势垒之比 |
|---|---|---|
| 分配项 `L·A_part·c²·∂h_solid/∂η` | ~8e-7 | **~6e-9** |
| 偏析项 `L·(Ω₀/w)(c−c₀)·∂h_gb/∂η` | ~6e-10 | **~4e-12** |
| 势垒 `L·mu0·(η³−η+2γηΣ)` | ~130 | 1 |

⇒ **可测量的影响是零。这个补丁的价值是「模型变分自洽」，不是「预测变了」。**
（这也与 T13 的结论一致：拖曳耦合比势垒弱 9 个数量级。）

## 为什么用 `AllenCahn`（而不是自己写核）

`AllenCahn` 的雅可比是**符号完备**的 —— 生产输入自己的注释就写着：
`AllenCahn.C:52` 对角 `∂²F/∂η²`、`:65` 非对角 `∂²F/∂η∂η_j`、
`ACBulk.h:105` 迁移率乘积法则项。
⚠ 这正是 `ACGrGrPoly` **缺**的那一套（所以本项目写了 `ACGrGrPolyJ`）。
⇒ **不要**改用 `ACGrGrPoly` 或 `MatReaction`。

## 代价

* **不增加 JIT**：`f_loc` 已是 `DerivativeParsedMaterial` + `derivative_order = 2`，
  它的一阶/二阶 η 导数**本来就为 `SplitCHParsed` 生成好了**
* 只多 8 个 `AllenCahn` 核（每个序参量一个）

## `coupled_variables` 为什么是 `'c <other 7>'`

两个都要：
* `c` —— 因为 `f_loc` 依赖 c
* **其余 7 个序参量** —— 因为 `L` 是各向异性的、对全部 8 个序参量都有导数，
  `ACBulk::initialSetup` 的 `validateNonlinearCoupling("mob_name")` 会检查，
  缺了会告警且 `_dLdarg[i]` 少项（**雅可比不完备**）。

用法
----
    python3 make_drag_prod.py --src stage1_meltpool_c.i --out x.i --dry-run
    python3 make_drag_prod.py --src stage1_meltpool_c.i --out stage1_meltpool_c.i
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

N = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    out = src
    added = []

    # 每个 [grN_drive] 块之后插入一个 [grN_solute] 块。
    # ⚠ 必须**行首锚定**并用 re.M（本项目的坑：块名在注释里也出现过）。
    for i in range(N):
        others = " ".join(f"gr{j}" for j in range(N) if j != i)
        pat = re.compile(rf"^([ \t]*)\[gr{i}_drive\]\n(?:.*?\n)*?\1\[\]\n", re.M)
        m = pat.search(out)
        if not m:
            sys.exit(f"错误：找不到 [gr{i}_drive] 块 —— 源文件变过了？")
        blk = m.group(0)
        if "type = AllenCahn" not in blk or "f_name = f_drive" not in blk:
            sys.exit(f"错误：[gr{i}_drive] 不是预期的 AllenCahn/f_drive 块")
        newblk = blk + (
            f"{m.group(1)}# 【溶质拖曳】f_loc 对 η_i 的导数 —— 补上 δF/δη 里缺的溶质项，\n"
            f"{m.group(1)}# 让模型变分自洽。量级比势垒小 9~11 个数量级（见脚本头注释）。\n"
            f"{m.group(1)}[gr{i}_solute]\n"
            f"{m.group(1)}  type = AllenCahn\n"
            f"{m.group(1)}  variable = gr{i}\n"
            f"{m.group(1)}  f_name = f_loc\n"
            f"{m.group(1)}  mob_name = L\n"
            f"{m.group(1)}  coupled_variables = 'c {others}'\n"
            f"{m.group(1)}[]\n"
        )
        out = out[:m.start()] + newblk + out[m.end():]
        added.append(i)

    assert len(added) == N, f"只插入了 {len(added)} 块（应为 {N}）"

    print("将做以下改动：")
    print(f"  1. 新增 {N} 个 `AllenCahn(f_loc)` 核（每个序参量一个）—— 溶质拖曳项")
    print(f"  2. 每个的 `coupled_variables = 'c <other 7>'`（c 因 f_loc；其余 7 个因 L 各向异性）")
    print()

    diff = list(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile=a.src, tofile=a.out))
    nchg = len([d for d in diff if d.startswith("+") or d.startswith("-")]) - 2
    print(f"diff：{nchg} 行变化")

    if a.dry_run:
        sys.stdout.writelines(diff[:60])
        print("\n(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(out)
    open(a.out + ".diff", "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {a.out}.diff")
    print("\n自检：")
    n_ac = out.count("type = AllenCahn")
    print("  AllenCahn 总数        :", n_ac, f"（应为 {2*N} = {N} drive + {N} solute）")
    # ⚠ `f_name = f_loc` 会数到 **N+1** 个 —— 除了新增的 N 个 AllenCahn，
    #   `SplitCHParsed` 也用它（那是 c 方程的核，本来就在）。别把期望值写成 N。
    n_floc = out.count("f_name = f_loc")
    print("  `f_name = f_loc` 出现  :", n_floc,
          f"（应为 {N+1} = {N} AllenCahn + 1 SplitCHParsed）")
    print("  仍指向 f_drive 的     :", out.count("f_name = f_drive"), f"（应为 {N}）")
    assert n_ac == 2 * N, f"AllenCahn 数不对：{n_ac} != {2*N}"
    assert n_floc == N + 1, f"f_name = f_loc 数不对：{n_floc} != {N+1}"


if __name__ == "__main__":
    main()
