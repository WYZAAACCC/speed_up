#!/usr/bin/env python3
"""
把 gen_aniso.py 生成的 aniso_block.i 接进 stage1_meltpool_c.i，
产出 stage1_meltpool_d.i。

为什么用脚本而不是手工改：算例文件 12 KB，手工插入容易破坏块结构；
脚本可复现、可复查，而且把"改了哪几处"固定下来。

做的五件事：
  1. [AuxVariables] 追加 orient_cos / orient_sin / grad_align
  2. [AuxKernels]   追加对应的三个 ParsedAux
  3. [Materials]    删掉 [consts]（kappa_op/gamma_asymm 常数）与
                    [L_mobility]（各向同性 Arrhenius），换成 2a/2b 的三个材料
                    —— barrier_mu（熔化开关）**原样保留**，绝不改动
  4. [Postprocessors] 追加各向异性诊断量
  5. 文件名/头注释

用法： python3 splice_aniso.py
"""

import sys

SRC = "stage1_meltpool_c.i"
BLK = "aniso_block.i"
DST = "stage1_meltpool_d.i"


def top_block(text, header):
    """返回顶层块 [header] 内容区间 (起, 止)。顶层块以行首 '[]' 结束。"""
    key = f"\n[{header}]\n"
    i = text.index(key)
    start = i + len(key)
    end = text.index("\n[]\n", start) + 1
    return start, end


def sub_block_span(text, name, indent="  "):
    """返回缩进子块 [name] 的完整区间（含首尾行）。"""
    key = f"\n{indent}[{name}]\n"
    i = text.index(key)
    j = text.index(f"\n{indent}[]\n", i) + len(f"\n{indent}[]\n")
    return i, j


