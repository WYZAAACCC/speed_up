#!/usr/bin/env python3
"""
从生产源输入生成**验证分支**输入（不改生产文件）。

审计要求（`01_IMPLEMENTATION_PLAN.md`）：
  * 物理修复不要直接改生产文件，复制到 `pipeline/validated/` 或用参数化输入
  * 每次只改一个物理/数值因素
  * 保存输入 diff

本脚本就是那个「参数化输入」。它做的每处替换都要求**恰好命中一次**，
命中不了就报错退出（避免静默改错）。输出的 `.diff` 与源输入逐行可核对。

用法
----
    # 温度截断
    python3 make_variant.py --src ../../stage1_meltpool_c.i --out cap3200.i --t-cap 3200
    python3 make_variant.py ... --t-cap off          # 关闭（等价不截断）

    # 溶质迁移率分层
    python3 make_variant.py ... --d-layer 2.52e-9 4.0e-13 4.0e-10

    # 两个一起（**审计明确禁止**——一次只改一个因素；这里保留能力只为做
    # 组合确认，正常流程不要用）
    python3 make_variant.py ... --t-cap 3200 --d-layer 2.52e-9 4.0e-13 4.0e-10
"""

import argparse
import difflib
import re
import sys

# Windows 控制台默认 GBK，打印 ⚠ 之类的符号会 UnicodeEncodeError 直接崩。
# 强制 UTF-8 输出，编码不了的字符退化成占位符而不是异常。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


# ---------------------------------------------------------------------------
# 补丁 1：温度截断 T_cap
# ---------------------------------------------------------------------------
def patch_t_cap(src: str, cap: float | None) -> tuple[str, str]:
    """
    把 laser_T 包成 min(原式, T_cap)。

    为什么要截断：Rosenthal 点源解在源点附近发散，生产输入的实际 T_max
    = 15107 K（实测扫描），而 Ti64 沸点约 3315 K。这个温度经 Arrhenius
    进入晶界迁移率 L = 4/3·M0·exp(-Q/kbT)/wGB，在熔池核心把 L 抬高了 4 个数量级。

    ---- 为什么用「截断」而不是「有限源半径」----
    thermal_field.py:55-58 记录过：把 rb^2 加进 R 会**同时**改掉 1/R 几何因子
    与 exp 衰减项，在 v·rb/(2α) ~ 4 时把温度压低两个数量级，**熔池直接消失**。
    ⇒ 源半径那条路已证伪，只能截断。

    ---- 安全性质（必须实测确认）----
    只要 T_cap > 液相线 1928 K，熔池几何**完全不变**：
    liquid_flag 的判据是 T > 1903，而 cap 远在其上。
    所以这条改动不碰凝固形貌，只压低熔池核心的虚假高温。
    """
    # 找到 [laser_T] 块里的 expression 行
    pat = re.compile(r"(\[laser_T\][^\[]*?expression\s*=\s*')(.*?)('\s*\n)", re.S)
    m = pat.search(src)
    if not m:
        sys.exit("错误：找不到 [laser_T] 的 expression 行")

    expr = m.group(2)
    if "min(" in expr:
        sys.exit("错误：[laser_T] 的表达式里已经有 min( —— 源文件可能已打过补丁")

    # cap = off 时用 1e30，等于不截断（已实测 min(x,1e30) == x）
    cap_str = "1e30" if cap is None else f"{cap:g}"
    new_expr = f"min({expr}, {cap_str})"

    src2 = src[: m.start(2)] + new_expr + src[m.end(2):]
    desc = (f"[laser_T] 表达外包 min(..., {cap_str})\n"
            f"    T_cap = {'关闭（1e30，等价不截断）' if cap is None else f'{cap:g} K'}")
    return src2, desc


# ---------------------------------------------------------------------------
# 补丁 2：溶质迁移率分层 D_L / D_S / D_GB
# ---------------------------------------------------------------------------
CH_PARAMS_OLD = """  [ch_params]
    type = GenericConstantMaterial
    prop_names  = 'M        kappa_c'
    prop_values = '2.8e-9   1e-14'
  []"""

