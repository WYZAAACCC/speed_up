#!/usr/bin/env python3
"""
Phase 3 合入生产：把「独立晶界偏析项 + `h_solid` 驱动的分配项」打进生产输入。

背景与依据
----------
生产输入 `/root/work/prod_merged/N.i`（= `stage1_meltpool_c.i` 合入后的版本）里

    N.i:891  f_loc = k_c/2*(c-c0)^2 + A_part*c^2*(gr0^2+...+gr7^2)
    N.i:874  M     = (D_L + ...) / (k_c + 2*A_part*S_eta2)

也就是说 **Phase 3 的两个增量一个都没进生产**：
  * 没有独立的晶界偏析项（`Γ_GB ∝ w_GB` 的病灶没修）
  * 分配项仍由 `Ση²` 驱动（固固晶界上凭空造出分配驱动力，见 T11）

本脚本把这两项打进去。**默认不改生产文件**，输出到指定路径并附 `.diff`。

⚠ 三个必须一起改的地方（少一个就错）
------------------------------------
1. `f_loc` 的分配项：`A_part*c^2*S` -> `A_part*c^2*h_solid`
2. `f_loc` 追加偏析项：`+ (Omega0/wgb)*(c-c0)*h_gb`
3. **`M` 的分母（f_cc）必须同步**：`k_c + 2*A_part*S` -> `k_c + 2*A_part*h_solid`
   否则 `D = M·f_cc` 不再成立，T6 的判据会挂。
   （`Ω₀·c·h_gb` 对 c 的二阶导为零，所以**偏析项不进 f_cc** —— 这一点省事但要注意。）

⚠ `h_solid` / `h_gb` **显式内联**，不走 `material_property_names`
--------------------------------------------------------------
本项目实测过：`DerivativeParsedMaterial` 经 `material_property_names` 引用**另一个**
`DerivativeParsedMaterial` 时，MOOSE 的链式法则会静默给零（`L2b` 的 `dL2b/dgr0` 就是
这么丢的），而且 JIT 会从 ~12 s 爆到 20+ 分钟。
`h_solid`、`h_gb` 都是简单多项式，内联没有代价：

    S       = Σ η_i²
    Q       = Σ η_i⁴
    h_gb    = 8(S² − Q) = 16·Σ_{i<j} η_i²η_j²
    h_solid = min(1, 2S)

用法
----
    # 只看会改什么（不写文件）
    python3 make_phase3_prod.py --src N.i --out new.i --dry-run
    # 打进去
    python3 make_phase3_prod.py --src N.i --out new.i \
        --f-part h_solid --omega0 -5e-11 --wgb 4e-6
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


def build_expr(f_part: str, omega0: float | None) -> str:
    """拼出新的 f_loc 表达式（指示函数全部内联）。

    ⚠ 表达式里的 `Omega0` / `wgb` 是**写给 MOOSE 的字面量**（由 constant_names 定义），
    不是 Python 变量 —— 所以 `wgb` 不作为本函数的参数。
    """
    S = "(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)"
    drive = S if f_part == "S" else f"min(1, 2*{S})"
    e = f"k_c/2*(c-c0)^2\n                  + A_part*c^2*{drive}"
    if omega0 is not None:
        Q = "(gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4)"
        # h_gb = 8*(S^2 - Q)，内联
        e += f"\n                  + (Omega0/wgb)*(c-c0)*8*({S}^2 - {Q})"
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="源生产输入")
    ap.add_argument("--out", required=True, help="输出文件")
    ap.add_argument("--f-part", choices=("S", "h_solid"), default="h_solid",
                    help="分配项由什么驱动。`S`(Ση²)=生产现状；`h_solid`=T11 修好的那版")
    ap.add_argument("--omega0", type=float, default=None,
                    help="偏析项系数。给了才加偏析项。"
                         "⚠ 标定值见 GB_SEGREGATION_LITERATURE.md §0.3：≈ −5e-11")
    ap.add_argument("--wgb", type=float, default=4.0e-6, help="晶界宽度 m（与 κ/μ0 一致）")
    ap.add_argument("--dry-run", action="store_true", help="只打印 diff，不写文件")
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    out = src
    notes = []

    # ---- 补丁 1：f_loc 的表达式 ----
    # ⚠ 必须锚定**行首**（`^` + re.M）的 `[free_energy]`：该字符串在**注释**里
    #   也出现过（N.i:253 "…见 [free_energy] 的…"）。只写 `[ \t]*\[free_energy\]`
    #   而不加行首锚定，`[ \t]*` 会匹配到注释里括号前的空格 ⇒ **匹配到注释**，
    #   表现为「块里没有 f_loc」。这个坑本轮踩了两次。
    m = re.search(r"(^[ \t]*\[free_energy\](?:.*?))\n[ \t]*\[\]", src, re.S | re.M)
    if not m:
        sys.exit("错误：找不到 [free_energy] 块")
    blk = m.group(1)
    if "property_name = f_loc" not in blk:
        sys.exit("错误：[free_energy] 块里没有 f_loc")

    new_expr = build_expr(a.f_part, a.omega0)
    blk2, n = re.subn(r"expression\s*=\s*'k_c/2\*\(c-c0\)\^2.*?'",
                      "expression = '" + new_expr + "'", blk, flags=re.S)
    if n != 1:
        sys.exit(f"错误：f_loc 的 expression 匹配到 {n} 处（应为 1）—— 源文件变过了？")
    notes.append(f"f_loc 表达式：分配项驱动 = {a.f_part}"
                 + (f"，并加偏析项 Ω₀ = {a.omega0:g}" if a.omega0 is not None else ""))

    # ---- 补丁 2：常量表（需要时才加 Omega0/wgb）----
    if a.omega0 is not None:
        blk2, n = re.subn(r"constant_names\s*=\s*'k_c c0 A_part'\s*\n(\s*)constant_expressions\s*=\s*'0\.9 0\.036 0\.264'",
                          lambda mm: ("constant_names     = 'k_c c0 A_part Omega0 wgb'\n"
                                      f"{mm.group(1)}constant_expressions = "
                                      f"'0.9 0.036 0.264 {a.omega0:g} {a.wgb:g}'"),
                          blk2)
        if n != 1:
            sys.exit(f"错误：f_loc 的常量表匹配到 {n} 处（应为 1）")
        notes.append(f"f_loc 常量表：加 Omega0={a.omega0:g} wgb={a.wgb:g}")

    out = out[:m.start(1)] + blk2 + out[m.end(1):]

    # ---- 补丁 3：M 的分母（f_cc）—— **必须与 f_loc 的分配项一致** ----
    if a.f_part != "S":
        m2 = re.search(r"(^[ \t]*\[solute_mobility\](?:.*?))\n[ \t]*\[\]", out, re.S | re.M)
        if not m2:
            sys.exit("错误：找不到 [solute_mobility] 块")
        blkM = m2.group(1)
        blkM2, n = re.subn(r"/ \(k_c \+ 2\*A_part\*S_eta2\)",
                           "/ (k_c + 2*A_part*min(1, 2*S_eta2))", blkM)
        if n != 1:
            sys.exit(f"错误：M 的分母匹配到 {n} 处（应为 1）")
        out = out[:m2.start(1)] + blkM2 + out[m2.end(1):]
        notes.append("M 的分母 f_cc 同步改为 k_c + 2*A_part*min(1, 2*S)")

    print("将做以下改动：")
    for i, s in enumerate(notes, 1):
        print(f"  {i}. {s}")
    print()

    diff = list(difflib.unified_diff(
        src.splitlines(keepends=True), out.splitlines(keepends=True),
        fromfile=a.src, tofile=a.out))
    print(f"diff：{len([d for d in diff if d.startswith('+') or d.startswith('-')]) - 2} 行变化")
    sys.stdout.writelines(diff)

    if a.dry_run:
        print("\n(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(out)
    dif = a.out + ".diff"
    open(dif, "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {dif}")

    # 自检：改完之后 f_loc / M 里不该再出现裸露的分配项
    print("\n自检：")
    print("  含偏析项     :", "是" if "Omega0" in out else "否")
    print("  分配项驱动   :", "h_solid" if "A_part*c^2*min(1, 2*(" in out else "Ση²")
    print("  M 的分母同步 :", "是" if "/ (k_c + 2*A_part*min(1, 2*S_eta2))" in out else "否")


if __name__ == "__main__":
    main()
