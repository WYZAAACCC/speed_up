#!/usr/bin/env python3
"""
把 D 版输入里的 `ACGrGrPoly` 换成 `ACGrGrPolyJ`（自建核，雅可比补全版）。

## 它改什么

对 8 个序参量，每个 `[grN_poly]` 块做两处改动：

    type = ACGrGrPoly                       →  type = ACGrGrPolyJ
    v = 'gr1 gr2 ... gr7'                   →  v = 'gr1 gr2 ... gr7'
                                               coupled_variables = 'T gr1 ... gr7'

**残差不改**（`ACGrGrPolyJ` 的 residual 逐位等于 `ACGrGrPoly`），
只补三处被静默丢掉的雅可比项，理由见 `pipeline/app/include/kernels/ACGrGrPolyJ.h`。

`coupled_variables` 里**必须含 T**：`L` 依赖 T，`validateNonlinearCoupling("mob_name")`
会检查；而 γ 的导数不走这条路（按 `v` 单独取），所以 `gamma_asymm` 不依赖 T 也没问题。
**不含自己**：dL/dη_self 由 ACBulk 的 `_dLdop` 对角项负责，重复列会多算。

## 为什么不在 frozen/splice_aniso_nonad.py 里改

`frozen/` 有 `SHA256SUMS` 冻结登记。验证阶段先出**分支输入**；验证通过、
用户拍板之后再更新冻结表（规矩见 validated/README.md §规矩 1）。

## 用法

    python3 make_jacfix.py --src in.i --out out.i
    python3 make_jacfix.py --src in.i            # 只检查，不写文件
"""

import argparse
import difflib
import re
import sys

N_OP = 8


def make_jacfix(src_text):
    """返回 (新文本, 改动说明列表)。不改动则抛 SystemExit。"""
    lines = src_text.splitlines(keepends=True)
    out = []
    changes = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "type = ACGrGrPoly":
            # 该块的变量名在下面几行的 `variable = grN`
            indent = ln[: len(ln) - len(ln.lstrip())]
            var = None
            vline_idx = None
            j = i + 1
            while j < len(lines) and lines[j].strip() != "[]":
                s = lines[j].strip()
                if s.startswith("variable = "):
                    var = s.split("=", 1)[1].strip()
                if s.startswith("v = "):
                    vline_idx = j
                j += 1
            if var is None or vline_idx is None:
                sys.exit(f"错误：第 {i+1} 行的 ACGrGrPoly 块里找不到 variable/v，拒绝继续")
            if not re.fullmatch(r"gr\d+", var):
                sys.exit(f"错误：第 {i+1} 行的 variable={var!r} 不是 grN，拒绝继续")

            others = re.findall(r"gr\d+", lines[vline_idx])
            if var in others:
                sys.exit(f"错误：{var} 的 v 列表里含自己（{others}），与 GrainGrowth 语义不符")
            if len(others) != N_OP - 1:
                sys.exit(f"错误：{var} 的 v 列表有 {len(others)} 项，期望 {N_OP-1}")

            # 替换 type 行
            out.append(f"{indent}type = ACGrGrPolyJ\n")
            changes.append(var)
            # 复制中间各行
            for k in range(i + 1, vline_idx + 1):
                out.append(lines[k])
            # 在 v 行之后插入 coupled_variables
            out.append(f"{indent}coupled_variables = 'T {' '.join(others)}'\n")
            i = vline_idx + 1
            continue
        out.append(ln)
        i += 1

    if len(changes) != N_OP:
        sys.exit(f"错误：只改了 {len(changes)} 个 poly 块（期望 {N_OP}）：{changes}")
    return "".join(out), changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", help="不给则只检查，不写文件")
    ap.add_argument("--diff", action="store_true", help="写 <out>.diff")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    dst, changes = make_jacfix(src)
    print(f"改了 {len(changes)} 个 poly 块：{' '.join(changes)}")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(dst)
        print(f"写入 {a.out}")
        if a.diff:
            with open(a.out + ".diff", "w", encoding="utf-8") as f:
                f.writelines(
                    difflib.unified_diff(
                        src.splitlines(keepends=True),
                        dst.splitlines(keepends=True),
                        fromfile=a.src, tofile=a.out))
            print(f"写入 {a.out}.diff")
        # 复核：新文件里 ACGrGrPolyJ 出现次数必须是 8，且没有残留裸 ACGrGrPoly
        n_new = len(re.findall(r"type = ACGrGrPolyJ", dst))
        n_old = len(re.findall(r"type = ACGrGrPoly\b(?!J)", dst))
        print(f"复核：ACGrGrPolyJ = {n_new}，残留 ACGrGrPoly = {n_old}")
        if n_new != N_OP or n_old != 0:
            sys.exit("错误：复核不通过")


if __name__ == "__main__":
    main()