CH_PARAMS_NEW = """  # =====================================================================
  # 【Phase 1.3】溶质迁移率分层：D_L / D_S / D_GB（审计 P0-3 + P0-4）
  # =====================================================================
  # 改前：M = 2.8e-9 常数，于是 D = M·f_cc，而 f_cc = k_c + 2·A_part·Ση²：
  #     液相 (Ση²=0)      D = 2.52e-9
  #     固相 (Ση²=1)      D = 4.00e-9   <- **比液相还快 1.59 倍（物理上反了）**
  #     固固晶界(Ση²=0.5)  D = 3.26e-9   <- 没有独立的晶界快速通道
  # 真实 Ti64 中 V 的 D_L 比 D_S 高约 4 个数量级，D_GB 又比 D_S 高若干个数量级。
  #
  # ---- 指示函数的选取（这里踩过一个坑，必须记下来）----
  # 第一版草稿用的是 h_gb = 4·S·(1−S)（S = Ση_i²）。
  # 它有个致命缺陷：**固液界面中点也满足 S ≈ 0.5**，于是固液界面会被
  # 误判成晶界，拿到 D_GB 的快速扩散 —— 而 LPBF 里恰恰是固液界面最重要。
  # 用 check_D_layering.py 与代码核对时发现了（晶界态算出 1.66e-9 而不是 4e-10）。
  #
  # 正确的晶界指示必须能区分「**两个不同晶粒**相遇」与「固相遇到液相」：
  #     固液界面：只有 1 个 η 非零        -> 指示 = 0
  #     固固晶界：2 个 η 同时非零          -> 指示 = 1
  # 用配对乘积即可：
  #     h_gb = 16 · Σ_{i<j} η_i² η_j² = 8·(S² − Q),   Q = Σ η_i⁴
  #   二元晶界 (η₀=η₁=0.5)：S=0.5, Q=0.125 -> 8·(0.25−0.125) = 1  OK
  #   晶粒内部 (η₀=1)      ：S=1,   Q=1     -> 0                  OK
  #   液相                 ：S=0             -> 0                  OK
  #   固液界面             ：只有 1 个 η     -> 0                  OK  <- 关键
  #   三叉晶界 (各 1/3)     ：S=1/3, Q=1/27  -> 16/27 ≈ 0.593      OK
  #
  # 固相指示：晶界处 S 只有 0.5，直接用 S 会让液相项漏进来（D 偏大）。
  #     h_s = min(1, 2·S)
  #   晶界 -> min(1,1) = 1；晶粒内 -> 1；液相 -> 0；固液界面 -> 2S（线性混合）
  #
  #   ⚠ 第一版用的是 h_s = S + h_gb(1−S)。它在**晶界两翼**把液相项漏进了固相，
  #     而且这一点是**用 1D 晶界算例量出来的**（validated/make_1d_gb.py），
  #     不是推出来的：
  #         位置           S       h_gb    h_solid    D (m²/s)      D/D_S
  #         晶粒 x=0.2µm  0.9998   0.000    0.9998    1.02e-12       2.6×
  #         晶粒 x=0.6µm  0.9982   0.000    0.9982    4.99e-12      12×
  #         晶粒 x=1.4µm  0.9096   0.033    0.9126    2.34e-10     584×
  #         晶界两翼      0.6068   0.619    0.8501    6.26e-10   ← 比晶界中心还大！
  #         晶界中心      0.5000   1.000    1.0000    4.00e-10
  #     **D 的最大值跑到了晶界两侧**，物理上反了；固相里 D 比 D_S 大 2.6~584 倍。
  #     根因：D_L 与 D_S 相差 6300 倍时，(1−h_solid) 的尾巴被放大 6300 倍。
  #     ⇒ 固相指示**必须在晶界处正好等于 1**。
  #   min(1, 2S) 在 S=0.5（二元晶界中点）恰好饱和到 1，两翼也全是 1。
  #   修复后实测：固相 D = 4.009e-13（期望 D_S=4.0e-13，+0.24%），
  #               且 D 随远离晶界**单调下降**。
  #   ⚠ 代价：min() 在 S=0.5 处有一个导数拐点（正好落在二元晶界中心线上）；
  #     MOOSE 对 min() 取次梯度，实测牛顿正常收敛。
  #
  # 合成：
  #     D(η) = D_L + (D_S−D_L)·h_s + (D_GB−D_S)·h_gb
  #   三个极限分别精确给出 D_L / D_S / D_GB —— 可逐点核对（T6）。
  #
  # =====================================================================
  #     M    = D(η) / f_cc,     f_cc = k_c + 2·A_part·S
  # =====================================================================
  # **关键性质**：f_cc 就是 f_loc 对 c 的二阶导（f_loc 是 c 的二次多项式），
  # 所以由构造保证 D = M·∂²f/∂c² 逐点成立。
  #
  # ⚠⚠ 参数来源：Ti64 中 V 的 D_S、D_GB 定量数据**基本不存在**（本项目已知
  #    文献缺口）。以下数值一律是 **calibration 参数**，不是材料常数。
  #    **不得**在任何文档或论文里写成"已验证的 Ti64 数据"。
  #
  # ⚠ M 现在依赖 η ⇒ [Kernels]/[coupled_res] **必须**声明 gr0..gr7，
  #    否则 ∂M/∂η_i 整块不进入雅可比 —— 与 P0-1 完全同类。
  #     本脚本已同步打上那个补丁。
  # =====================================================================
  [ch_kappa]
    type = GenericConstantMaterial
    prop_names  = 'kappa_c'
    prop_values = '1e-14'
  []

  # --- S = Ση²（固相指示 + f_cc 的输入）---
  [solute_S]
    type = DerivativeParsedMaterial
    property_name = S_eta2
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = 'gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2'
    derivative_order = 2
  []

  # --- Q = Ση⁴（只为算 h_gb）---
  [solute_Q]
    type = DerivativeParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    expression = 'gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4'
    derivative_order = 2
  []

  # --- 晶界指示 h_gb = 8(S²−Q) = 16·Σ_{i<j}η_i²η_j²；二元晶界=1，其余=0 ---
  [solute_hgb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []

  # --- 固相指示 h_s = min(1, 2S)；晶界处饱和到 1 ---
  [solute_hs]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
    derivative_order = 2
  []

  # --- 分层扩散系数 -> 迁移率 M = D(η)/f_cc ---
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    material_property_names = 'S_eta2 h_gb h_solid'
    constant_names = 'D_L D_S D_GB k_c A_part'
    constant_expressions = '{DL} {DS} {DGB} 0.9 0.264'
    expression = '(D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb) / (k_c + 2*A_part*S_eta2)'
    derivative_order = 2
  []"""

