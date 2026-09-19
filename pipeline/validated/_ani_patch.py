#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
`run_ani_sweep.sh` 的辅助：给生成好的 `_d` 打两件事。

① **确认 A_ani 真的进了 `L` 的表达式**（jacchain 之后 `L2a` 已内联进 `L`，
   所以 `1+{A}*(2*` 这个串应当出现在 `[L_aniso]` 的 `expression` 里）。
   ⚠ 块名必须**行首锚定** + `re.M` —— 本仓库的坑：块名在注释里也出现过。
     第一版没锚定，`re.search` 匹配到了 `[Functions]` 里的 `laser_T`，
   断言当场抓到（这正是不锚定的代价）。

② 注入 `[align_melt]` = `ElementAverageValue(grad_align, block=1)` ——
   只统计**初始熔池区域**的对齐度，避免被未熔化的基体（~92% 的体积）稀释。
"""
import re
import sys


def main():
    A = sys.argv[1]
    p = "stage1_meltpool_d.i"
    t = open(p, encoding="utf-8").read()

    # ① 行首锚定取 [L_aniso] 块
    mb = re.search(r"^[ \t]*\[L_aniso\][ \t]*\n(?P<b>(?:.*?\n)*?)^[ \t]*\[\][ \t]*$",
                   t, re.M)
    assert mb, "找不到 [L_aniso] 块"
    m = re.search(r"expression\s*=\s*'([^']*)'", mb.group("b"), re.S)
    assert m, "[L_aniso] 里没有 expression = '...'"
    e = m.group(1)
    assert f"1+{A}*(2*" in e, f"A={A} 没进 L 的表达式（实际开头：{e[:70]}…）"
    print(f"    ✅ [L_aniso] 的表达式里确认 A = {A}")

    # ② 注入熔池区域的对齐度
    if "[align_melt]" in t:
        print("    （[align_melt] 已存在，跳过）")
    else:
        pp = ("  [align_melt]\n"
              "    type = ElementAverageValue\n"
              "    variable = grad_align\n"
              "    block = 1\n"
              "    execute_on = 'initial timestep_end'\n"
              "  []\n")
        m2 = re.search(r"^\[Postprocessors\][ \t]*\n", t, re.M)
        assert m2, "找不到 [Postprocessors]"
        t = t[:m2.end()] + pp + t[m2.end():]
        open(p, "w", encoding="utf-8", newline="").write(t)
        print("    ✅ 已注入 [align_melt]（block 1 = 初始熔池区域）")


if __name__ == "__main__":
    main()
