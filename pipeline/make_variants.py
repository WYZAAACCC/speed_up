#!/usr/bin/env python3
"""
生成 D 版的对照变体，用于定位"残差停在非零地板"是哪个改动引入的。

四个变体（每次只关掉一个 2a/2b 环节）：
  v0  原样（对照，已知会卡）
  v1  关掉 2b       —— L2b 因子恒为 1
  v2  关掉 L 的取向依赖 —— L 换成各向同性 Arrhenius（不走 material_property_names 链）
  v3  关掉 kappa/gamma 的取向依赖 —— 两者换成常数

另外全部打开 print_linear_residuals，否则看不到线性求解是否解到位
（上一步排查就卡在这里：日志里一条 Linear solve 都没有）。

用法： python3 make_variants.py
"""

import re
import sys

SRC = "stage1_meltpool_d.i"
END_TIME = "2e-6"          # 只跑 2 步，够看出第 1 步收不收敛


def block_span(text, name):
    m = re.search(rf"\n  \[{name}\]\n(.*?)\n  \[\]\n", text, re.S)
    if not m:
        sys.exit(f"找不到 [Materials] 子块 {name}")
    return m


def set_expr(text, name, expr_line):
    """只替换块内的 expression 行（表达式都是单行，内部无单引号）。"""
    m = block_span(text, name)
    body = m.group(1)
    body2 = re.sub(r"\n? *expression = '[^']*'", "\n    " + expr_line, body, count=1)
    if body2 == body:
        sys.exit(f"{name} 里没找到 expression 行")
    return text[:m.start(1)] + body2 + text[m.end(1):]


def get_expr(text, name):
    """取出块内 expression = '...' 里的表达式本体。"""
    m = block_span(text, name)
    em = re.search(r"expression = '([^']*)'", m.group(1))
    if not em:
        sys.exit(f"{name} 里没找到 expression")
    return em.group(1)


def set_body_tail(text, name, old, new):
    """把块体里的一段原文换掉（用于删掉 material_property_names 行）。"""
    m = block_span(text, name)
    body = m.group(1)
    if old not in body:
        sys.exit(f"{name} 里没找到要替换的内容: {old!r}")
    return text[:m.start(1)] + body.replace(old, new) + text[m.end(1):]


def common(text, tag):
    out = text.replace("  end_time = 6.5e-4", f"  end_time = {END_TIME}")
    out = out.replace("print_linear_residuals = false", "print_linear_residuals = true")
    out = out.replace("file_base = stage1d", f"file_base = {tag}")
    assert f"end_time = {END_TIME}" in out, "end_time 没替换成功"
    assert f"file_base = {tag}" in out, "file_base 没替换成功"
    return out


def main():
    src = open(SRC, encoding="utf-8").read()

    # v0 对照
    open("v0.i", "w", encoding="utf-8").write(common(src, "v0"))

    # v1 关掉 2b：L2b 恒为 1
    v1 = set_expr(src, "L2b", "expression = '1+0*(2*align4-1)'")
    open("v1.i", "w", encoding="utf-8").write(common(v1, "v1"))

    # v2 关掉 L 的取向依赖：换成各向同性 Arrhenius，且不再链式引用 L2a/L2b
    # （必须补 coupled_variables='T'，否则表达式里的 T 未定义）
    v2 = set_body_tail(src, "L_aniso", "    material_property_names = 'L2a L2b'\n",
                       "    coupled_variables = 'T'\n")
    v2 = set_expr(v2, "L_aniso",
                  "expression = '(4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-6'")
    open("v2.i", "w", encoding="utf-8").write(common(v2, "v2"))

    # v3 关掉 kappa/gamma 的取向依赖
    v3 = set_expr(src, "kappa_aniso", "expression = '1.8e-6'")
    v3 = set_expr(v3, "gamma_aniso", "expression = '1.5'")
    open("v3.i", "w", encoding="utf-8").write(common(v3, "v3"))

    # v4 【关键对照】把 align4 内联进 L，做成**单个材料、零链式**。
    #   若 v4 收敛 -> 问题在 material_property_names 的二阶链式求导
    #   若 v4 仍卡  -> 问题在"把 AuxVariable 耦合进二阶 DerivativeParsedMaterial"
    l2a = get_expr(src, "L2a")          # 2a 的迁移率基
    al4 = get_expr(src, "align4_prop")  # 对齐因子
    etas = " ".join(f"gr{i}" for i in range(8))
    v4 = set_body_tail(src, "L_aniso", "    material_property_names = 'L2a L2b'\n",
                       f"    coupled_variables = 'T {etas} grad_Tx grad_Ty'\n")
    v4 = set_expr(v4, "L_aniso",
                  f"expression = '({l2a})*(1+0.7*(2*({al4})-1))'")
    open("v4.i", "w", encoding="utf-8").write(common(v4, "v4"))

    print("已生成 v0.i(对照) v1.i(无2b) v2.i(L各向同性) "
          "v3.i(kappa/gamma常数) v4.i(align4内联进L,零链式)")


if __name__ == "__main__":
    main()
