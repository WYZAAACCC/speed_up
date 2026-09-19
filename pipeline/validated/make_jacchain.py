#!/usr/bin/env python3
"""
把**「经 material_property_names 的链式法则不进雅可比」**的三处链拆平。

## 缺陷（2026-09-20 查明，见 validated/VALIDATION_STATUS.md 的 T1b 详段）

`DerivativeParsedMaterial` **只对「本材料表达式里字面出现的变量」发射导数**。
表达式里如果只有别的**材料属性**、没有任何变量，它就**一个导数都不发射**，
而生产核**确实在索取**这些导数 ⇒ 求到的值是静默的零 ⇒ **雅可比与残差不一致**。

受控 FD 判决（`run_t1b_L_test.sh`，1D/60 单元/真晶界，只差两处）：

| 算例 | `||J-Jfd||/||J||` |
|---|---|
| `const`（正对照，L 与 η 无关） | **6.17e-10** ✅ |
| `eta_dep`（**生产结构**：`L2b` 经 `material_property_names` 引 `align4`） | **1.36e-03** ❌ |
| `inline`（把 η 依赖写进 `L2b` 的表达式） | **1.36e-03** ❌ ← 逐位相同！ |
| `direct`（绕过 `L_aniso`，直接用 `L2b`） | **1.23e-09** ✅ |
| `merged`（把 η 写进 `L` 自己的表达式） | **1.23e-09** ✅ |

⇒ **断链在 `L_aniso` 那一层**；把上游修好没用，必须让**最终被索取的那个属性**
的表达式自己字面含变量。

## 本脚本修三处

| 属性 | 被谁索取 | 现状 | 修法 |
|---|---|---|---|
| `L` | `ACInterface(variable_L=true)` 取 `dL/dgr0`、`d²L/dgr0²` | 表达式 = `L2a*L2b`（无变量）⇒ **不发射** | 把 `L2a`、`align4` 的式子**内联**进 `L` |
| `M` | `SplitCHWRes(coupled_variables='gr0..gr7')` 取 `dM/dgr0` | 表达式只含 `S_eta2 h_gb h_solid` ⇒ **不发射** | 把三者**内联**进 `M` |
| `F_at` | `AntitrappingCurrent` 取 `dF_at/dgr*`（非对角块） | 表达式只含 `h_gb` ⇒ 只发射 `dF_at/dc` | 把 `h_gb` **内联**进 `F_at` |

## ⚠ 代价必须先量

`L2a` 的式子是 28 项的和、`align4` 是 8 项的和 —— 内联后符号求导树会变大。
生成器注释里写着「拆三层就是为了让每个材料的求导树都小」，而且曾有一次内联尝试
**5 分钟 100% CPU、0 次 JIT**。⇒ **本脚本只生成，代价由 `run_jacchain_check.sh` 量**。

## 用法

    python3 make_jacchain.py --src stage1_meltpool_d.i --out x.i --dry-run
    python3 make_jacchain.py --src stage1_meltpool_d.i --out stage1_meltpool_d.i
"""

import argparse
import difflib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

# ⚠ 不要硬编码 op_num。从输入的 [free_energy] 的 coupled_variables 里读
#   （它必须列出全部序参量，否则 f_loc 的 η 导数会静默缺失 —— P0-1 同类）。
#   读不到就报错退出，**不要猜**。
def read_eta(t):
    m = re.search(r"^[ 	]*\[free_energy\][\s\S]*?coupled_variables\s*=\s*'([^']*)'",
                  t, re.M)
    if not m:
        sys.exit("错误：读不到 [free_energy] 的 coupled_variables —— 无法确定 op_num")
    names = m.group(1).split()
    eta = [v for v in names if v.startswith("gr") and v[2:].isdigit()]
    if not eta:
        sys.exit(f"错误：[free_energy] 的 coupled_variables 里没有 gr*：{names}")
    if sorted(eta, key=lambda v: int(v[2:])) != eta:
        sys.exit(f"错误：序参量不是有序的 gr0..grN：{eta}")
    return eta


def block(t, name):
    """取行首锚定的 `[name]` 块（含块头与 `[]`）。本仓库的坑：块名在注释里也出现过。"""
    m = re.search(rf"^(?P<ind>[ \t]*)\[{re.escape(name)}\](?P<body>(?:.*?\n)*?)^[ \t]*\[\][ \t]*$",
                  t, re.M)
    if not m:
        sys.exit(f"错误：找不到块 [{name}] —— 源文件变过了？")
    return m