COUPLED_RES_OLD = """  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
  []"""

COUPLED_RES_NEW = """  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    # 【必须】M 现在依赖 η ⇒ 不声明 gr0..gr7 的话，∂M/∂η_i 整块不进雅可比
    # （SplitCHWResBase.h:83 `_dmobdarg[cvar] = getMaterialPropertyDerivative(_mob_name, i)`，
    #  而 cvar 来自 mapJvarToCvar —— 只认声明过的耦合变量）。
    # 这是 P0-1 的同类缺陷，只是换了个核。
    coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
  []"""


def patch_d_layer(src: str, dl: float, ds: float, dgb: float) -> tuple[str, str]:
    if src.count(CH_PARAMS_OLD) != 1:
        sys.exit(f"错误：[ch_params] 块匹配到 {src.count(CH_PARAMS_OLD)} 次，期望 1 次。"
                 f"源文件可能已改过。")
    if src.count(COUPLED_RES_OLD) != 1:
        sys.exit(f"错误：[coupled_res] 块匹配到 {src.count(COUPLED_RES_OLD)} 次，期望 1 次。")

    # ⚠ 不能用 str.format()：注释里有 `Σ_{i<j}` 这种花括号，会被当成占位符
    #   （报 KeyError: 'i<j'）。用 replace 做大括号安全的替换。
    new_ch = (CH_PARAMS_NEW
              .replace("{DL}", f"{dl:g}")
              .replace("{DS}", f"{ds:g}")
              .replace("{DGB}", f"{dgb:g}"))
    src2 = src.replace(CH_PARAMS_OLD, new_ch)
    src2 = src2.replace(COUPLED_RES_OLD, COUPLED_RES_NEW)

    desc = (f"[ch_params] 常数 M 拆成 S_eta2 / h_gb / solute_mobility 三个材料\n"
            f"    D_L = {dl:g}   D_S = {ds:g}   D_GB = {dgb:g}   (m^2/s, **calibration**)\n"
            f"    [coupled_res] 增加 coupled_variables = gr0..gr7（同理 P0-1）\n"
            f"    改前等效：D_L=2.52e-9, D_S=4.00e-9, D_GB=3.26e-9")
    return src2, desc


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="源输入（生产 stage1_meltpool_c.i）")
    ap.add_argument("--out", required=True, help="输出分支输入")
    ap.add_argument("--t-cap", default=None,
                    help="温度上限 K，或 off（= 1e30，等价不截断）")
    ap.add_argument("--d-layer", nargs=3, type=float, metavar=("D_L", "D_S", "D_GB"),
                    help="分层扩散系数 m^2/s")
    args = ap.parse_args()

    src = open(args.src, encoding="utf-8").read()
    orig = src
    notes = []

    if args.t_cap is not None:
        cap = None if args.t_cap.lower() == "off" else float(args.t_cap)
        src, d = patch_t_cap(src, cap)
        notes.append(d)

    if args.d_layer is not None:
        src, d = patch_d_layer(src, *args.d_layer)
        notes.append(d)

    if not notes:
        sys.exit("错误：没有指定任何补丁（--t-cap 或 --d-layer）")

    open(args.out, "w", encoding="utf-8").write(src)

    # --- 输入 diff：审计要求保存 ---
    diff = difflib.unified_diff(
        orig.splitlines(keepends=True), src.splitlines(keepends=True),
        fromfile=args.src, tofile=args.out, n=2)
    with open(args.out + ".diff", "w", encoding="utf-8") as f:
        f.writelines(diff)

    print(f"写出 {args.out}  ({len(src)} 字符)")
    print(f"     {args.out}.diff  （逐行可核对）")
    print("补丁：")
    for n in notes:
        print("  - " + n)
    print()
    print("⚠ 记住：一次只改一个因素。两个补丁同时用只用于组合确认，不要用来解释因果。")


if __name__ == "__main__":
    main()