def main():
    src = open(SRC, encoding="utf-8").read()
    blk = open(BLK, encoding="utf-8").read()

    # --- 从生成块里取出各 section 的内容 ---
    def sec(name):
        a, b = top_block(blk, name)
        return blk[a:b]

    funcs, auxv, auxk, mats = (sec("Functions"), sec("AuxVariables"),
                               sec("AuxKernels"), sec("Materials"))

    out = src

    # --- 1/2. 追加 Functions / AuxVariables / AuxKernels ---
    # 每次都在最新的 out 上重新定位块尾，所以插入顺序不影响正确性
    for header, content in (("Functions", funcs),
                            ("AuxKernels", auxk),
                            ("AuxVariables", auxv)):
        if f"\n[{header}]\n" not in out:
            sys.exit(f"错误：源文件里找不到顶层块 [{header}]，拒绝继续")
        _, end = top_block(out, header)
        out = out[:end] + content + out[end:]

    # --- 3. 删除 [consts] 与 [L_mobility]，插入 aniso 材料 ---
    # 先确认这两个块确实存在，避免静默什么都删不掉
    for name in ("consts", "L_mobility"):
        if f"\n  [{name}]\n" not in out:
            sys.exit(f"错误：源文件里找不到 [Materials]/{name}，拒绝继续")

    # 两个块都要删；按位置从后往前删，避免偏移
    spans = sorted((sub_block_span(out, n) for n in ("consts", "L_mobility")),
                   reverse=True)
    for a, b in spans:
        out = out[:a] + out[b:]

    # 插到 [Materials] 之后紧接着的位置
    ins = top_block(out, "Materials")[0]
    out = out[:ins] + mats.lstrip("\n") + out[ins:]

    # --- 3b.【关键修复】把序参量加进 ACInterface/ACGrGrPoly 的 args ---
    #
    # 算例原来是 `coupled_variables = 'T'`，因为 C 版的 L 只依赖 T。
    # 但 D 版里 kappa_op 和 L 都依赖 gr0..gr7，而 ACInterface 的雅可比
    # 只对 **args** 求材料属性的导数：
    #     _dLdarg[i]     = getMaterialPropertyDerivative("mob_name",  i)
    #     _dkappadarg[i] = getMaterialPropertyDerivative("kappa_name", i)
    # i 只遍历 args。于是"通过 L/κ 传递到其他序参量"的雅可比项**全部丢失**。
    #
    # MOOSE 自己一直在报警告（之前被漏看了）：
    #     Missing coupled variables {gr1..gr7}
    #     (add them to coupled_variables parameter of gr0_ACInterface)
    #
    # 后果完全对上观测：C 版正常（L 只依赖 T）；2a 单独只是慢（η 导数 ~1%）；
    # 2b 一开就卡死（align 因子 η 导数 O(1)）；挪到 mu 上也卡
    # （ACGrGrPoly 用 mu 时完全不取导数，所以同样进不了雅可比）；
    # 线性求解 DIVERGED_ITS；牛顿残差停在非零地板。
    n_op = 8
    etas = [f"gr{i}" for i in range(n_op)]
    ker = []
    for e in etas:
        others = " ".join(x for x in etas if x != e)
        # 【必须逐字复刻 GrainGrowthAction::act() 建的三个核，否则解的不是同一个方程】
        # 对照 GrainGrowthAction.C 第 118-175 行：
        #   1. TimeDerivative(variable)                      <- 漏了它 => 方程退化成稳态！
        #   2. ACGrGrPoly(variable, v=**除自己外**的序参量, mob_name)
        #        文档方程：mu*(eta_i^3-eta_i+2*gamma*eta_i*sum_{j!=i} eta_j^2)
        #        原来传的是**含自己**的全部 8 个 -> 晶粒内部多出 2*gamma*mu 的虚假驱动力
        #   3. ACInterface(variable, mob_name, kappa_name, variable_L)
        #        动作里 params.set<bool>("variable_L") = variable_mobility，
        #        而 C 版 [Modules] 写的 variable_mobility = true。
        #        漏了它 => 弱形式里少掉 gradL 项（nabla(L*psi) 的乘积法则那一半）
        #        => 又一个不同的 PDE。
        # 另外 coupled_variables 除 T 外还要列出**其他**序参量：L、kappa 都依赖它们，
        # ACInterface 的雅可比只对 coupled_variables 求材料属性的导数。
        # （动作做不到这件事：它把同一份列表发给所有核，而每个核不该含自己的变量。）
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
    # 删掉整个 [Modules] 块（含它的结束符 "[]"）。
    # 坑：top_block 返回的 end 只指向 "["，不含 "[]\n"，直接拿它当终点
    # 会把结束符留下 -> 文件里多出一个顶层 [] -> 语法错误。
    mstart = out.index("\n[Modules]\n")
    mbody = mstart + len("\n[Modules]\n")
    mend = out.index("\n[]\n", mbody) + len("\n[]\n")
    out = out[:mstart] + out[mend:]
    _, kend = top_block(out, "Kernels")
    out = out[:kend] + "".join(ker) + out[kend:]

    # --- 4. 追加诊断后处理 ---
    diag = """  # --- 2a/2b 诊断（smoke test 用，确认各向异性真的在起作用）---
  #   align4 = cos^2(2(phi-theta))：1 = 晶粒易生长轴与热梯度完全对齐
  #   若这个量的时间平均始终是常数，说明 2b 没生效
  [align_mean]
    type = ElementAverageValue
    variable = grad_align
    execute_on = 'initial timestep_end'
  []
  [align_max]
    type = ElementExtremeValue
    variable = grad_align
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [align_min]
    type = ElementExtremeValue
    variable = grad_align
    value_type = min
    execute_on = 'initial timestep_end'
  []
  # 局部取向场的两个分量 —— 与 extract.py 反解出的 theta 交叉校验
  [oc_mean]
    type = ElementAverageValue
    variable = orient_cos
    execute_on = 'initial timestep_end'
  []
  [os_mean]
    type = ElementAverageValue
    variable = orient_sin
    execute_on = 'initial timestep_end'
  []
"""
    _, end = top_block(out, "Postprocessors")
    out = out[:end] + diag + out[end:]

    # --- 5. 输出文件名与头注释 ---
    out = out.replace("file_base = stage1c", "file_base = stage1d")
    header = """# =============================================================================
# 阶段一 · D 版 = C 版（柱状基体 + 溶质，已验证） + 第二档（2a + 2b）
# =============================================================================
#
# D 版相对 C 版**只改晶界性质，不改任何其他物理**：
#
#   [consts]     kappa_op=1.8e-6, gamma_asymm=1.5   （常数）
#   [L_mobility] L = 4/3*M0*exp(-Q/kbT)/wGB         （各向同性 Arrhenius）
#       ↓ 被替换为
#   [kappa_aniso] [gamma_aniso] [L_aniso]           （2a + 2b，见 aniso_block.i）
#
#   barrier_mu（熔化开关）、溶质系统、温度场、网格、求解器  —— **全部未动**
#
# 【2a】取向差依赖的晶界能/迁移率
#   严格复刻 GBAnisotropy 的 Moelans Algorithm 1（不用该材料的原因见
#   gen_aniso.py 头注释：它会声明 `mu`，与熔化开关抢同名属性）。
#   各向同性极限下 kappa_op/gamma_asymm/L **都精确退化为 C 版的值**
#   （kappa 偏差 3.17e-05，来自教科书圆整值 0.75 vs 不动点精确解 0.74997626）。
#
# 【2b】热梯度驱动的晶粒选择
#   对齐因子 (1 + A*(2*align4 - 1))，align4 = cos^2(2(phi-theta)) 四重对称。
#   热梯度取实际温度场的**解析导数**，不是几何近似。
#
# 【本版新增输出】orient_cos / orient_sin / grad_align（逐单元定值）
#   extract.py 靠前两个逐晶粒反解出晶粒取向 theta；
#   grad_align 用于与 extract.py 独立算出的对齐度交叉校验。
#
# 【已知简化，非 bug】
#   * 无形核核 -> 无等轴晶形核（真实 LPBF 熔池顶部有）
#   * A_ani = 0.7 是唯象占位，需用 LPBF 实测织构标定
#   * Q 的取向差依赖未建模（缺少文献依据），仅 sigma 与 M 有取向差依赖
# =============================================================================

"""
    # 去掉原来的头注释块：从第一行真正的 MOOSE 块（行首 '['）开始保留
    lines = out.splitlines(keepends=True)
    body_start = next(k for k, ln in enumerate(lines) if ln.startswith("["))
    out = header + "".join(lines[body_start:])

    open(DST, "w", encoding="utf-8").write(out)
    print(f"写入 {DST}  ({len(out)} 字符)")
    print(f"  追加 Functions   : {len(funcs)} 字符")
    print(f"  追加 AuxVariables: {len(auxv)} 字符")
    print(f"  追加 AuxKernels  : {len(auxk)} 字符")
    print(f"  替换 Materials   : {len(mats)} 字符")


if __name__ == "__main__":
    main()
