#!/usr/bin/env python3
"""
自证：我手写的核序列化是否逐字等价于 GrainGrowthAction 建的核？

做法：拿 **C 版**（材料保持各向同性**不变**），只把它的 [Modules] 块换成我手写的
8x(TimeDerivative + ACGrGrPoly + ACInterface)，然后与**未改动的 C 版**对比：
  * 首步逐变量残差（iteration 0，最敏感）
  * 收敛步数、牛顿迭代数、线性迭代数

材料不变时，kappa/L 不依赖序参量，所以 coupled_variables 里多列 gr 是无害的
（导数为零）。若两边逐位一致 -> 核序列化忠实 -> 才可以拿它去改 D 版。

这一点必须做到，因为我在手写核上已经错过三次（缺 TimeDerivative、
v 含自己、缺 variable_L），不能再靠"看起来对"。
"""

import re
import sys

N_OP = 8


def top_block(text, header):
    key = f"\n[{header}]\n"
    i = text.index(key)
    start = i + len(key)
    end = text.index("\n[]\n", start) + 1
    return start, end


def main():
    src = open("stage1_meltpool_c.i", encoding="utf-8").read()

    etas = [f"gr{i}" for i in range(N_OP)]
    ker = []
    for e in etas:
        others = " ".join(x for x in etas if x != e)
        ker.append(f"""  [{e}_dt]
    type = TimeDerivative
    variable = {e}
  []
  [{e}_poly]
    type = ACGrGrPoly
    variable = {e}
    v = '{others}'
    mob_name = L
  []
  [{e}_int]
    type = ACInterface
    variable = {e}
    mob_name = L
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'T {others}'
  []
""")

    # 校验 C 版确实用的是 GrainGrowth 动作（否则这个测试没意义）
    if "\n[Modules]\n" not in src:
        sys.exit("C 版里没有 [Modules] 块 —— 前提不成立，测试无意义")
    if "GrainGrowth" not in src:
        sys.exit("C 版的 [Modules] 里没有 GrainGrowth —— 前提不成立")
    if "\n  [consts]\n" not in src:
        sys.exit("C 版里没有 [Materials]/consts —— 前提不成立")

    # 删掉整个 [Modules] 块
    mstart = src.index("\n[Modules]\n")
    mend = src.index("\n[]\n", mstart + len("\n[Modules]\n")) + len("\n[]\n")
    out = src[:mstart] + src[mend:]

    # 插入手写核
    _, kend = top_block(out, "Kernels")
    out = out[:kend] + "".join(ker) + out[kend:]

    # 统一诊断设置：end_time=1e-6 + 逐变量残差 + 唯一 file_base
    out = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", out, flags=re.M)
    out = out.replace("file_base = stage1c", "file_base = CK")
    assert "[Debug]" not in out
    out = out.replace("\n[Executioner]\n",
                      "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
    open("CK.i", "w", encoding="utf-8").write(out)

    # 参照组：未改动的 C 版，同样设置
    ref = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", src, flags=re.M)
    ref = ref.replace("file_base = stage1c", "file_base = CR")
    ref = ref.replace("\n[Executioner]\n",
                      "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
    open("CR.i", "w", encoding="utf-8").write(ref)

    n_dt = out.count("type = TimeDerivative")
    n_poly = out.count("type = ACGrGrPoly")
    n_int = out.count("type = ACInterface")
    print(f"CK.i: TimeDerivative x{n_dt}, ACGrGrPoly x{n_poly}, ACInterface x{n_int}")
    assert (n_dt, n_poly, n_int) == (N_OP, N_OP, N_OP), "核数量不对"
    # 确认 v 不含自己
    for e in etas:
        m = re.search(rf"\[{e}_poly\]\n(.*?)\n  \[\]\n", out, re.S)
        v = re.search(r"v = '([^']*)'", m.group(1)).group(1).split()
        assert e not in v, f"{e}_poly 的 v 含自己！"
        assert len(v) == N_OP - 1, f"{e}_poly 的 v 长度错"
    print("v 已确认排除自己，且 variable_L = true")
    print("CR.i: 未改动的 C 版（参照）")


if __name__ == "__main__":
    main()
