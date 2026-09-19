#!/usr/bin/env python3
"""
解析 `-snes_test_jacobian_view` 的输出，把差异按「属于哪个变量」分块统计。

## 为什么需要它

`-snes_test_jacobian` 只给一个标量比值（`||J-Jfd||_F/||J||_F`），
**不告诉你差异落在哪个方程上**。加 `-snes_test_jacobian_view` 会逐行打出
`(列, 差值)` 对，但那是近万行的原始 dump，人读不了。

本脚本把它归类成「行变量 × 列变量」的块统计 —— 一眼就能看出
缺项是**集中在某个核覆盖的变量上**（⇒ 某个核缺项），
还是**所有变量都错**（⇒ 全局性问题，不是某个核）。

## DOF 布局

MOOSE 按变量分组编号：`DOF // 每变量自由度数` = 变量序号。
本项目 10 个变量（`gr0…gr7`, `c`, `w`），24×12 QUAD4 ⇒ 25×13 = 325 节点，
所以每变量 325 个自由度。

⚠ **这个布局假设必须核对**：变量个数、节点数、是否有序参量以外的变量
（比如 `T` 是 AuxVariable，**不在**解向量里）。用 `--np` 覆盖。

## 用法

    # 1) 先跑出 view 日志
    gb_jac-opt -i N.i -pc_type lu -pc_factor_mat_solver_type mumps \\
        -snes_test_jacobian 1e-3 -snes_test_jacobian_view > view.log 2>&1
    # 2) 再分析
    python3 analyze_jac_view.py view.log --np 325 --nvar 10
"""

import argparse
import collections
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--np", type=int, required=True,
                    help="每个变量的自由度数（= 节点数，对 LAGRANGE 一阶变量）")
    ap.add_argument("--nvar", type=int, default=10)
    ap.add_argument("--names", default="gr0,gr1,gr2,gr3,gr4,gr5,gr6,gr7,c,w")
    a = ap.parse_args()

    names = a.names.split(",")
    if len(names) != a.nvar:
        sys.exit(f"错误：--names 给了 {len(names)} 个，--nvar 说 {a.nvar}")

    def var(d):
        v = d // a.np
        return names[v] if 0 <= v < a.nvar else f"?{v}"

    rows = {}
    for ln in open(a.log, encoding="utf-8", errors="replace"):
        m = re.match(r"row (\d+): (.*)", ln)
        if not m:
            continue
        r = int(m.group(1))
        rows[r] = [(int(c), float(v))
                   for c, v in re.findall(r"\((\d+), ([0-9.eE+-]+)\)", m.group(2))]

    if not rows:
        sys.exit("没解析到任何 `row N:` 行 —— 日志确定是 -snes_test_jacobian_view 产的吗？")

    blk = collections.Counter()
    diag = off = 0
    mx = (0.0, None)
    rvars = set()
    for r, ent in rows.items():
        rvars.add(var(r))
        for c, v in ent:
            blk[(var(r), var(c))] += 1
            if r == c:
                diag += 1
                if abs(v) > abs(mx[0]):
                    mx = (v, (r, c))
            else:
                off += 1

    print(f"有差异的行数        : {len(rows)}")
    print(f"差异涉及的行变量    : {sorted(rvars)}")
    print(f"对角元差异 / 非对角 : {diag} / {off}")
    print(f"最大的单条差异      : {mx[0]:.6g} at (row,col)={mx[1]}"
          f"  -> {var(mx[1][0])} x {var(mx[1][1])}" if mx[1] else "")
    print()
    print("按 (行变量, 列变量) 分块统计 —— 前 20：")
    for (x, y), n in blk.most_common(20):
        print(f"   {x:>4} x {y:<4} : {n}")
    print()
    print("怎么读：")
    print("  * 差异只落在**某几个变量**上      -> 那几类核里有缺项（可定位到核）")
    print("  * 差异落在**全部变量**上          -> 全局性问题，继续查材料链/测试本身")
    print("  * 最大差异在**对角元**上          -> 该方程对『自己』的导数不对")


if __name__ == "__main__":
    main()
