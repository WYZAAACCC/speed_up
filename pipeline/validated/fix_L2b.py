#!/usr/bin/env python3
"""
T1 根因的**修法**（在 D 输入上直接验证，不动生成器）：

## 根因（已实测确认）

`L2b` 的表达式 `1+0.7*(2*align4-1)` 靠 `material_property_names = 'align4'` 引用
`align4`。MOOSE 的 `DerivativeParsedMaterial` 在这条链上**没有生成 η 导数** ——
在真实生产输入上直接请求 `dL2b/dgr0` 会报 "is not defined"。
于是 `∂L/∂η_j` 静默丢掉整个 2b 项（`L2a` 那一半还在，所以不报错）。

## 修法

让 η 依赖**变成显式的**：
1. 把 `align4` 里的 8 个方向因子 `c_i = (a_i·gdir_p + b_i·gdir_q)^2` 各自做成
   一个独立的 `ParsedMaterial`（**纯数据** —— 只依赖 gdir，不依赖 η，不需要导数）。
2. `align4` 改写成 `(gr0^2*c0 + … + gr7^2*c7) / (gr0^2+…+gr7^2 + DELTA)`
   —— η 依赖现在**全在表达式里**，不再经过链式法则。
3. `L2b` **内联**第 2 步的表达式。因为 `c_i` 是数据，符号求导树只剩 η 的二次型，
   规模可控（直接内联原式会**求导树爆炸**，实测卡死在 setup）。

## 验收

* `dL2b/dgr0` 必须**存在**（原先不存在）
* FD 比值 `||J-Jfd||/||J||` 应从 `2.08e-2` 掉到 `1e-5` 以下

## 用法

    python3 fix_L2b.py --src <D 输入> --out <修好的 D 输入>
"""

import argparse
import re
import sys

# align4 里的 8 个方向因子 (a_i, b_i)，从生产输入的表达式原文抄出（顺序 = gr0..gr7）
AB = [(1.0, 0.0), (0.8686315144, 0.4954586684), (0.5090414158, 0.860742027),
      (0.3534748438, 0.9354440308), (-0.156434465, 0.9876883406),
      (-0.6252426563, 0.7804304073), (-0.7501110696, 0.6613118653),
      (-0.9792228106, 0.2027872954)]
N_OP = 8
DELTA = "0.001"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    s = open(a.src, encoding="utf-8").read()

    # --- 1. 抽出 align4 的表达式，校验方向因子与 AB 一致 ---
    m = re.search(r"\[align4_prop\](.*?)\n  \[\]", s, re.S)
    if not m:
        sys.exit("错误：找不到 [align4_prop]")
    al = re.search(r"expression = '(.*?)'\s*\n", m.group(1), re.S)
    if not al:
        sys.exit("错误：align4_prop 里找不到 expression")
    expr = al.group(1)

    # ⚠ 不要拿写死的字符串去匹配：生成器写的是 `1*gdir_p+0*gdir_q`（没有 `.0`），
    #   第一版按 `1.0*gdir_p` 匹配，直接报"生成器可能变了"。改成**从原文解析**。
    pat = re.compile(
        r"gr(\d)\^2\*\((-?[\d.eE+-]+)\*gdir_p\+(-?[\d.eE+-]+)\*gdir_q\)\^2")
    found = {int(i): (float(x), float(y)) for i, x, y in pat.findall(expr)}
    if len(found) != N_OP:
        sys.exit(f"错误：align4 表达式里只解析出 {len(found)} 个方向因子（期望 {N_OP}）")
    for i, (x, y) in enumerate(AB):
        if i not in found:
            sys.exit(f"错误：缺 gr{i} 的方向因子")
        if abs(found[i][0] - x) > 1e-9 or abs(found[i][1] - y) > 1e-9:
            sys.exit(f"错误：gr{i} 的系数原文是 {found[i]}，脚本里写的是 ({x}, {y})  —— 请核对 AB 表")

    # --- 2. 生成 8 个 c_i 材料（纯数据）+ 改写 align4 ---
    # ⚠ `gdir_p`/`gdir_q` 是**材料属性**（来自 ParsedMaterial），不是 MOOSE 变量：
    #   必须走 `material_property_names`，写成 `coupled_variables` 会报
    #   "Coupled variable 'gdir_p' was not found"（实测踩过）。
    c_mats = "\n".join(
        f"  [cm{i}]\n    type = ParsedMaterial\n    property_name = c{i}\n"
        f"    material_property_names = 'gdir_p gdir_q'\n"
        f"    expression = '({AB[i][0]}*gdir_p+{AB[i][1]}*gdir_q)^2'\n  []"
        for i in range(N_OP))
    num = " + ".join(f"gr{i}^2*c{i}" for i in range(N_OP))
    den = " + ".join(f"gr{i}^2" for i in range(N_OP))
    eta_vars = " ".join(f"gr{i}" for i in range(N_OP))
    c_names = " ".join(f"c{i}" for i in range(N_OP))

    new_align4 = (f"  [align4_prop]\n"
                  f"    type = DerivativeParsedMaterial\n"
                  f"    property_name = align4\n"
                  f"    coupled_variables = '{eta_vars}'\n"
                  f"    material_property_names = '{c_names}'\n"
                  f"    expression = '({num})/(({den})+{DELTA})'\n"
                  f"    derivative_order = 2\n"
                  f"  []")

    # --- 3. 内联进 L2b（去掉 material_property_names = 'align4'，换成 c_i 数据）---
    m2 = re.search(r"\[L2b\](.*?)\n  \[\]", s, re.S)
    if not m2:
        sys.exit("错误：找不到 [L2b]")
    blk = m2.group(0)
    if "material_property_names = 'align4'" not in blk:
        sys.exit("错误：L2b 的 material_property_names 不是 'align4'")
    new_l2b = (f"  [L2b]\n"
               f"    type = DerivativeParsedMaterial\n"
               f"    property_name = L2b\n"
               f"    coupled_variables = '{eta_vars}'\n"
               f"    material_property_names = '{c_names}'\n"
               f"    expression = '1+0.7*(2*(({num})/(({den})+{DELTA}))-1)'\n"
               f"    derivative_order = 2\n"
               f"  []")

    out = s.replace(m.group(0), c_mats + "\n" + new_align4)
    out = out.replace(blk, new_l2b)
    if out == s:
        sys.exit("错误：什么都没改动")

    open(a.out, "w", encoding="utf-8").write(out)
    print(f"写出 {a.out}")
    print("  1) 新增 8 个纯数据材料 c0..c7（方向因子）")
    print("  2) align4 改写为显式 η 表达式（不再靠链式法则拿 η 导数）")
    print("  3) L2b 内联同一表达式（求导树只剩 η 的二次型，不会爆炸）")
    print()
    print("验收：dL2b/dgr0 应存在；FD 比值应从 2.08e-2 掉到 1e-5 以下。")


if __name__ == "__main__":
    main()