def expr_of(t, name):
    m = block(t, name)
    e = re.search(r"expression\s*=\s*'([^']*)'", m.group("body"), re.S)
    if not e:
        sys.exit(f"错误：块 [{name}] 里没有单引号包裹的 expression")
    return e.group(1)


def mp_of(t, name):
    m = block(t, name)
    e = re.search(r"material_property_names\s*=\s*'([^']*)'", m.group("body"))
    return e.group(1).split() if e else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    # 与 make_jacfix.py 的接口对齐：diff 总是写，`--diff` 只是接受这个旗标
    ap.add_argument("--diff", action="store_true", help="（总是写 diff，此旗标仅为接口一致）")
    a = ap.parse_args()

    t = open(a.src, encoding="utf-8").read()
    ETA = read_eta(t)
    N = len(ETA)
    print(f"  从输入读到 {N} 个序参量：{ETA[0]}..{ETA[-1]}")
    log = []

    # ---------------- ① L：把 L2a 与 align4 内联进 L_aniso ----------------
    #     L = L2a * (1 + 0.7*(2*align4 - 1))
    e_L2a = expr_of(t, "L2a")
    e_al4 = expr_of(t, "align4_prop") if "align4_prop" in t else None
    if e_al4 is None:
        # 生成器里块名可能是 align4；扫一遍
        for cand in ("align4", "align4_prop", "align4_mat"):
            if cand in t:
                try:
                    e_al4 = expr_of(t, cand); break
                except SystemExit:
                    pass
    if e_al4 is None:
        sys.exit("错误：找不到 align4 的定义")
    e_L2b_inline = f"(1+0.7*(2*({e_al4})-1))"
    e_L_new = f"({e_L2a})*{e_L2b_inline}"

    m = block(t, "L_aniso")
    body_new = (
        "  # 【2026-09-20 T1b 修复】把 L2a 与 align4 **内联**进来。\n"
        "  #   原来这一层的表达式里**没有任何变量**，只有别的材料属性 ⇒\n"
        "  #   DerivativeParsedMaterial 一个导数都不发射 ⇒ ACInterface(variable_L=true)\n"
        "  #   索取的 dL/dgr0 / d^2L/dgr0^2 静默为零 ⇒ 雅可比与残差不一致。\n"
        "  #   实测：内联后 FD 比值从 1.36e-03 回到 1.23e-09（正对照 6.17e-10）。\n"
        "  #   ⚠ 代价是符号求导树变大，必须量 JIT 时间（见 run_jacchain_check.sh）。\n"
        "  # ⚠ 本注释**不得**写出 expression 赋值的样子 —— 本文件的解析是正则，\n"
        "  #   会在注释里先命中（AGENTS.md 教训 6，本轮又踩一次）。\n"
        f"    type = DerivativeParsedMaterial\n"
        f"    property_name = L\n"
        f"    coupled_variables = 'T {' '.join(ETA)}'\n"
        f"    material_property_names = 'gdir_p gdir_q'\n"
        f"    expression = '{e_L_new}'\n"
        f"    derivative_order = 2\n"
    )
    t = t[:m.start()] + "  [L_aniso]\n" + body_new + "  []\n" + t[m.end():]
    log.append(("L_aniso", f"内联 L2a + align4，表达式 {len(e_L_new)} 字符"))

    # ---------------- ② M：把 S_eta2 / h_gb / h_solid 内联 ----------------
    #     S  = Σ gr^2          Q = Σ gr^4
    #     h_gb    = 8*(S^2 - Q)
    #     h_solid = min(1, 2*S)
    S = "(" + "+".join(f"{g}^2" for g in ETA) + ")"
    Q = "(" + "+".join(f"{g}^4" for g in ETA) + ")"
    eM = expr_of(t, "solute_mobility")
    if any(v in mp_of(t, "solute_mobility") for v in ("S_eta2", "h_gb", "h_solid")):
        eM_new = (eM.replace("S_eta2", S)
                     .replace("h_gb", f"(8*({S}^2-{Q}))")
                     .replace("h_solid", f"(min(1, 2*{S}))"))
        m = block(t, "solute_mobility")
        body = m.group("body")
        body = re.sub(r"[ \t]*material_property_names\s*=\s*'[^']*'\n", "", body)
        body = re.sub(r"expression\s*=\s*'[^']*'", f"expression = '{eM_new}'", body, flags=re.S)
        body = (
            "  # 【2026-09-20 T1b 修复】把 S_eta2 / h_gb / h_solid 内联进来。\n"
            "  #   原来只含材料属性 ⇒ dM/dgr0 静默为零，而 SplitCHWRes 明确索取它。\n"
            + body
        )
        t = t[:m.start()] + "  [solute_mobility]\n" + body + "  []\n" + t[m.end():]
        log.append(("solute_mobility", f"内联 S_eta2/h_gb/h_solid，表达式 {len(eM_new)} 字符"))
    else:
        log.append(("solute_mobility", "⚠ 未发现这三个材料属性 —— 跳过（可能已改过）"))

    # ---------------- ③ F_at：把 h_gb 内联（抗截留项，若存在）----------------
    if "property_name = F_at" in t:
        eF = expr_of(t, "at_susc")
        if "h_gb" in mp_of(t, "at_susc"):
            eF_new = eF.replace("h_gb", f"(8*({S}^2-{Q}))")
            m = block(t, "at_susc")
            body = m.group("body")
            body = re.sub(r"[ \t]*material_property_names\s*=\s*'[^']*'\n", "", body)
            body = re.sub(r"expression\s*=\s*'[^']*'", f"expression = '{eF_new}'", body, flags=re.S)
            # ⚠⚠ **内联了变量就必须把它加进 `coupled_variables`** —— 否则解析器
            #    报 "Unknown identifier"（本轮实测踩到：at_susc 原来是 'c w'，
            #    内联 h_gb 后表达式里出现了 gr*）。`w` 因为 `+ 0*w` 必须保留。
            body = re.sub(r"coupled_variables\s*=\s*'[^']*'",
                          f"coupled_variables = 'c w {' '.join(ETA)}'", body)
            t = t[:m.start()] + "  [at_susc]\n" + body + "  []\n" + t[m.end():]
            log.append(("at_susc", f"内联 h_gb + 扩 coupled_variables，表达式 {len(eF_new)} 字符"))
    else:
        log.append(("at_susc", "输入里没有抗截留项 —— 跳过"))

    print("将做以下改动：")
    for k, v in log:
        print(f"  {k:<18} {v}")
    print()

    src = open(a.src, encoding="utf-8").read()
    diff = list(difflib.unified_diff(src.splitlines(keepends=True), t.splitlines(keepends=True),
                                     fromfile=a.src, tofile=a.out))
    nchg = len([d for d in diff if d.startswith(("+", "-"))]) - 2
    print(f"diff：{nchg} 行变化")
    if a.dry_run:
        print("(--dry-run：没有写文件)")
        return

    open(a.out, "w", encoding="utf-8", newline="").write(t)
    open(a.out + ".diff", "w", encoding="utf-8", newline="").write("".join(diff))
    print(f"\n写出 {a.out}    diff 存到 {a.out}.diff")

    # ---- 自检：① 表达式必须**字面含变量**（否则不发射导数）
    #           ② 表达式里用到的变量必须**都在 coupled_variables 里**（否则解析器报 Unknown identifier）
    print("\n自检：")
    ok = True
    for name in ("L_aniso", "solute_mobility", "at_susc"):
        try:
            e = expr_of(t, name)
            cv = re.search(r"coupled_variables\s*=\s*'([^']*)'", block(t, name).group("body"))
            cvs = cv.group(1).split() if cv else []
        except SystemExit:
            continue
        has = "gr0" in e
        missing = [v for v in ([f"gr{i}" for i in range(N)] + ["c", "w", "T"])
                   if re.search(rf"{v}", e) and (v not in cvs)]
        flag = "✅" if (has and not missing) else "❌"
        msg = (f"含变量 {'是' if has else '否'}"
               + (f"，但 coupled_variables 缺 {missing}" if missing else ""))
        print(f"  {flag} {name:<18} {msg}（表达式 {len(e)} 字符）")
        ok &= has and not missing
    assert ok, "修法没生效或有变量没声明 —— 见上"


if __name__ == "__main__":
    main()
